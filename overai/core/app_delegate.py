"""
App Delegate - Main application controller with optimized lifecycle management.
Follows Apple design patterns with proper memory management.
"""

import objc
from Foundation import NSObject, NSNotificationCenter, NSTimer
from AppKit import NSApp
from AppKit import (
    NSApplication, NSApplicationActivationPolicyAccessory,
    NSApplicationDidBecomeActiveNotification,
    NSApplicationDidResignActiveNotification
)
from ApplicationServices import AXIsProcessTrustedWithOptions
from Foundation import NSDictionary
from AVFoundation import AVCaptureDevice, AVMediaTypeAudio

from ..utils.logger import Logger
from ..utils.accessibility import AccessibilityManager
from ..utils.haptics import get_haptics
from ..utils.onboarding import show_onboarding
from ..utils.memory_tracker import get_memory_tracker
from ..ui.notifications import get_notification_manager
from ..ui.api_config_dialog import show_api_config
from .window_manager import WindowManager
from .lifecycle_manager import LifecycleManager
from ..ui.webview_manager import WebViewManager
from ..ui.control_bar import ControlBar
from ..ui.status_bar import StatusBarManager
from ..utils.keyboard import KeyboardManager

logger = Logger("AppDelegate")

# Memory check interval in seconds
MEMORY_CHECK_INTERVAL = 30.0


class AppDelegate(NSObject):
    """
    Main application delegate with proper separation of concerns.
    """
    
    def init(self):
        self = objc.super(AppDelegate, self).init()
        if self is None:
            return None
        
        # Initialize components
        self._window_manager = None
        self._webview_manager = None
        self._status_bar = None
        self._keyboard_manager = None
        self._lifecycle = None
        self._control_bar = None
        self._accessibility = AccessibilityManager()
        self._memory_timer = None
        
        return self
    
    def applicationDidFinishLaunching_(self, notification):
        """App launched - show onboarding if needed, then setup."""
        logger.info("Application launching")
        
        # Set activation policy (accessory app = no dock icon)
        NSApp.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
        
        # Check if accessibility permission is granted
        is_trusted = AXIsProcessTrustedWithOptions(None)
        
        if is_trusted:
            # Already have permission, proceed normally
            logger.info("Accessibility permission already granted")
            self._complete_setup()
        else:
            # Show onboarding window
            logger.info("Showing onboarding for accessibility permission")
            self._onboarding = show_onboarding(self._on_onboarding_complete)
    
    def _on_onboarding_complete(self, success: bool):
        """Called when onboarding completes."""
        if success:
            logger.info("Onboarding complete - permission granted")
            self._complete_setup()
        else:
            logger.warning("Onboarding closed without permission")
            # Still setup, but keyboard shortcuts won't work
            self._complete_setup()
    
    def _complete_setup(self):
        """Complete app setup after permission check."""
        # Setup lifecycle manager
        self._lifecycle = LifecycleManager.alloc().init()
        self._lifecycle.setupLifecycle()
        
        # Setup main menu bar with Edit menu (for Cut/Copy/Paste to work)
        self._setup_menu_bar()
        
        # Setup components
        self._setup_window()
        self._setup_webview()
        self._setup_control_bar()
        self._setup_status_bar()
        self._setup_keyboard()
        
        # Request other permissions (microphone)
        self._request_permissions()
        
        # Setup memory monitoring
        self._setup_memory_monitoring()
        
        # Show window
        self.show_window()
        
        logger.info("Application launched successfully")
    
    def _setup_window(self):
        """Setup window manager."""
        self._window_manager = WindowManager.alloc().init()
        self._window_manager.createWindow()
    
    def _setup_menu_bar(self):
        """Setup main menu bar with Edit menu for Cut/Copy/Paste to work."""
        from AppKit import NSMenu, NSMenuItem
        
        # Create main menu bar
        main_menu = NSMenu.alloc().init()
        
        # App menu (required but can be empty)
        app_menu_item = NSMenuItem.alloc().init()
        app_menu = NSMenu.alloc().init()
        app_menu_item.setSubmenu_(app_menu)
        main_menu.addItem_(app_menu_item)
        
        # Edit menu with standard editing commands
        edit_menu_item = NSMenuItem.alloc().init()
        edit_menu = NSMenu.alloc().initWithTitle_("Edit")
        
        # Undo
        undo_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Undo", "undo:", "z")
        edit_menu.addItem_(undo_item)
        
        # Redo  
        redo_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Redo", "redo:", "Z")
        edit_menu.addItem_(redo_item)
        
        edit_menu.addItem_(NSMenuItem.separatorItem())
        
        # Cut
        cut_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Cut", "cut:", "x")
        edit_menu.addItem_(cut_item)
        
        # Copy
        copy_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Copy", "copy:", "c")
        edit_menu.addItem_(copy_item)
        
        # Paste
        paste_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Paste", "paste:", "v")
        edit_menu.addItem_(paste_item)
        
        # Delete
        delete_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Delete", "delete:", "")
        edit_menu.addItem_(delete_item)
        
        edit_menu.addItem_(NSMenuItem.separatorItem())
        
        # Select All
        select_all_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Select All", "selectAll:", "a")
        edit_menu.addItem_(select_all_item)
        
        edit_menu_item.setSubmenu_(edit_menu)
        main_menu.addItem_(edit_menu_item)
        
        # Set as main menu
        NSApp.setMainMenu_(main_menu)
        
        logger.debug("Menu bar with Edit menu created")
    
    def _setup_webview(self):
        """Setup WebView with proper positioning."""
        self._webview_manager = WebViewManager.alloc().init()
        
        # Get content bounds minus control bar
        content_view = self._window_manager.content_view
        if content_view:
            bounds = content_view.bounds()
            webview_frame = (
                (0, 0),
                (bounds.size.width, bounds.size.height - ControlBar.HEIGHT)
            )
            
            webview = self._webview_manager.create_webview(webview_frame)
            # Ensure webview resizes with window
            from AppKit import NSViewWidthSizable, NSViewHeightSizable
            webview.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
            content_view.addSubview_(webview)
            
            # Set up background color callback
            self._webview_manager.set_background_callback(self._on_webview_background_change)
    
    def _setup_control_bar(self):
        """Setup control bar with proper anchoring."""
        content_view = self._window_manager.content_view
        if not content_view:
            return
        
        bounds = content_view.bounds()
        control_bar_frame = (
            (0, bounds.size.height - ControlBar.HEIGHT),
            (bounds.size.width, ControlBar.HEIGHT)
        )
        
        self._control_bar = ControlBar.alloc().initWithFrame_(control_bar_frame)
        # Anchor to top width-wise, fixed height
        from AppKit import NSViewWidthSizable, NSViewMinYMargin
        self._control_bar.setAutoresizingMask_(NSViewWidthSizable | NSViewMinYMargin)
        
        # Set callbacks
        self._control_bar.on_service_changed(self._on_service_changed)
        self._control_bar.on_transparency_changed(self._on_transparency_changed)
        self._control_bar.on_close(self.hide_window)
        self._control_bar.on_quit(self._quit)
        self._control_bar.on_api_config(self._show_api_config)
        
        # Restore last used service
        if self._webview_manager:
            last_service = self._control_bar.select_last_service()
            # Load the last used service in webview
            if last_service == "local_ai":
                self._webview_manager.load_local_ai()
            else:
                self._webview_manager.load_service(last_service)
        
        content_view.addSubview_(self._control_bar)
    
    def _setup_status_bar(self):
        """Setup status bar."""
        self._status_bar = StatusBarManager()
        self._status_bar.setup()
        
        # Register callbacks for menu
        self._status_bar.on('show', self.show_window)
        self._status_bar.on('hide', self.hide_window)
        self._status_bar.on('reload', self._reload_page)
        self._status_bar.on('settings', self._show_settings)
        self._status_bar.on('api_config', self._show_api_config)
        self._status_bar.on('about', self._show_about)
        self._status_bar.on('quit', self._quit)
    
    def _setup_keyboard(self):
        """Setup global keyboard shortcuts."""
        self._keyboard_manager = KeyboardManager()
        self._keyboard_manager.start_listening(self._toggle_window)
    
    def _setup_memory_monitoring(self):
        """Setup periodic memory monitoring."""
        # Start periodic memory check timer
        self._memory_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            MEMORY_CHECK_INTERVAL,
            self,
            'checkMemoryUsage:',
            None,
            True
        )
        logger.debug(f"Memory monitoring started (interval: {MEMORY_CHECK_INTERVAL}s)")
    
    def checkMemoryUsage_(self, timer):
        """Periodic memory check callback."""
        tracker = get_memory_tracker()
        if tracker.check_and_cleanup():
            stats = tracker.get_stats()
            logger.info(f"Memory cleanup: {stats['current_mb']} MB ({stats['status']})")

    
    def _request_permissions(self):
        """Request necessary permissions (accessibility handled by onboarding)."""
        # Log current accessibility status
        is_trusted = AXIsProcessTrustedWithOptions(None)
        logger.info(f"Accessibility trusted: {is_trusted}")
        
        # Microphone (for voice features if added later)
        AVCaptureDevice.requestAccessForMediaType_completionHandler_(
            AVMediaTypeAudio,
            lambda granted: logger.info(f"Microphone access: {granted}")
        )
    
    # MARK: - Action Handlers
    
    def show_window(self):
        """Show the overlay window."""
        if self._window_manager:
            self._window_manager.showWindow()
            
            # Resume webview if it was suspended
            if self._webview_manager:
                self._webview_manager.resume()
                self._webview_manager.focus_input()
    
    def hide_window(self):
        """Hide the overlay window."""
        # Suspend webview to save memory when hidden
        if self._webview_manager:
            self._webview_manager.suspend()
        
        if self._window_manager:
            self._window_manager.hideWindow()
        
        # Run memory cleanup when hiding
        tracker = get_memory_tracker()
        freed = tracker.run_cleanup()
        if freed > 5:
            logger.debug(f"Memory cleanup freed {freed:.1f} MB")
    
    def _toggle_window(self):
        """Toggle window visibility."""
        if not self._window_manager or not self._window_manager.window:
            return
        
        window = self._window_manager.window
        
        # Check if window is actually visible (not just key)
        if window.isVisible():
            # Window is showing - hide it
            self.hide_window()
        else:
            # Window is hidden - show it
            self.show_window()
    
    def _on_service_changed(self, service_id: str):
        """Handle service change."""
        if service_id == "local_ai":
            # Load Local AI (Ollama) chat interface
            self._load_local_ai()
        elif self._webview_manager:
            # Web-based service (ChatGPT, Claude, Gemini, etc.)
            self._webview_manager.load_service(service_id)
            # Show notification
            services = self._webview_manager.get_services()
            if service_id in services:
                get_notification_manager().show_service_switch(
                    services[service_id].name, service_id
                )
    
    def _load_local_ai(self):
        """Load the Local AI (Ollama) chat interface."""
        if self._webview_manager:
            self._webview_manager.load_local_ai()
        get_notification_manager().show_service_switch("Local AI", "local_ai")
    
    def _on_transparency_changed(self, increase: bool):
        """Handle transparency change."""
        if self._window_manager:
            self._window_manager.adjust_opacity(increase)
            # Haptic feedback
            get_haptics().level_change_feedback()
            # Show notification with new opacity
            new_opacity = self._window_manager._state.opacity
            get_notification_manager().show_opacity_change(new_opacity)
    
    def _on_webview_background_change(self, color: str):
        """Handle webview background color change."""
        # Could update control bar to match
        pass
    
    def _reload_page(self):
        """Reload current page."""
        if self._webview_manager:
            self._webview_manager.reload()
            logger.info("Page reloaded")
    
    def _show_about(self):
        """Show about dialog."""
        from AppKit import NSAlert, NSInformationalAlertStyle
        from ..constants import APP_VERSION
        
        alert = NSAlert.alloc().init()
        alert.setMessageText_("OverAI")
        alert.setInformativeText_(
            f"Version {APP_VERSION}\n\n"
            "A lightweight AI overlay for macOS.\n\n"
            "Open source and free forever.\n"
            "github.com/N-Saipraveen/overai"
        )
        alert.setAlertStyle_(NSInformationalAlertStyle)
        alert.addButtonWithTitle_("OK")
        alert.runModal()
    
    def _show_settings(self):
        """Show settings panel."""
        # For now, show the API config as the main settings
        self._show_api_config()
    
    def _show_api_config(self):
        """Show API configuration dialog."""
        def on_config_complete():
            # Refresh service list
            if self._control_bar:
                self._control_bar.refresh_services()
        
        show_api_config(self._window_manager.window, on_config_complete)
    
    def _quit(self):
        """Quit application."""
        logger.info("Quitting application")
        self._cleanup()
        NSApp.terminate_(None)
    
    def _cleanup(self):
        """Clean up all resources."""
        logger.info("Cleaning up resources")
        
        # Stop memory timer
        if self._memory_timer:
            self._memory_timer.invalidate()
            self._memory_timer = None
        
        if self._keyboard_manager:
            self._keyboard_manager.cleanup()
            self._keyboard_manager = None
        
        if self._status_bar:
            self._status_bar.cleanup()
            self._status_bar = None
        
        if self._webview_manager:
            self._webview_manager.cleanup()
            self._webview_manager = None
        
        if self._window_manager:
            self._window_manager.cleanup()
            self._window_manager = None
        
        if self._lifecycle:
            self._lifecycle.shutdown()
            self._lifecycle = None
        
        # Final memory cleanup
        get_memory_tracker().run_cleanup()
        
        logger.info("Cleanup complete")
    
    # MARK: - NSResponder overrides
    
    def handleKeyEvent_(self, event):
        """Handle key events."""
        import AppKit
        
        modifiers = event.modifierFlags()
        key = event.charactersIgnoringModifiers()
        
        # Command-based shortcuts
        if modifiers & AppKit.NSCommandKeyMask:
            if key == 'h':
                self.hide_window()
                return
            elif key == 'q':
                self._quit()
                return
            elif key == 'g':
                self._go_home()
                return
            elif key == 'r':
                if self._webview_manager:
                    self._webview_manager.reload()
                return
        
        # Pass to default handler
        objc.super(AppDelegate, self).keyDown_(event)
    
    def applicationWillTerminate_(self, notification):
        """App will terminate."""
        logger.info("Application will terminate")
        self._cleanup()


# Need to import AppKit constants after class definition
import AppKit
