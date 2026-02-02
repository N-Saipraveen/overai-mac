"""
Dynamic Island-style notification manager for macOS.
Shows subtle pill-shaped notifications for service switching and other events.
"""

import objc
from Foundation import NSObject, NSTimer, NSMakeRect, CGPoint, CGRect
from AppKit import (
    NSWindow, NSView, NSColor, NSFont, NSTextField, 
    NSVisualEffectView, NSVisualEffectMaterialMenu, NSBezierPath,
    NSBorderlessWindowMask, 
    NSViewWidthSizable, NSViewHeightSizable,
    NSAnimationContext, NSImage, NSImageView
)
from AppKit import NSStatusWindowLevel

from ..utils.logger import Logger

logger = Logger("Notifications")


class DynamicIslandNotification(NSObject):
    """
    A pill-shaped notification similar to iOS Dynamic Island.
    Appears briefly at the top center of the screen.
    """
    
    WIDTH = 200.0
    HEIGHT = 44.0
    PILL_CORNER_RADIUS = 22.0
    DISPLAY_DURATION = 2.0  # Seconds to show
    ANIMATION_DURATION = 0.3
    
    def init(self):
        self = objc.super(DynamicIslandNotification, self).init()
        if self is None:
            return None
        
        self._window = None
        self._content_view = None
        self._icon_view = None
        self._text_field = None
        self._hide_timer = None
        self._is_showing = False
        
        return self
    
    def _create_window(self):
        """Create the notification window."""
        from AppKit import NSScreen
        
        screen = NSScreen.mainScreen()
        screen_frame = screen.frame()
        
        # Center at top of screen
        x = (screen_frame.size.width - self.WIDTH) / 2
        y = screen_frame.size.height - 60  # 60px from top
        
        window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(x, y, self.WIDTH, self.HEIGHT),
            NSBorderlessWindowMask,
            2,
            False
        )
        
        window.setLevel_(NSStatusWindowLevel + 1)
        window.setOpaque_(False)
        window.setBackgroundColor_(NSColor.clearColor())
        window.setIgnoresMouseEvents_(True)
        window.setCollectionBehavior_(1 << 7)  # NSWindowCollectionBehaviorCanJoinAllSpaces
        
        # Create content
        self._setup_content(window)
        
        self._window = window
        return window
    
    def _setup_content(self, window):
        """Setup the pill-shaped content."""
        bounds = window.contentView().bounds()
        
        # Visual effect view for blur
        visual = NSVisualEffectView.alloc().initWithFrame_(bounds)
        visual.setMaterial_(NSVisualEffectMaterialMenu)
        visual.setBlendingMode_(1)  # Behind window
        visual.setState_(0)
        visual.setWantsLayer_(True)
        visual.layer().setCornerRadius_(self.PILL_CORNER_RADIUS)
        visual.layer().setMasksToBounds_(True)
        
        # Add subtle border
        visual.layer().setBorderWidth_(0.5)
        visual.layer().setBorderColor_(
            NSColor.whiteColor().colorWithAlphaComponent_(0.2).CGColor()
        )
        
        window.contentView().addSubview_(visual)
        
        # Icon (left side)
        self._icon_view = NSImageView.alloc().initWithFrame_(
            NSMakeRect(14, 10, 24, 24)
        )
        self._icon_view.setImageScaling_(1)  # NSImageScaleProportionallyDown
        visual.addSubview_(self._icon_view)
        
        # Text (center)
        self._text_field = NSTextField.alloc().initWithFrame_(
            NSMakeRect(42, 10, self.WIDTH - 56, 24)
        )
        self._text_field.setBezeled_(False)
        self._text_field.setDrawsBackground_(False)
        self._text_field.setEditable_(False)
        self._text_field.setSelectable_(False)
        self._text_field.setTextColor_(NSColor.whiteColor())
        self._text_field.setFont_(NSFont.systemFontOfSize_(14))
        self._text_field.setAlignment_(1)  # NSCenterTextAlignment
        visual.addSubview_(self._text_field)
        
        self._content_view = visual
    
    def displayNotification_icon_duration_(self, message: str, icon_name: str, duration: float):
        
        # Create window if needed
        if not self._window:
            self._create_window()
        
        # Update content
        self._text_field.setStringValue_(message)
        
        # Set icon
        icon = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
            icon_name, message
        )
        if icon:
            icon.setTintColor_(NSColor.whiteColor())
            self._icon_view.setImage_(icon)
        
        # Cancel any existing timer
        if self._hide_timer:
            self._hide_timer.invalidate()
            self._hide_timer = None
        
        # Show window with animation
        self._window.setAlphaValue_(0.0)
        self._window.orderFront_(None)
        
        # Spring animation for appearance
        NSAnimationContext.runAnimationGroup_completionHandler_(
            lambda ctx: self._setup_show_animation(ctx),
            None
        )
        
        self._is_showing = True
        
        # Schedule hide
        self._schedule_hide(duration)
    
    def _setup_show_animation(self, context):
        """Setup show animation with spring."""
        context.setDuration_(self.ANIMATION_DURATION)
        self._window.animator().setAlphaValue_(1.0)
        
        # Slight scale animation
        self._content_view.setFrameOrigin_((-10, 0))
        self._content_view.animator().setFrameOrigin_((0, 0))
    
    def _schedule_hide(self, duration: float):
        """Schedule auto-hide using performSelector."""
        from Foundation import NSObject
        NSObject.cancelPreviousPerformRequestsWithTarget_selector_object_(
            self, "hideNotification", None
        )
        self.performSelector_withObject_afterDelay_(
            "hideNotification", None, duration
        )
    
    def hideNotification(self):
        """Auto-hide after delay - called by performSelector."""
        self.hideNotification_()
    
    def hideNotification_(self, sender=None):
        """Hide the notification with animation."""
        if not self._is_showing or not self._window:
            return
        
        self._is_showing = False
        
        # Spring animation for disappearance
        NSAnimationContext.runAnimationGroup_completionHandler_(
            lambda ctx: self._setup_hide_animation(ctx),
            lambda: self._complete_hide()
        )
    
    def _setup_hide_animation(self, context):
        """Setup hide animation."""
        context.setDuration_(self.ANIMATION_DURATION)
        self._window.animator().setAlphaValue_(0.0)
    
    def _complete_hide(self):
        """Complete hide operation."""
        if self._window:
            self._window.orderOut_(None)


