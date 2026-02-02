"""
Optimized keyboard handling with event tap management.
"""

import json
import time
from pathlib import Path
from typing import Callable, Optional, Dict, Any
from dataclasses import dataclass

import objc
from Quartz import (
    CGEventTapCreate, CGEventTapEnable, CFMachPortCreateRunLoopSource,
    CFRunLoopAddSource, CFRunLoopGetCurrent, kCFRunLoopCommonModes,
    kCGHIDEventTap, kCGHeadInsertEventTap, kCGEventTapOptionDefault,
    CGEventMaskBit, kCGEventKeyDown, kCGKeyboardEventKeycode,
    CGEventGetIntegerValueField, CGEventGetFlags,
    kCGEventFlagMaskAlternate, kCGEventFlagMaskCommand,
    kCGEventFlagMaskControl, kCGEventFlagMaskShift
)
from AppKit import NSEvent

from .logger import Logger

logger = Logger("KeyboardManager")

SPECIAL_KEYS = {
    49: "Space",
    36: "Return",
    53: "Escape",
    48: "Tab",
    51: "Delete",
    117: "Forward Delete",
    122: "F1", 120: "F2", 99: "F3", 118: "F4",
    96: "F5", 97: "F6", 98: "F7", 100: "F8",
    101: "F9", 109: "F10", 103: "F11", 111: "F12",
    123: "Left", 124: "Right", 125: "Down", 126: "Up",
    116: "Page Up", 121: "Page Down", 119: "End", 115: "Home"
}


@dataclass
class HotkeyConfig:
    """Immutable hotkey configuration."""
    flags: int
    keycode: int
    
    def to_dict(self) -> Dict[str, int]:
        return {"flags": self.flags, "keycode": self.keycode}
    
    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> "HotkeyConfig":
        return cls(flags=data.get("flags", 0), keycode=data.get("keycode", 0))
    
    def matches(self, flags: int, keycode: int) -> bool:
        """Check if event matches this hotkey."""
        return keycode == self.keycode and (flags & self.flags) == self.flags


# Default: Command + G
DEFAULT_HOTKEY = HotkeyConfig(
    flags=kCGEventFlagMaskCommand,
    keycode=5  # 'g'
)


class KeyboardManager:
    """
    Manages global keyboard shortcuts with proper cleanup.
    """
    
    CONFIG_PATH = Path.home() / "Library" / "Application Support" / "OverAI" / "hotkey.json"
    
    def __init__(self):
        self._event_tap = None
        self._run_loop_source = None
        self._hotkey = DEFAULT_HOTKEY
        self._callback: Optional[Callable] = None
        self._is_listening = False
        self._last_trigger_time = 0
        self._debounce_ms = 200  # Prevent rapid triggering
        
        # Ensure directory exists
        self.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        # Load saved hotkey
        self._load_hotkey()
    
    def _load_hotkey(self):
        """Load hotkey from config."""
        try:
            if self.CONFIG_PATH.exists():
                with open(self.CONFIG_PATH, 'r') as f:
                    data = json.load(f)
                    self._hotkey = HotkeyConfig.from_dict(data)
                    logger.info(f"Loaded hotkey: {self.get_hotkey_string()}")
        except Exception as e:
            logger.error(f"Failed to load hotkey: {e}")
    
    def save_hotkey(self, flags: int, keycode: int):
        """Save hotkey to config."""
        self._hotkey = HotkeyConfig(flags=flags, keycode=keycode)
        try:
            with open(self.CONFIG_PATH, 'w') as f:
                json.dump(self._hotkey.to_dict(), f)
            logger.info(f"Saved hotkey: {self.get_hotkey_string()}")
        except Exception as e:
            logger.error(f"Failed to save hotkey: {e}")
    
    def start_listening(self, callback: Callable):
        """Start global keyboard listening."""
        if self._is_listening:
            return
        
        self._callback = callback
        
        # Create event tap
        self._event_tap = CGEventTapCreate(
            kCGHIDEventTap,
            kCGHeadInsertEventTap,
            kCGEventTapOptionDefault,
            CGEventMaskBit(kCGEventKeyDown),
            self._event_handler,
            None
        )
        
        if not self._event_tap:
            logger.error("Failed to create event tap - check Accessibility permissions")
            return
        
        # Create run loop source
        self._run_loop_source = CFMachPortCreateRunLoopSource(
            None, self._event_tap, 0
        )
        
        # Add to run loop
        CFRunLoopAddSource(
            CFRunLoopGetCurrent(),
            self._run_loop_source,
            kCFRunLoopCommonModes
        )
        
        # Enable event tap
        CGEventTapEnable(self._event_tap, True)
        self._is_listening = True
        
        logger.info("Keyboard listener started")
    
    def stop_listening(self):
        """Stop keyboard listening and cleanup."""
        if not self._is_listening:
            return
        
        if self._event_tap:
            CGEventTapEnable(self._event_tap, False)
            self._event_tap = None
        
        if self._run_loop_source:
            # Note: Run loop sources can't be removed, but we disabled the tap
            self._run_loop_source = None
        
        self._is_listening = False
        self._callback = None
        
        logger.info("Keyboard listener stopped")
    
    def _event_handler(self, proxy, event_type, event, refcon):
        """Handle keyboard events."""
        if event_type != kCGEventKeyDown:
            return event
        
        keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
        flags = CGEventGetFlags(event)
        
        # Check debounce
        current_time = time.time() * 1000
        if current_time - self._last_trigger_time < self._debounce_ms:
            return None  # Swallow event
        
        # Check if matches our hotkey
        if self._hotkey.matches(flags, keycode):
            self._last_trigger_time = current_time
            if self._callback:
                self._callback()
            return None  # Swallow the event
        
        return event
    
    def get_hotkey_string(self) -> str:
        """Get human-readable hotkey string."""
        modifiers = []
        
        if self._hotkey.flags & kCGEventFlagMaskCommand:
            modifiers.append("⌘")
        if self._hotkey.flags & kCGEventFlagMaskOption:
            modifiers.append("⌥")
        if self._hotkey.flags & kCGEventFlagMaskControl:
            modifiers.append("⌃")
        if self._hotkey.flags & kCGEventFlagMaskShift:
            modifiers.append("⇧")
        
        key = SPECIAL_KEYS.get(self._hotkey.keycode, chr(self._hotkey.keycode + 93))
        
        return " + ".join(modifiers + [key]) if modifiers else key
    
    def cleanup(self):
        """Cleanup resources."""
        self.stop_listening()


# C function callback needs to be at module level for stability
def create_event_handler(manager: KeyboardManager):
    """Create stable event handler callback."""
    @objc.callbackFor(CGEventTapCreate)
    def handler(proxy, event_type, event, refcon):
        return manager._event_handler(proxy, event_type, event, refcon)
    return handler
