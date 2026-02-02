"""
Accessibility Onboarding Window.
Beautiful, Apple-style permission request flow like Raycast and Alfred.
"""

import os
import sys
import objc
from Foundation import (
    NSObject, NSMakeRect, NSTimer, NSNotificationCenter,
    NSURL, NSBundle, NSDictionary
)
from AppKit import (
    NSWindow, NSView, NSButton, NSTextField, NSImageView,
    NSColor, NSFont, NSImage, NSBezierPath,
    NSWindowStyleMaskTitled, NSWindowStyleMaskClosable,
    NSBackingStoreBuffered, NSModalResponseOK, NSModalResponseCancel,
    NSVisualEffectView, NSVisualEffectMaterialWindowBackground,
    NSTextAlignmentCenter, NSLineBreakByWordWrapping,
    NSApp, NSWorkspace, NSBezelStyleRounded,
    NSViewWidthSizable, NSViewMinYMargin, NSViewMaxYMargin,
    NSScreen
)
from ApplicationServices import AXIsProcessTrustedWithOptions, kAXTrustedCheckOptionPrompt

from .logger import Logger

logger = Logger("OnboardingWindow")


# Use a simple Python class wrapper instead of NSObject subclass
# to avoid PyObjC method signature issues
class OnboardingHelper:
    """Helper class for window delegate and timer handling."""
    
    def __init__(self, parent):
        self.parent = parent


class OnboardingWindowDelegate(NSObject):
    """Window delegate for the onboarding window."""
    
    parent = objc.ivar()
    
    def windowWillClose_(self, notification):
        """Handle window close."""
        if self.parent:
            self.parent.handle_close()


class OnboardingTimerHandler(NSObject):
    """Timer handler."""
    
    parent = objc.ivar()
    
    def checkPermission_(self, timer):
        """Check if permission was granted."""
        if self.parent:
            self.parent.check_permission()
    
    def autoRestart_(self, timer):
        """Auto-restart after permission granted."""
        if self.parent:
            self.parent.do_restart()


class OnboardingButtonHandler(NSObject):
    """Button action handler."""
    
    parent = objc.ivar()
    
    def openSettings_(self, sender):
        """Open System Settings."""
        if self.parent:
            self.parent.open_settings()
    
    def continueClicked_(self, sender):
        """Continue button clicked."""
        if self.parent:
            self.parent.do_complete(True)


