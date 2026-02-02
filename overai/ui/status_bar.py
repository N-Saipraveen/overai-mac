"""
Status bar manager - Clean, minimal Apple-style menu.
"""

from typing import Callable, Optional

import objc
from Foundation import NSNotificationCenter
from AppKit import (
    NSStatusBar, NSMenu, NSMenuItem, NSImage,
    NSSquareStatusItemLength, NSFont, NSAttributedString,
    NSForegroundColorAttributeName, NSColor
)

from ..utils.logger import Logger
from ..constants import APP_VERSION

logger = Logger("StatusBar")


class StatusBarManager:
    """Minimal status bar with Apple-style menu."""
    
    def __init__(self):
        self._status_item = None
        self._menu = None
        self._callbacks = {}
    
    def setup(self):
        """Setup status bar."""
        # Use Variable length for better compatibility
        from AppKit import NSVariableStatusItemLength
        self._status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(
            NSVariableStatusItemLength
        )
        self._update_icon()
        self._create_menu()
        self._status_item.setMenu_(self._menu)
        self._setup_appearance_observer()
    
    def _update_icon(self):
        """Set menu bar icon."""
        if not self._status_item:
            return
        
        # Use system symbol 'sparkles' (AI standard) for reliability
        # This avoids "white square" (solid icon) and "missing" (bad path) issues
        image = NSImage.imageWithSystemSymbolName_accessibilityDescription_("sparkles", "OverAI")
        
        if image:
            image.setTemplate_(True)
            self._status_item.button().setImage_(image)
            self._status_item.button().setTitle_("")
            return
        
        # 3. Last resort: System Symbol (Always works)
        # Use a system symbol that looks like 'O'
        fallback = NSImage.imageWithSystemSymbolName_accessibilityDescription_("circle.circle", "OverAI")
        if fallback:
            self._status_item.button().setImage_(fallback)
            self._status_item.button().setTitle_("")
        else:
            # Text fallback
            self._status_item.button().setTitle_("O")
    
    def _setup_appearance_observer(self):
        """Watch for theme changes."""
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(
            self, 'appearanceChanged:', 'AppleInterfaceThemeChangedNotification', None
        )
    
    def appearanceChanged_(self, notification):
        self._update_icon()
    
    def _create_menu(self):
        """Create clean Apple-style menu."""
        self._menu = NSMenu.alloc().init()
        
        # App header
        self._add_item(f"OverAI v{APP_VERSION}", enabled=False)
        self._menu.addItem_(NSMenuItem.separatorItem())
        
        # Window controls
        self._add_item("Show Window", "show:", "macwindow", "s")
        self._add_item("Hide Window", "hide:", "eye.slash", "h")
        self._add_item("Reload", "reload:", "arrow.clockwise", "r")
        self._menu.addItem_(NSMenuItem.separatorItem())
        
        # Settings
        self._add_item("Preferences…", "settings:", "gear", ",")
        self._menu.addItem_(NSMenuItem.separatorItem())
        
        # Standard app items
        self._add_item("About OverAI", "about:", "info.circle")
        self._add_item("Quit OverAI", "quit:", "power", "q")
    
    def _add_item(self, title: str, action: str = None, icon: str = None, 
                  shortcut: str = "", enabled: bool = True):
        """Add menu item."""
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            title, action, shortcut
        )
        
        if action:
            item.setTarget_(self)
        
        item.setEnabled_(enabled)
        
        if icon:
            image = NSImage.imageWithSystemSymbolName_accessibilityDescription_(icon, title)
            if image:
                item.setImage_(image)
        
        self._menu.addItem_(item)
    
    # MARK: - Actions
    
    def show_(self, sender):
        if 'show' in self._callbacks:
            self._callbacks['show']()
    
    def hide_(self, sender):
        if 'hide' in self._callbacks:
            self._callbacks['hide']()
    
    def reload_(self, sender):
        if 'reload' in self._callbacks:
            self._callbacks['reload']()
    
    def settings_(self, sender):
        if 'settings' in self._callbacks:
            self._callbacks['settings']()
    
    def about_(self, sender):
        if 'about' in self._callbacks:
            self._callbacks['about']()
    
    def quit_(self, sender):
        if 'quit' in self._callbacks:
            self._callbacks['quit']()
    
    # MARK: - Public API
    
    def on(self, event: str, callback: Callable):
        """Register callback."""
        self._callbacks[event] = callback
    
    def cleanup(self):
        """Clean up resources."""
        if self._status_item:
            NSStatusBar.systemStatusBar().removeStatusItem_(self._status_item)
            self._status_item = None
        self._menu = None
        self._callbacks.clear()