class NotificationManager:
    """
    Manager for showing various types of notifications.
    """
    
    def __init__(self):
        self._notification = DynamicIslandNotification.alloc().init()
        self._service_icons = {
            "grok": "bolt.fill",
            "chatgpt": "bubble.left.fill",
            "claude": "quote.bubble.fill",
            "gemini": "sparkles",
            "deepseek": "magnifyingglass",
            "perplexity": "magnifyingglass.circle"
        }
    
    def show_service_switch(self, service_name: str, service_id: str):
        """Show notification when switching AI services."""
        icon = self._service_icons.get(service_id, "info.circle.fill")
        self._notification.displayNotification_icon_duration_(
            f"Switched to {service_name}", icon, self._notification.DISPLAY_DURATION
        )
    
    def show_opacity_change(self, opacity: float):
        """Show notification when opacity changes."""
        percentage = int(opacity * 100)
        self._notification.displayNotification_icon_duration_(
            f"Opacity: {percentage}%", "eye.fill", 1.0
        )
    
    def show_message(self, message: str, icon: str = "info.circle.fill"):
        """Show a custom message."""
        self._notification.displayNotification_icon_duration_(
            message, icon, self._notification.DISPLAY_DURATION
        )


# Global instance
_notification_manager = None

def get_notification_manager() -> NotificationManager:
    """Get the global notification manager."""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager
