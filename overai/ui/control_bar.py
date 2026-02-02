"""
Control bar with accessible, Apple Design-compliant controls.
Uses manual layout for reliable resizing.
"""

import objc
from Foundation import NSMakeRect, NSUserDefaults
from AppKit import (
    NSView, NSButton, NSPopUpButton, NSColor,
    NSBezelStyleRounded, NSBezelStyleRegularSquare,
    NSImage
)

from ..utils.logger import Logger
from ..utils.theme import ThemeManager
from ..utils.accessibility import AccessibilityManager
from ..utils.haptics import get_haptics
from .notifications import get_notification_manager
from ..api.api_manager import get_api_manager

logger = Logger("ControlBar")

# Key for storing last used service
LAST_SERVICE_KEY = "com.overai.lastService"


class ControlBar(NSView):
    """
    Accessible control bar for the overlay window.
    All controls maintain their positions during window resize.
    """
    
    HEIGHT = 38.0
    
    # Layout constants
    LEFT_MARGIN = 12
    RIGHT_MARGIN = 12
    BUTTON_SIZE = 20
    BUTTON_SPACING = 28
    SERVICE_SELECTOR_WIDTH = 110
    
    def initWithFrame_(self, frame):
        self = objc.super(ControlBar, self).initWithFrame_(frame)
        if self is None:
            return None
        
        self._theme = ThemeManager()
        self._accessibility = AccessibilityManager()
        self._service_changed_callback = None
        self._transparency_callback = None
        self._close_callback = None
        self._quit_callback = None
        
        # Control references
        self._close_btn = None
        self._service_popup = None
        self._decrease_btn = None
        self._increase_btn = None
        self._quit_btn = None
        self._bottom_border = None
        
        # Disable autoresizing for subviews - we handle layout manually
        self.setAutoresizesSubviews_(False)
        
        # Callback for API config
        self._api_config_callback = None
        
        self._setup_ui()
        
        return self
    
    def _setup_ui(self):
        """Create all UI components."""
        bounds = self.bounds()
        
        # Clear background
        self.setWantsLayer_(True)
        self.layer().setBackgroundColor_(NSColor.clearColor().CGColor())
        
        # Bottom border (full width)
        self._bottom_border = self._create_border(
            NSMakeRect(0, 0, bounds.size.width, 1)
        )
        self.addSubview_(self._bottom_border)
        
        # Left side controls
        self._close_btn = self._create_button(
            NSMakeRect(self.LEFT_MARGIN, 9, self.BUTTON_SIZE, self.BUTTON_SIZE),
            "xmark.circle.fill",
            "closeClicked:",
            "Hide window",
            "Hide the OverAI overlay window",
            "Command+H"
        )
        self.addSubview_(self._close_btn)
        
        # Service selector
        self._service_popup = NSPopUpButton.alloc().initWithFrame_(
            NSMakeRect(self.LEFT_MARGIN + 24 + 4, 7, self.SERVICE_SELECTOR_WIDTH + 20, 24)
        )
        self._service_popup.setBezelStyle_(NSBezelStyleRounded)
        
        self._refresh_service_menu()
        
        self._service_popup.setTarget_(self)
        self._service_popup.setAction_("serviceChanged:")
        self._accessibility.configure_popUpButton(
            self._service_popup, "AI Service Selector", "Select which AI service to use"
        )
        self.addSubview_(self._service_popup)
        
        # Right side controls (will be positioned in layout)
        self._decrease_btn = self._create_button(
            NSMakeRect(0, 9, self.BUTTON_SIZE, self.BUTTON_SIZE),  # Position set in layout
            "minus.circle",
            "decreaseOpacity:",
            "Decrease transparency",
            "Make window more transparent"
        )
        self.addSubview_(self._decrease_btn)
        
        self._increase_btn = self._create_button(
            NSMakeRect(0, 9, self.BUTTON_SIZE, self.BUTTON_SIZE),  # Position set in layout
            "plus.circle",
            "increaseOpacity:",
            "Increase transparency",
            "Make window less transparent"
        )
        self.addSubview_(self._increase_btn)
        
        self._quit_btn = self._create_button(
            NSMakeRect(0, 9, self.BUTTON_SIZE, self.BUTTON_SIZE),  # Position set in layout
            "power",
            "quitClicked:",
            "Quit application",
            "Quit OverAI completely",
            "Command+Q"
        )
        self._quit_btn.setContentTintColor_(NSColor.systemRedColor())
        self.addSubview_(self._quit_btn)
        
        # Initial layout
        self._layout_controls(self.bounds().size.width)
    
    def _create_border(self, frame):
        """Create a separator border."""
        border = NSView.alloc().initWithFrame_(frame)
        border.setWantsLayer_(True)
        border.layer().setBackgroundColor_(NSColor.separatorColor().CGColor())
        return border
    
    def _create_button(self, frame, icon, action, label, help_text=None, shortcut=None):
        """Create an icon button."""
        btn = NSButton.alloc().initWithFrame_(frame)
        btn.setBezelStyle_(NSBezelStyleRegularSquare)
        btn.setBordered_(False)
        
        image = NSImage.imageWithSystemSymbolName_accessibilityDescription_(icon, label)
        if image:
            image.setSize_((16, 16))
            btn.setImage_(image)
        
        btn.setTarget_(self)
        btn.setAction_(action)
        self._accessibility.configure_button(btn, label, help_text, shortcut)
        return btn
    
    def _layout_controls(self, width):
        """Position all controls based on current width."""
        # Right side buttons - anchored to right edge
        right_x = width - self.RIGHT_MARGIN - self.BUTTON_SIZE
        
        frame = self._quit_btn.frame()
        frame.origin.x = right_x
        self._quit_btn.setFrame_(frame)
        
        right_x -= self.BUTTON_SPACING
        frame = self._increase_btn.frame()
        frame.origin.x = right_x
        self._increase_btn.setFrame_(frame)
        
        right_x -= self.BUTTON_SPACING
        frame = self._decrease_btn.frame()
        frame.origin.x = right_x
        self._decrease_btn.setFrame_(frame)
        
        # Bottom border - full width
        frame = self._bottom_border.frame()
        frame.size.width = width
        self._bottom_border.setFrame_(frame)
    
    def resizeSubviewsWithOldSize_(self, old_size):
        """Called when view is resized - reposition right-side controls."""
        new_width = self.bounds().size.width
        self._layout_controls(new_width)
    
    def setFrame_(self, frame):
        """Handle frame changes."""
        objc.super(ControlBar, self).setFrame_(frame)
        self._layout_controls(frame.size.width)
    
    def _get_services(self):
        """Get available services including API-based ones."""
        from .webview_manager import AI_SERVICES
        
        # Combine web services with API services
        all_services = dict(AI_SERVICES)
        
        # Add API services
        api_manager = get_api_manager()
        for service_id, service in api_manager.get_all_services().items():
            # Convert API service to webview service format
            from .webview_manager import AIService
            all_services[service_id] = AIService(
                name=service.name,
                url="about:blank",  # API services use blank page
                icon=service.icon
            )
        
        return all_services
    
    # MARK: - Actions
    
    def closeClicked_(self, sender):
        if self._close_callback:
            self._close_callback()
    
    def quitClicked_(self, sender):
        if self._quit_callback:
            self._quit_callback()
    
    def serviceChanged_(self, sender):
        selected_item = sender.selectedItem()
        if not selected_item:
            return
        
        service_id = selected_item.representedObject()
        
        # Check for Custom API option
        if service_id == "custom_api":
            # Reset to previous selection
            if self._service_popup.numberOfItems() > 0:
                self._service_popup.selectItemAtIndex_(0)
            
            # Open API config
            if self._api_config_callback:
                get_haptics().level_change_feedback()
                self._api_config_callback()
            return
        
        if service_id and self._service_changed_callback:
            # Save as last used service
            self._save_last_service(service_id)
            # Haptic feedback
            get_haptics().level_change_feedback()
            # Callback
            self._service_changed_callback(service_id)
            # Show notification
            service_name = selected_item.title()
            get_notification_manager().show_service_switch(service_name, service_id)
    
    def decreaseOpacity_(self, sender):
        if self._transparency_callback:
            get_haptics().level_change_feedback()
            self._transparency_callback(False)
    
    def increaseOpacity_(self, sender):
        if self._transparency_callback:
            get_haptics().level_change_feedback()
            self._transparency_callback(True)
    
    # MARK: - Callbacks
    
    def on_service_changed(self, callback):
        self._service_changed_callback = callback
    
    def on_transparency_changed(self, callback):
        self._transparency_callback = callback
    
    def on_close(self, callback):
        self._close_callback = callback
    
    def on_quit(self, callback):
        self._quit_callback = callback
    
    def on_api_config(self, callback):
        """Set callback for API configuration."""
        self._api_config_callback = callback
    
    def refresh_services(self):
        """Refresh the service dropdown (called after API config changes)."""
        # Save current selection
        current = None
        if self._service_popup.indexOfSelectedItem() >= 0:
            item = self._service_popup.selectedItem()
            if item:
                current = item.representedObject()
        
        # Clear and rebuild
        self._service_popup.removeAllItems()
        self._refresh_service_menu()
        
        # Restore selection if possible
        if current:
            self.set_selected_service(current)
    
    def _refresh_service_menu(self):
        """Rebuild the service menu with web services and Local AI."""
        from .webview_manager import AI_SERVICES
        from AppKit import NSMenuItem
        
        # Web Services first
        for service_id, service in AI_SERVICES.items():
            self._service_popup.addItemWithTitle_(service.name)
            item = self._service_popup.lastItem()
            item.setRepresentedObject_(service_id)
        
        # Add proper separator
        self._service_popup.menu().addItem_(NSMenuItem.separatorItem())
        
        # Local AI (Ollama) option
        self._service_popup.addItemWithTitle_("🏠 Local AI")
        item = self._service_popup.lastItem()
        item.setRepresentedObject_("local_ai")
    
    def set_selected_service(self, service_id):
        """Set the selected service."""
        for i in range(self._service_popup.numberOfItems()):
            item = self._service_popup.itemAtIndex_(i)
            if item.representedObject() == service_id:
                self._service_popup.selectItemAtIndex_(i)
                break
    
    def _save_last_service(self, service_id):
        """Save last used service to UserDefaults."""
        try:
            defaults = NSUserDefaults.standardUserDefaults()
            defaults.setObject_forKey_(service_id, LAST_SERVICE_KEY)
            defaults.synchronize()
            logger.debug(f"Saved last service: {service_id}")
        except Exception as e:
            logger.error(f"Failed to save last service: {e}")
    
    def get_last_service(self):
        """Get the last used service from UserDefaults."""
        try:
            defaults = NSUserDefaults.standardUserDefaults()
            service_id = defaults.stringForKey_(LAST_SERVICE_KEY)
            return service_id if service_id else "chatgpt"  # Default to ChatGPT
        except Exception:
            return "chatgpt"
    
    def select_last_service(self):
        """Select and return the last used service. Call after setup."""
        service_id = self.get_last_service()
        self.set_selected_service(service_id)
        logger.info(f"Restored last service: {service_id}")
        return service_id

