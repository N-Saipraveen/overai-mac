"""
Window Manager - Optimized window handling with proper memory management.
Uses modern AppKit patterns and supports state restoration.
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

import objc
from Foundation import NSObject, CGRect, NSMakeRect, NSNotificationCenter, NSUserDefaults
from AppKit import (
    NSWindow, NSPanel, NSColor, NSView, NSViewWidthSizable, NSViewHeightSizable,
    NSApplication, NSApp, NSScreen, NSFloatingWindowLevel, NSBorderlessWindowMask,
    NSResizableWindowMask, NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorStationary, NSWindowSharingNone,
    NSWindowDidResizeNotification, NSVisualEffectView, NSAppearance,
    NSAppearanceNameAqua, NSAppearanceNameDarkAqua,
    NSAnimationContext, NSHapticFeedbackManager, NSHapticFeedbackPerformanceTimeNow,
    NSNonactivatingPanelMask
)
from Quartz import CGEventTapEnable

from ..utils.logger import Logger
from ..utils.theme import ThemeManager
from ..utils.accessibility import AccessibilityManager

logger = Logger("WindowManager")

# Constants
FRAME_SAVE_NAME = "OverAIWindowFrame"
CONFIG_FILE = Path.home() / "Library" / "Application Support" / "OverAI" / "config.json"
MIN_OPACITY = 0.2
MAX_OPACITY = 1.0
OPACITY_STEP = 0.1


@dataclass
class WindowState:
    """Immutable window state for restoration."""
    opacity: float = 0.9
    size: tuple = (550, 580)
    position: tuple = (0, 0)  # Will be centered
    service: str = "Grok"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WindowState":
        return cls(**data)


class OverAI_OverlayPanel(NSPanel):
    """
    Non-activating panel - appears above other apps WITHOUT stealing focus.
    This is how ChatGPT, Spotlight, and Alfred overlays work.
    """
    
    def init(self):
        self = objc.super(OverAI_OverlayPanel, self).init()
        if self is None:
            return None
        self._drag_start_pos = None
        self._drag_start_frame = None
        return self
    
    def canBecomeKeyWindow(self) -> bool:
        return True
    
    def canBecomeMainWindow(self) -> bool:
        return True
    
    def keyDown_(self, event):
        """Handle key events with proper forwarding."""
        delegate = self.delegate()
        if delegate and hasattr(delegate, 'handleKeyEvent:'):
            delegate.handleKeyEvent_(event)
        else:
            # Forward to responder chain
            objc.super(OverAI_OverlayPanel, self).keyDown_(event)
    
    # MARK: - Dragging Support
    
    def mouseDown_(self, event):
        """Start dragging - track initial position."""
        # Get the location in screen coordinates
        self._drag_start_pos = event.locationInWindow()
        self._drag_start_frame = self.frame()
        
    def mouseDragged_(self, event):
        """Handle drag - move window."""
        if self._drag_start_pos is None or self._drag_start_frame is None:
            return
        
        # Get current mouse location in screen coordinates
        current_pos = self.mouseLocationOutsideOfEventStream()
        
        # Calculate new frame position
        from Foundation import NSPoint
        screen = NSScreen.mainScreen()
        screen_frame = screen.frame()
        
        # Calculate new origin
        new_x = self._drag_start_frame.origin.x + event.deltaX()
        new_y = self._drag_start_frame.origin.y - event.deltaY()
        
        # Keep window on screen (with some padding)
        padding = 50
        new_x = max(-self._drag_start_frame.size.width + padding, 
                    min(new_x, screen_frame.size.width - padding))
        new_y = max(padding, 
                    min(new_y, screen_frame.size.height - padding))
        
        # Update frame
        new_frame = self._drag_start_frame
        new_frame.origin.x = new_x
        new_frame.origin.y = new_y
        
        self.setFrame_display_(new_frame, True)
        self._drag_start_frame = new_frame
        
    def mouseUp_(self, event):
        """End dragging - save position."""
        self._drag_start_pos = None
        self._drag_start_frame = None
        # Save the new position
        if self.delegate() and hasattr(self.delegate(), '_save_state'):
            self.delegate()._save_state()


class WindowManager(NSObject):
    """
    Manages the overlay window with optimized memory usage and state restoration.
    """
    
    def init(self):
        self = objc.super(WindowManager, self).init()
        if self is None:
            return None
        
        self._window: Optional[OverAI_OverlayPanel] = None
        self._content_view: Optional[NSView] = None
        self._drag_area: Optional[NSView] = None
        self._state = WindowState()
        self._theme_manager = ThemeManager()
        self._accessibility = AccessibilityManager()
        self._resize_observer = None
        
        # Ensure config directory exists
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        return self
    
    def createWindow(self) -> OverAI_OverlayPanel:
        """Create optimized window with proper settings."""
        logger.info("Creating optimized window")
        
        # Load saved state
        self._load_state()
        
        # Calculate centered position
        screen = NSScreen.mainScreen()
        screen_rect = screen.visibleFrame()
        full_rect = screen.frame()
        
        x_pos = full_rect.origin.x + (full_rect.size.width - self._state.size[0]) / 2
        y_pos = screen_rect.origin.y + 20
        
        # Create panel with non-activating behavior (key for overlay UX)
        window = OverAI_OverlayPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(x_pos, y_pos, self._state.size[0], self._state.size[1]),
            NSBorderlessWindowMask | NSResizableWindowMask | NSNonactivatingPanelMask,
            2,  # NSBackingStoreBuffered
            False
        )
        
        # Configure window
        window.setLevel_(NSFloatingWindowLevel)
        window.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces |
            NSWindowCollectionBehaviorStationary
        )
        window.setFrameAutosaveName_(FRAME_SAVE_NAME)
        window.setOpaque_(False)
        window.setBackgroundColor_(NSColor.clearColor())
        window.setAlphaValue_(self._state.opacity)
        window.setSharingType_(NSWindowSharingNone)  # Hidden from recordings
        window.setDelegate_(self)
        
        # Panel-specific settings for overlay behavior
        window.setFloatingPanel_(True)  # Float above regular windows
        window.setBecomesKeyOnlyIfNeeded_(True)  # Only become key when needed
        window.setWorksWhenModal_(True)  # Work even when modal dialogs are open
        
        # Set up content with vibrancy
        self._setup_content_view(window)
        
        self._window = window
        
        # Add resize observer
        self._setup_resize_observer()
        
        return window
    
    def _setup_content_view(self, window: NSWindow):
        """Setup content view with native macOS visual effects."""
        bounds = window.contentView().bounds()
        
        # Create a visual effect view for the background (Apple-like blur)
        visual_effect = NSVisualEffectView.alloc().initWithFrame_(bounds)
        visual_effect.setMaterial_(4)  # NSVisualEffectMaterialSidebar / HUD
        visual_effect.setBlendingMode_(1)  # NSVisualEffectBlendingModeBehindWindow
        visual_effect.setState_(0)  # NSVisualEffectStateFollowsWindowActiveState
        visual_effect.setWantsLayer_(True)
        visual_effect.layer().setCornerRadius_(12.0)
        visual_effect.layer().setMasksToBounds_(True)
        # Ensure visual effect resizes with window
        visual_effect.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        
        # Create content container
        container = NSView.alloc().initWithFrame_(bounds)
        container.setWantsLayer_(True)
        container.layer().setCornerRadius_(12.0)
        container.layer().setMasksToBounds_(True)
        
        # Use clear background - the visual effect provides the color
        container.setBackgroundColor_(NSColor.clearColor())
        
        window.setContentView_(container)
        # Enable autoresizing for subviews
        container.setAutoresizesSubviews_(True)
        self._content_view = container
        
        # Add visual effect as background
        container.addSubview_positioned_relativeTo_(visual_effect, 0, None)
        self._visual_effect = visual_effect
        
        # Setup drag area on top
        self._setup_drag_area(container)
    
    def _setup_drag_area(self, container: NSView):
        """Setup draggable title bar area - minimal Apple design."""
        bounds = container.bounds()
        drag_height = 38.0  # Match control bar height
        
        # Create drag area with clear background
        drag_area = NSView.alloc().initWithFrame_(
            NSMakeRect(0, bounds.size.height - drag_height, bounds.size.width, drag_height)
        )
        drag_area.setWantsLayer_(True)
        
        # Use clear/semi-transparent background
        drag_area.layer().setBackgroundColor_(NSColor.clearColor().CGColor())
        
        # Anchor to top, resize width with window
        from AppKit import NSViewMinYMargin
        drag_area.setAutoresizingMask_(NSViewWidthSizable | NSViewMinYMargin)
        
        container.addSubview_(drag_area)
        self._drag_area = drag_area
        
        # Accessibility
        self._accessibility.configure_drag_area(drag_area)
    
    def _setup_resize_observer(self):
        """Setup window resize notification observer."""
        self._resize_observer = NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(
            self,
            'windowDidResize:',
            NSWindowDidResizeNotification,
            self._window
        )
    
    def windowDidResize_(self, notification):
        """Handle window resize - update subviews."""
        if not self._window or not self._content_view:
            return
        
        # Get new bounds
        bounds = self._content_view.bounds()
        
        # Update drag area if exists
        if self._drag_area:
            self._drag_area.setFrame_(
                NSMakeRect(0, bounds.size.height - 32, bounds.size.width, 32)
            )
        
        # Update all subviews to match new bounds
        for subview in self._content_view.subviews():
            # Skip the drag area (handled above)
            if subview == self._drag_area:
                continue
            
            # Update frame to match width
            frame = subview.frame()
            frame.size.width = bounds.size.width
            subview.setFrame_(frame)
        
        # Save state after resize
        self._save_state()
    
    def showWindow(self):
        """Show window with spring animation - WITHOUT stealing focus from other apps."""
        if not self._window:
            self.createWindow()
        
        # DON'T activate app - this is what makes it NOT steal focus!
        # NSApp.activateIgnoringOtherApps_(True)  <- REMOVED
        
        # Ensure window is at correct level
        self._window.setLevel_(NSFloatingWindowLevel)
        
        # Start from invisible
        self._window.setAlphaValue_(0.0)
        
        # Show without making key (use orderFront instead of makeKeyAndOrderFront)
        # The panel will become key when user clicks on it or focuses input
        self._window.orderFrontRegardless()
        
        # Get current frame for animation
        target_frame = self._window.frame()
        
        # Animate with spring effect
        NSAnimationContext.runAnimationGroup_completionHandler_(
            lambda ctx: self._setup_spring_show(ctx),
            None
        )
    
    def hideWindow(self):
        """Hide window with spring animation."""
        if not self._window:
            return
        
        # Animate out with spring
        NSAnimationContext.runAnimationGroup_completionHandler_(
            lambda ctx: self._setup_spring_hide(ctx),
            lambda: self._complete_hide()
        )
    
    def _complete_hide(self):
        """Complete hide after animation."""
        if self._window:
            self._window.orderOut_(None)
    
    def _setup_spring_show(self, context):
        """Setup spring animation for showing window (Spotlight-style)."""
        context.setDuration_(0.3)
        context.setAllowsImplicitAnimation_(True)
        
        # Use ease-out timing for spring feel
        from Quartz import CAMediaTimingFunction, kCAMediaTimingFunctionEaseOut
        timing = CAMediaTimingFunction.functionWithName_(kCAMediaTimingFunctionEaseOut)
        context.setTimingFunction_(timing)
        
        # Animate opacity
        self._window.animator().setAlphaValue_(self._state.opacity)
    
    def _setup_spring_hide(self, context):
        """Setup spring animation for hiding window."""
        context.setDuration_(0.2)
        context.setAllowsImplicitAnimation_(True)
        
        # Use ease-in timing for quick hide
        from Quartz import CAMediaTimingFunction, kCAMediaTimingFunctionEaseIn
        timing = CAMediaTimingFunction.functionWithName_(kCAMediaTimingFunctionEaseIn)
        context.setTimingFunction_(timing)
        
        self._window.animator().setAlphaValue_(0.0)
    
    def _animate_opacity(self, target: float):
        """Animate window opacity."""
        if self._window:
            self._window.animator().setAlphaValue_(target)
    
    def adjust_opacity(self, increase: bool):
        """Python API to adjust window opacity with haptic feedback."""
        current = self._state.opacity
        if increase:
            new_opacity = min(current + OPACITY_STEP, MAX_OPACITY)
        else:
            new_opacity = max(current - OPACITY_STEP, MIN_OPACITY)
        
        self._state.opacity = new_opacity
        if self._window:
            self._window.setAlphaValue_(new_opacity)
        
        # Haptic feedback for tactile response
        self._perform_haptic_feedback()
        
        self._save_state()
    
    def _perform_haptic_feedback(self, pattern=1):
        """Perform Force Touch haptic feedback.
        
        Pattern types:
        - 1: Generic (default) - subtle bump
        - 2: Alignment - for snapping/alignment
        - 3: Level change - for discrete value changes
        """
        try:
            performer = NSHapticFeedbackManager.defaultPerformer()
            # NSHapticFeedbackPatternGeneric = 0, LevelChange = 1, Alignment = 2
            performer.performFeedbackPattern_performanceTime_(
                pattern,  # Pattern type
                NSHapticFeedbackPerformanceTimeNow  # Perform immediately
            )
        except Exception as e:
            # Haptic feedback not available (older Mac or no Force Touch trackpad)
            logger.debug(f"Haptic feedback not available: {e}")
    
    def _load_state(self):
        """Load window state from disk."""
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self._state = WindowState.from_dict(data.get('window', {}))
                    logger.debug(f"Loaded window state: {self._state}")
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
    
    def _save_state(self):
        """Save window state to disk."""
        try:
            if self._window:
                frame = self._window.frame()
                self._state.size = (frame.size.width, frame.size.height)
            
            data = {'window': self._state.to_dict()}
            with open(CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up window manager")
        
        if self._resize_observer:
            NSNotificationCenter.defaultCenter().removeObserver_(self._resize_observer)
            self._resize_observer = None
        
        self._save_state()
        
        self._window = None
        self._content_view = None
        self._drag_area = None
    
    @property
    def window(self) -> Optional[OverAI_OverlayPanel]:
        return self._window
    
    @property
    def content_view(self) -> Optional[NSView]:
        return self._content_view
