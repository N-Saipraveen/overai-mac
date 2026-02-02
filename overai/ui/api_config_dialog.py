"""
API Configuration Dialog for managing custom AI services.
"""

import objc
from Foundation import NSMakeRect, NSObject
from AppKit import (
    NSWindow, NSView, NSTextField, NSSecureTextField, NSButton, 
    NSPopUpButton, NSTextView, NSScrollView, NSColor, NSFont,
    NSBezelStyleRounded, NSBezelStyleRegularSquare, 
    NSWindowStyleMaskTitled, NSWindowStyleMaskClosable,
    NSModalResponseOK, NSAlert, NSAlertStyleInformational,
    NSTextFieldSquareBezel, NSViewWidthSizable, NSViewHeightSizable,
    NSViewMinYMargin
)

from ..api.api_manager import get_api_manager, PREDEFINED_APIS
from ..api.api_service import APIFormat
from ..utils.logger import Logger

logger = Logger("APIConfigDialog")


class APIConfigDialog(NSObject):
    """
    Dialog for configuring custom API services.
    """
    
    WINDOW_WIDTH = 500
    WINDOW_HEIGHT = 450
    
    def init(self):
        self = objc.super(APIConfigDialog, self).init()
        if self is None:
            return None
        
        self._window = None
        self._callback = None
        self._manager = get_api_manager()
        
        return self
    
    def show(self, parent_window=None, callback=None):
        """Show the configuration dialog."""
        self._callback = callback
        
        # Create window
        window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, self.WINDOW_WIDTH, self.WINDOW_HEIGHT),
            NSWindowStyleMaskTitled | NSWindowStyleMaskClosable,
            2,
            False
        )
        window.setTitle_("Configure API Services")
        window.center()
        window.setDelegate_(self)
        
        # Setup UI
        self._setup_ui(window)
        
        self._window = window
        
        # Show as modal
        if parent_window:
            parent_window.beginSheet_completionHandler_(window, lambda result: None)
        else:
            window.makeKeyAndOrderFront_(None)
        
        return window
    
    def _setup_ui(self, window):
        """Setup the dialog UI."""
        content = window.contentView()
        bounds = content.bounds()
        
        y_pos = bounds.size.height - 30
        
        # Title
        title = NSTextField.alloc().initWithFrame_(
            NSMakeRect(20, y_pos - 20, 460, 24)
        )
        title.setStringValue_("Add Custom AI API")
        title.setBezeled_(False)
        title.setDrawsBackground_(False)
        title.setEditable_(False)
        title.setFont_(NSFont.boldSystemFontOfSize_(16))
        content.addSubview_(title)
        
        y_pos -= 50
        
        # Service Name
        name_label = self._create_label("Service Name:", 20, y_pos)
        content.addSubview_(name_label)
        
        self._name_field = NSTextField.alloc().initWithFrame_(
            NSMakeRect(140, y_pos - 4, 340, 24)
        )
        self._name_field.setBezelStyle_(NSTextFieldSquareBezel)
        content.addSubview_(self._name_field)
        
        y_pos -= 40
        
        # API Format dropdown
        format_label = self._create_label("API Format:", 20, y_pos)
        content.addSubview_(format_label)
        
        self._format_popup = NSPopUpButton.alloc().initWithFrame_(
            NSMakeRect(140, y_pos - 4, 200, 26)
        )
        self._format_popup.setBezelStyle_(NSBezelStyleRounded)
        self._format_popup.addItemWithTitle_("OpenAI Compatible")
        self._format_popup.addItemWithTitle_("Anthropic Claude")
        self._format_popup.addItemWithTitle_("Custom")
        content.addSubview_(self._format_popup)
        
        y_pos -= 40
        
        # Base URL
        url_label = self._create_label("Base URL:", 20, y_pos)
        content.addSubview_(url_label)
        
        self._url_field = NSTextField.alloc().initWithFrame_(
            NSMakeRect(140, y_pos - 4, 340, 24)
        )
        self._url_field.setBezelStyle_(NSTextFieldSquareBezel)
        self._url_field.setStringValue_("https://api.example.com/v1")
        content.addSubview_(self._url_field)
        
        y_pos -= 40
        
        # API Key
        key_label = self._create_label("API Key:", 20, y_pos)
        content.addSubview_(key_label)
        
        self._key_field = NSSecureTextField.alloc().initWithFrame_(
            NSMakeRect(140, y_pos - 4, 340, 24)
        )
        self._key_field.setBezelStyle_(NSTextFieldSquareBezel)
        content.addSubview_(self._key_field)
        
        y_pos -= 40
        
        # Default Model
        model_label = self._create_label("Default Model:", 20, y_pos)
        content.addSubview_(model_label)
        
        self._model_field = NSTextField.alloc().initWithFrame_(
            NSMakeRect(140, y_pos - 4, 340, 24)
        )
        self._model_field.setBezelStyle_(NSTextFieldSquareBezel)
        self._model_field.setStringValue_("gpt-3.5-turbo")
        content.addSubview_(self._model_field)
        
        y_pos -= 50
        
        # Buttons
        self._test_btn = NSButton.alloc().initWithFrame_(
            NSMakeRect(20, y_pos, 100, 28)
        )
        self._test_btn.setTitle_("Test")
        self._test_btn.setBezelStyle_(NSBezelStyleRounded)
        self._test_btn.setTarget_(self)
        self._test_btn.setAction_("testConnection:")
        content.addSubview_(self._test_btn)
        
        self._add_btn = NSButton.alloc().initWithFrame_(
            NSMakeRect(280, y_pos, 90, 28)
        )
        self._add_btn.setTitle_("Add")
        self._add_btn.setBezelStyle_(NSBezelStyleRounded)
        self._add_btn.setTarget_(self)
        self._add_btn.setAction_("addService:")
        content.addSubview_(self._add_btn)
        
        cancel_btn = NSButton.alloc().initWithFrame_(
            NSMakeRect(380, y_pos, 90, 28)
        )
        cancel_btn.setTitle_("Close")
        cancel_btn.setBezelStyle_(NSBezelStyleRounded)
        cancel_btn.setTarget_(self)
        cancel_btn.setAction_("close:")
        content.addSubview_(cancel_btn)
        
        y_pos -= 40
        
        # Existing services section
        sep = NSView.alloc().initWithFrame_(
            NSMakeRect(20, y_pos, 460, 1)
        )
        sep.setWantsLayer_(True)
        sep.layer().setBackgroundColor_(NSColor.separatorColor().CGColor())
        content.addSubview_(sep)
        
        y_pos -= 30
        
        existing_label = NSTextField.alloc().initWithFrame_(
            NSMakeRect(20, y_pos, 460, 20)
        )
        existing_label.setStringValue_("Configured API Services")
        existing_label.setBezeled_(False)
        existing_label.setDrawsBackground_(False)
        existing_label.setEditable_(False)
        existing_label.setFont_(NSFont.boldSystemFontOfSize_(14))
        content.addSubview_(existing_label)
        
        # Services list
        y_pos -= 80
        self._services_list = self._create_services_list(20, y_pos, 460, 70)
        content.addSubview_(self._services_list)
    
    def _create_label(self, text, x, y):
        """Create a label."""
        label = NSTextField.alloc().initWithFrame_(
            NSMakeRect(x, y - 2, 110, 20)
        )
        label.setStringValue_(text)
        label.setBezeled_(False)
        label.setDrawsBackground_(False)
        label.setEditable_(False)
        label.setFont_(NSFont.systemFontOfSize_(12))
        return label
    
    def _create_services_list(self, x, y, width, height):
        """Create the services list view."""
        scroll = NSScrollView.alloc().initWithFrame_(
            NSMakeRect(x, y, width, height)
        )
        scroll.setHasVerticalScroller_(True)
        scroll.setBorderType_(1)  # NSBezelBorder
        
        # Container for service items
        container = NSView.alloc().initWithFrame_(
            NSMakeRect(0, 0, width - 20, height)
        )
        
        services = self._manager.get_all_services()
        y_offset = height - 30
        
        for service_id, service in services.items():
            if service_id in PREDEFINED_APIS:
                continue  # Skip predefined
            
            # Service name
            name = NSTextField.alloc().initWithFrame_(
                NSMakeRect(10, y_offset, 200, 20)
            )
            name.setStringValue_(service.name)
            name.setBezeled_(False)
            name.setDrawsBackground_(False)
            name.setEditable_(False)
            container.addSubview_(name)
            
            # Delete button
            delete_btn = NSButton.alloc().initWithFrame_(
                NSMakeRect(350, y_offset - 2, 80, 22)
            )
            delete_btn.setTitle_("Remove")
            delete_btn.setBezelStyle_(NSBezelStyleRegularSquare)
            delete_btn.setBordered_(False)
            delete_btn.setContentTintColor_(NSColor.systemRedColor())
            delete_btn.setTarget_(self)
            delete_btn.setAction_("removeService:")
            delete_btn.setTag_(hash(service_id) % 10000)  # Simple tag
            container.addSubview_(delete_btn)
            
            y_offset -= 25
        
        # Adjust container size
        if y_offset < 0:
            frame = container.frame()
            frame.size.height = height - y_offset
            container.setFrame_(frame)
        
        scroll.setDocumentView_(container)
        return scroll
    
    # MARK: - Actions
    
    def testConnection_(self, sender):
        """Test the API connection."""
        url = self._url_field.stringValue()
        key = self._key_field.stringValue()
        
        if not url:
            self._show_alert("Error", "Please enter a base URL")
            return
        
        # Create temporary service for testing
        from ..api.api_service import CustomAPIService
        
        format_map = {
            0: "openai",
            1: "anthropic",
            2: "custom"
        }
        
        temp_service = CustomAPIService(
            id="temp_test",
            name="Test",
            icon="test",
            api_format=APIFormat(format_map.get(self._format_popup.indexOfSelectedItem(), "openai")),
            base_url=url,
            requires_api_key=bool(key)
        )
        
        # Temporarily save key
        if key:
            self._manager.update_service_api_key("temp_test", key)
        
        # Test connection
        success, message = self._manager.test_connection("temp_test")
        
        # Clean up temp key
        self._manager._keychain.delete_api_key("temp_test")
        
        if success:
            self._show_alert("Success", message)
        else:
            self._show_alert("Connection Failed", message)
    
    def addService_(self, sender):
        """Add a new API service."""
        name = self._name_field.stringValue()
        url = self._url_field.stringValue()
        key = self._key_field.stringValue()
        model = self._model_field.stringValue()
        
        if not name or not url:
            self._show_alert("Error", "Please enter service name and URL")
            return
        
        format_map = {
            0: "openai",
            1: "anthropic",
            2: "custom"
        }
        api_format = format_map.get(self._format_popup.indexOfSelectedItem(), "openai")
        
        service = self._manager.add_custom_service(
            name=name,
            base_url=url,
            api_key=key,
            api_format=api_format,
            default_model=model or None
        )
        
        if service:
            self._show_alert("Success", f"Added {service.name}")
            
            # Clear fields
            self._name_field.setStringValue_("")
            self._key_field.setStringValue_("")
            
            # Refresh list
            self._services_list.removeFromSuperview()
            self._services_list = self._create_services_list(20, 70, 460, 70)
            self._window.contentView().addSubview_(self._services_list)
            
            # Notify callback
            if self._callback:
                self._callback()
        else:
            self._show_alert("Error", "Failed to add service")
    
    def removeService_(self, sender):
        """Remove a custom service."""
        # Find service by tag (simplified)
        tag = sender.tag()
        
        # For simplicity, show all custom services and let user pick
        custom = [s for s in self._manager.get_all_services().values() 
                  if s.id not in PREDEFINED_APIS]
        
        if custom:
            # Remove the first one for now (in real UI, use proper identification)
            service = custom[0]
            self._manager.remove_custom_service(service.id)
            
            # Refresh
            self._services_list.removeFromSuperview()
            self._services_list = self._create_services_list(20, 70, 460, 70)
            self._window.contentView().addSubview_(self._services_list)
            
            if self._callback:
                self._callback()
    
    def close_(self, sender):
        """Close the dialog."""
        self._window.close()
    
    def _show_alert(self, title, message):
        """Show an alert dialog."""
        alert = NSAlert.alloc().init()
        alert.setMessageText_(title)
        alert.setInformativeText_(message)
        alert.setAlertStyle_(NSAlertStyleInformational)
        alert.addButtonWithTitle_("OK")
        alert.runModal()


# Global dialog instance
_dialog_instance = None

def show_api_config(parent_window=None, on_complete=None):
    """
    Show the API configuration dialog.
    
    Args:
        parent_window: Parent window for sheet presentation
        on_complete: Callback when dialog closes
    """
    global _dialog_instance
    _dialog_instance = APIConfigDialog.alloc().init()
    return _dialog_instance.show(parent_window, on_complete)