class OnboardingWindow:
    """
    Beautiful onboarding window for accessibility permissions.
    Inspired by Raycast and Alfred's permission flows.
    Uses composition instead of NSObject inheritance to avoid PyObjC issues.
    """
    
    WINDOW_WIDTH = 480
    WINDOW_HEIGHT = 400
    
    def __init__(self):
        self.window = None
        self.check_timer = None
        self.completion_callback = None
        self.status_label = None
        self.open_settings_btn = None
        self.continue_btn = None
        
        # Create delegate and handlers
        self.delegate = OnboardingWindowDelegate.alloc().init()
        self.delegate.parent = self
        
        self.timer_handler = OnboardingTimerHandler.alloc().init()
        self.timer_handler.parent = self
        
        self.button_handler = OnboardingButtonHandler.alloc().init()
        self.button_handler.parent = self
    
    def show(self, callback):
        """Show the onboarding window with a completion callback."""
        self.completion_callback = callback
        
        # Check if already trusted
        if self.is_trusted():
            logger.info("Already trusted, skipping onboarding")
            if callback:
                callback(True)
            return
        
        # Create and show window
        self.create_window()
        self.window.makeKeyAndOrderFront_(None)
        NSApp.activateIgnoringOtherApps_(True)
        
        # Start polling for permission
        self.start_permission_check()
    
    def is_trusted(self) -> bool:
        """Check if accessibility permission is granted."""
        try:
            return AXIsProcessTrustedWithOptions(None)
        except:
            return False
    
    def create_window(self):
        """Create the beautiful onboarding window."""
        # Center on screen
        screen = NSScreen.mainScreen()
        screen_frame = screen.frame()
        x = (screen_frame.size.width - self.WINDOW_WIDTH) / 2
        y = (screen_frame.size.height - self.WINDOW_HEIGHT) / 2
        
        # Create window
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(x, y, self.WINDOW_WIDTH, self.WINDOW_HEIGHT),
            NSWindowStyleMaskTitled | NSWindowStyleMaskClosable,
            NSBackingStoreBuffered,
            False
        )
        
        self.window.setTitle_("Welcome to OverAI")
        self.window.setDelegate_(self.delegate)
        
        # Setup content
        content = self.window.contentView()
        content.setWantsLayer_(True)
        
        # Add visual effect background
        visual_effect = NSVisualEffectView.alloc().initWithFrame_(content.bounds())
        visual_effect.setMaterial_(NSVisualEffectMaterialWindowBackground)
        visual_effect.setBlendingMode_(0)  # Within window
        visual_effect.setAutoresizingMask_(NSViewWidthSizable | NSViewMinYMargin | NSViewMaxYMargin)
        content.addSubview_(visual_effect)
        
        # Add content views
        self.add_icon(content)
        self.add_title(content)
        self.add_description(content)
        self.add_status_indicator(content)
        self.add_buttons(content)
    
    def add_icon(self, parent):
        """Add app icon at top."""
        icon_size = 80
        x = (self.WINDOW_WIDTH - icon_size) / 2
        y = self.WINDOW_HEIGHT - icon_size - 40
        
        icon_view = NSImageView.alloc().initWithFrame_(
            NSMakeRect(x, y, icon_size, icon_size)
        )
        
        # Try to load app icon, fallback to SF Symbol
        app_icon = NSImage.imageNamed_("NSApplicationIcon")
        if app_icon:
            icon_view.setImage_(app_icon)
        else:
            # Use SF Symbol as fallback
            symbol = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
                "hand.raised.circle.fill", "Accessibility"
            )
            if symbol:
                icon_view.setImage_(symbol)
                icon_view.setContentTintColor_(NSColor.systemBlueColor())
        
        icon_view.setImageScaling_(2)  # NSImageScaleProportionallyUpOrDown
        parent.addSubview_(icon_view)
    
    def add_title(self, parent):
        """Add title text."""
        title = NSTextField.alloc().initWithFrame_(
            NSMakeRect(40, self.WINDOW_HEIGHT - 160, self.WINDOW_WIDTH - 80, 30)
        )
        title.setStringValue_("OverAI needs Accessibility Permission")
        title.setBezeled_(False)
        title.setDrawsBackground_(False)
        title.setEditable_(False)
        title.setSelectable_(False)
        title.setAlignment_(NSTextAlignmentCenter)
        title.setFont_(NSFont.boldSystemFontOfSize_(18))
        title.setTextColor_(NSColor.labelColor())
        parent.addSubview_(title)
    
    def add_description(self, parent):
        """Add description text explaining why permission is needed."""
        desc_text = (
            "OverAI uses accessibility permissions to:\n\n"
            "• Respond to global keyboard shortcuts (⌘+G)\n"
            "• Stay visible above other windows\n"
            "• Focus input fields automatically\n\n"
            "Your privacy is protected. OverAI only reads\n"
            "keyboard shortcuts, never your screen content."
        )
        
        desc = NSTextField.alloc().initWithFrame_(
            NSMakeRect(40, self.WINDOW_HEIGHT - 290, self.WINDOW_WIDTH - 80, 120)
        )
        desc.setStringValue_(desc_text)
        desc.setBezeled_(False)
        desc.setDrawsBackground_(False)
        desc.setEditable_(False)
        desc.setSelectable_(False)
        desc.setAlignment_(NSTextAlignmentCenter)
        desc.setFont_(NSFont.systemFontOfSize_(13))
        desc.setTextColor_(NSColor.secondaryLabelColor())
        parent.addSubview_(desc)
    
    def add_status_indicator(self, parent):
        """Add status indicator showing current permission state."""
        status_y = 100
        
        self.status_label = NSTextField.alloc().initWithFrame_(
            NSMakeRect(40, status_y, self.WINDOW_WIDTH - 80, 24)
        )
        self.status_label.setBezeled_(False)
        self.status_label.setDrawsBackground_(False)
        self.status_label.setEditable_(False)
        self.status_label.setSelectable_(False)
        self.status_label.setAlignment_(NSTextAlignmentCenter)
        self.status_label.setFont_(NSFont.systemFontOfSize_(12))
        self.update_status_label(False)
        parent.addSubview_(self.status_label)
    
    def update_status_label(self, is_granted: bool, restarting: bool = False):
        """Update the status label."""
        if restarting:
            self.status_label.setStringValue_("🔄 Restarting OverAI...")
            self.status_label.setTextColor_(NSColor.systemBlueColor())
        elif is_granted:
            self.status_label.setStringValue_("✅ Permission Granted!")
            self.status_label.setTextColor_(NSColor.systemGreenColor())
        else:
            self.status_label.setStringValue_("⏳ Waiting for permission...")
            self.status_label.setTextColor_(NSColor.secondaryLabelColor())
    
    def add_buttons(self, parent):
        """Add action buttons."""
        button_width = 180
        button_height = 32
        button_y = 40
        spacing = 20
        
        total_width = button_width * 2 + spacing
        start_x = (self.WINDOW_WIDTH - total_width) / 2
        
        # Open System Settings button (primary)
        self.open_settings_btn = NSButton.alloc().initWithFrame_(
            NSMakeRect(start_x, button_y, button_width, button_height)
        )
        self.open_settings_btn.setTitle_("Open System Settings")
        self.open_settings_btn.setBezelStyle_(NSBezelStyleRounded)
        self.open_settings_btn.setTarget_(self.button_handler)
        self.open_settings_btn.setAction_("openSettings:")
        self.open_settings_btn.setKeyEquivalent_("\r")  # Enter key
        parent.addSubview_(self.open_settings_btn)
        
        # Continue button (disabled until permission granted)
        self.continue_btn = NSButton.alloc().initWithFrame_(
            NSMakeRect(start_x + button_width + spacing, button_y, button_width, button_height)
        )
        self.continue_btn.setTitle_("Continue")
        self.continue_btn.setBezelStyle_(NSBezelStyleRounded)
        self.continue_btn.setTarget_(self.button_handler)
        self.continue_btn.setAction_("continueClicked:")
        self.continue_btn.setEnabled_(False)
        parent.addSubview_(self.continue_btn)
    
    def open_settings(self):
        """Open System Settings to Accessibility pane."""
        logger.info("Opening System Settings > Accessibility")
        
        # Open directly to Privacy > Accessibility
        url = NSURL.URLWithString_(
            "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
        )
        NSWorkspace.sharedWorkspace().openURL_(url)
        
        # Also trigger the system prompt
        options = NSDictionary.dictionaryWithObject_forKey_(
            True, kAXTrustedCheckOptionPrompt
        )
        AXIsProcessTrustedWithOptions(options)
    
    def start_permission_check(self):
        """Start polling for permission grant."""
        # Check every 0.5 seconds
        self.check_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.5,
            self.timer_handler,
            "checkPermission:",
            None,
            True
        )
    
    def check_permission(self):
        """Check if permission was granted."""
        if self.is_trusted():
            logger.info("Permission granted! Will restart app...")
            self.update_status_label(True)
            self.continue_btn.setEnabled_(True)
            self.continue_btn.setTitle_("Restart Now")
            self.open_settings_btn.setTitle_("Settings ✓")
            
            # Stop checking
            if self.check_timer:
                self.check_timer.invalidate()
                self.check_timer = None
            
            # Auto-restart after 1.5 seconds
            NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                1.5,
                self.timer_handler,
                "autoRestart:",
                None,
                False
            )
    
    def do_complete(self, success: bool):
        """Complete the onboarding flow without restart."""
        # Stop timer
        if self.check_timer:
            self.check_timer.invalidate()
            self.check_timer = None
        
        # Close window
        if self.window:
            self.window.close()
            self.window = None
        
        # Call completion
        if self.completion_callback:
            self.completion_callback(success)
    
    def do_restart(self):
        """Restart the app to apply accessibility permissions."""
        logger.info("Restarting app for accessibility...")
        
        # Update UI
        self.update_status_label(True, restarting=True)
        self.continue_btn.setEnabled_(False)
        
        # Close window
        if self.window:
            self.window.close()
            self.window = None
        
        # Restart the application
        try:
            # Get the python executable and script
            python = sys.executable
            args = [python] + sys.argv
            
            logger.info(f"Restarting with: {' '.join(args)}")
            
            # Use os.execv to replace current process
            os.execv(python, args)
        except Exception as e:
            logger.error(f"Failed to restart: {e}")
            # Fall back to normal completion
            if self.completion_callback:
                self.completion_callback(True)
    
    def handle_close(self):
        """Handle window close."""
        # Stop checking
        if self.check_timer:
            self.check_timer.invalidate()
            self.check_timer = None
        
        # If closed without granting, still callback with False
        if self.completion_callback:
            is_trusted = self.is_trusted()
            self.completion_callback(is_trusted)


# Convenience function
def show_onboarding(callback):
    """Show the onboarding window."""
    onboarding = OnboardingWindow()
    onboarding.show(callback)
    return onboarding
