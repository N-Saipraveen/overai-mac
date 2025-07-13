

# Python libraries
import os
import sys

import objc
from AppKit import *
from AppKit import NSWindowSharingNone
from WebKit import *
from Quartz import *
from AVFoundation import AVCaptureDevice, AVMediaTypeAudio
# Accessibility prompt import with fallback
try:
    from Quartz import AXIsProcessTrustedWithOptions, kAXTrustedCheckOptionPrompt
except ImportError:
    try:
        from Quartz.CoreGraphics import AXIsProcessTrustedWithOptions, kAXTrustedCheckOptionPrompt
    except ImportError:
        AXIsProcessTrustedWithOptions = None
        kAXTrustedCheckOptionPrompt = None
from Foundation import NSObject, NSURL, NSURLRequest, NSDate
from CoreFoundation import kCFRunLoopCommonModes

# Local libraries
from .constants import (
    APP_TITLE,
    CORNER_RADIUS,
    DRAG_AREA_HEIGHT,
    LOGO_BLACK_PATH,
    LOGO_WHITE_PATH,
    FRAME_SAVE_NAME,
    STATUS_ITEM_CONTEXT,
    WEBSITE,
)
from .launcher import (
    install_startup,
    uninstall_startup,
)
from .listener import (
    global_show_hide_listener,
    load_custom_launcher_trigger,
    set_custom_launcher_trigger,
)


# Add AI service endpoints
AI_SERVICES = {
    "Grok": "https://grok.com",
    "Gemini": "https://gemini.google.com",
    "ChatGPT": "https://chat.openai.com",
    "Claude": "https://claude.ai/chat",
    "DeepSeek": "https://chat.deepseek.com",
}

# Custom window (contains entire application).
class AppWindow(NSWindow):
    # Explicitly allow key window status
    def canBecomeKeyWindow(self):
        return True

    # Required to capture "Command+..." sequences.
    def keyDown_(self, event):
        delegate = self.delegate()
        if delegate and hasattr(delegate, 'keyDown_'):
            delegate.keyDown_(event)
        else:
            # Fallback to default handling
            objc.super(AppWindow, self).keyDown_(event)


# Custom view (contains click-and-drag area on top sliver of overlay).
class DragArea(NSView):
    def initWithFrame_(self, frame):
        objc.super(DragArea, self).initWithFrame_(frame)
        self.setWantsLayer_(True)
        return self
    
    # Used to update top-bar background to (roughly) match app color.
    def setBackgroundColor_(self, color):
        self.layer().setBackgroundColor_(color.CGColor())

    # Used to capture the click-and-drag event.
    def mouseDown_(self, event):
        self.window().performWindowDragWithEvent_(event)


# The main delegate for running the overlay app.
class AppDelegate(NSObject):
    # The main application setup.
    def applicationDidFinishLaunching_(self, notification):
        # Placeholders for event tap and its run loop source
        self.eventTap = None
        self.eventTapSource = None
        # Run as accessory app
        NSApp.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
        # Create a borderless, floating, resizable window
        self.window = AppWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(500, 200, 550, 580),
            NSBorderlessWindowMask | NSResizableWindowMask,
            NSBackingStoreBuffered,
            False
        )
        self.window.setLevel_(NSFloatingWindowLevel)
        self.window.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces
            | NSWindowCollectionBehaviorStationary
        )
        # Save the last position and size
        self.window.setFrameAutosaveName_(FRAME_SAVE_NAME)
        # Create the webview for the main application.
        config = WKWebViewConfiguration.alloc().init()
        config.preferences().setJavaScriptCanOpenWindowsAutomatically_(True)
        # Initialize the WebView with a frame
        self.webview = WKWebView.alloc().initWithFrame_configuration_(
            ((0, 0), (800, 600)),  # Frame: origin (0,0), size (800x600)
            config
        )
        self.webview.setUIDelegate_(self)
        self.webview.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)  # Resizes with window
        # Set a custom user agent
        safari_user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
        self.webview.setCustomUserAgent_(safari_user_agent)
        # Make window transparent so that the corners can be rounded
        self.window.setOpaque_(False)
        self.window.setBackgroundColor_(NSColor.clearColor())
        # Prevent overlay from appearing in screenshots or screen recordings
        self.window.setSharingType_(NSWindowSharingNone)
        # Set up content view with rounded corners
        content_view = NSView.alloc().initWithFrame_(self.window.contentView().bounds())
        content_view.setWantsLayer_(True)
        content_view.layer().setCornerRadius_(CORNER_RADIUS)
        content_view.layer().setBackgroundColor_(NSColor.whiteColor().CGColor())
        self.window.setContentView_(content_view)
        # Set up drag area (top sliver, full width)
        content_bounds = content_view.bounds()
        self.drag_area = DragArea.alloc().initWithFrame_(
            NSMakeRect(0, content_bounds.size.height - DRAG_AREA_HEIGHT, content_bounds.size.width, DRAG_AREA_HEIGHT)
        )
        content_view.addSubview_(self.drag_area)
        # Add close button to the drag area
        close_button = NSButton.alloc().initWithFrame_(NSMakeRect(5, 5, 20, 20))
        close_button.setBordered_(False)
        close_button.setImage_(NSImage.imageWithSystemSymbolName_accessibilityDescription_("xmark.circle.fill", None))
        close_button.setTarget_(self)
        close_button.setAction_("hideWindow:")
        self.drag_area.addSubview_(close_button)
        # Add AI service selector dropdown
        self.ai_selector = NSPopUpButton.alloc().initWithFrame_(NSMakeRect(40, 5, 150, 20))
        for name in AI_SERVICES.keys():
            self.ai_selector.addItemWithTitle_(name)
        self.ai_selector.setTarget_(self)
        self.ai_selector.setAction_("aiServiceChanged:")
        self.drag_area.addSubview_(self.ai_selector)
        # Anchor selector to the left edge when drag area resizes
        self.ai_selector.setAutoresizingMask_(NSViewMaxXMargin)

        # Add transparency control buttons
        decrease_btn = NSButton.alloc().initWithFrame_(NSMakeRect(content_bounds.size.width - 60, 5, 20, 20))
        decrease_btn.setBordered_(False)
        decrease_btn.setImage_(NSImage.imageWithSystemSymbolName_accessibilityDescription_("minus.circle.fill", None))
        decrease_btn.setTarget_(self)
        decrease_btn.setAction_("decreaseTransparency:")
        self.drag_area.addSubview_(decrease_btn)
        # Anchor decrease button to the right edge
        decrease_btn.setAutoresizingMask_(NSViewMinXMargin)

        increase_btn = NSButton.alloc().initWithFrame_(NSMakeRect(content_bounds.size.width - 30, 5, 20, 20))
        increase_btn.setBordered_(False)
        increase_btn.setImage_(NSImage.imageWithSystemSymbolName_accessibilityDescription_("plus.circle.fill", None))
        increase_btn.setTarget_(self)
        increase_btn.setAction_("increaseTransparency:")
        self.drag_area.addSubview_(increase_btn)
        # Anchor increase button to the right edge
        increase_btn.setAutoresizingMask_(NSViewMinXMargin)
        # Update the webview sizinug and insert it below drag area.
        content_view.addSubview_(self.webview)
        self.webview.setFrame_(NSMakeRect(0, 0, content_bounds.size.width, content_bounds.size.height - DRAG_AREA_HEIGHT))
        # Contat the target website.
        url = NSURL.URLWithString_(WEBSITE)
        request = NSURLRequest.requestWithURL_(url)
        self.webview.loadRequest_(request)
        # Set up script message handler for background color changes
        configuration = self.webview.configuration()
        user_content_controller = configuration.userContentController()
        user_content_controller.addScriptMessageHandler_name_(self, "backgroundColorHandler")
        # Inject JavaScript to monitor background color changes
        script = """
            function sendBackgroundColor() {
                var bgColor = window.getComputedStyle(document.body).backgroundColor;
                window.webkit.messageHandlers.backgroundColorHandler.postMessage(bgColor);
            }
            window.addEventListener('load', sendBackgroundColor);
            new MutationObserver(sendBackgroundColor).observe(document.body, { attributes: true, attributeFilter: ['style'] });
        """
        user_script = WKUserScript.alloc().initWithSource_injectionTime_forMainFrameOnly_(script, WKUserScriptInjectionTimeAtDocumentEnd, True)
        user_content_controller.addUserScript_(user_script)
        # Create status bar item with logo
        self.status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(NSSquareStatusItemLength)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_white_path = os.path.join(script_dir, LOGO_WHITE_PATH)
        self.logo_white = NSImage.alloc().initWithContentsOfFile_(logo_white_path)
        self.logo_white.setSize_(NSSize(18, 18))
        logo_black_path = os.path.join(script_dir, LOGO_BLACK_PATH)
        self.logo_black = NSImage.alloc().initWithContentsOfFile_(logo_black_path)
        self.logo_black.setSize_(NSSize(18, 18))
        # Set the initial logo image based on the current appearance
        self.updateStatusItemImage()
        # Observe system appearance changes
        self.status_item.button().addObserver_forKeyPath_options_context_(
            self, "effectiveAppearance", NSKeyValueObservingOptionNew, STATUS_ITEM_CONTEXT
        )
        # Create status bar menu
        menu = NSMenu.alloc().init()

        # Show/Hide group
        show_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Show " + APP_TITLE, "showWindow:", "")
        show_item.setTarget_(self)
        show_item.setImage_(NSImage.imageWithSystemSymbolName_accessibilityDescription_("rectangle.on.rectangle.angled", None))
        menu.addItem_(show_item)

        hide_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Hide " + APP_TITLE, "hideWindow:", "h")
        hide_item.setTarget_(self)
        hide_item.setImage_(NSImage.imageWithSystemSymbolName_accessibilityDescription_("eye.slash", None))
        menu.addItem_(hide_item)

        menu.addItem_(NSMenuItem.separatorItem())

        # Navigation group
        home_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Home", "goToWebsite:", "g")
        home_item.setTarget_(self)
        home_item.setImage_(NSImage.imageWithSystemSymbolName_accessibilityDescription_("house", None))
        menu.addItem_(home_item)

        clear_data_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Clear Web Cache", "clearWebViewData:", "")
        clear_data_item.setTarget_(self)
        clear_data_item.setImage_(NSImage.imageWithSystemSymbolName_accessibilityDescription_("trash", None))
        menu.addItem_(clear_data_item)

        set_trigger_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Set New Trigger", "setTrigger:", "")
        set_trigger_item.setTarget_(self)
        set_trigger_item.setImage_(NSImage.imageWithSystemSymbolName_accessibilityDescription_("bolt.fill", None))
        menu.addItem_(set_trigger_item)

        menu.addItem_(NSMenuItem.separatorItem())

        # Autolaunch group
        install_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Install Autolauncher", "install:", "")
        install_item.setTarget_(self)
        install_item.setImage_(NSImage.imageWithSystemSymbolName_accessibilityDescription_("arrow.up.app", None))
        menu.addItem_(install_item)

        uninstall_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Uninstall Autolauncher", "uninstall:", "")
        uninstall_item.setTarget_(self)
        uninstall_item.setImage_(NSImage.imageWithSystemSymbolName_accessibilityDescription_("arrow.down.app", None))
        menu.addItem_(uninstall_item)

        menu.addItem_(NSMenuItem.separatorItem())

        # Quit item
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Quit", "terminate:", "q")
        quit_item.setTarget_(NSApp)
        quit_item.setImage_(NSImage.imageWithSystemSymbolName_accessibilityDescription_("power", None))
        menu.addItem_(quit_item)

        # Set the menu for the status item
        self.status_item.setMenu_(menu)
        # Add resize observer
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(
            self, 'windowDidResize:', NSWindowDidResizeNotification, self.window
        )
        # Add local mouse event monitor for left mouse down
        self.local_mouse_monitor = NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
            NSEventMaskLeftMouseDown,  # Monitor left mouse-down events
            self.handleLocalMouseEvent  # Handler method
        )
        # Create and store the event tap for key-down events
        self.eventTap = CGEventTapCreate(
            kCGHIDEventTap,
            kCGHeadInsertEventTap,
            kCGEventTapOptionDefault,
            CGEventMaskBit(kCGEventKeyDown),
            global_show_hide_listener(self),
            None
        )
        # Prompt for Accessibility if API is available
        if AXIsProcessTrustedWithOptions and kAXTrustedCheckOptionPrompt:
            AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True})
        # Prompt for microphone permission when running via Python
        AVCaptureDevice.requestAccessForMediaType_completionHandler_(
            AVMediaTypeAudio,
            lambda granted: print("Microphone access granted:", granted)
        )
        if self.eventTap:
            # Create and add the run loop source
            self.eventTapSource = CFMachPortCreateRunLoopSource(None, self.eventTap, 0)
            CFRunLoopAddSource(CFRunLoopGetCurrent(), self.eventTapSource, kCFRunLoopCommonModes)
            CGEventTapEnable(self.eventTap, True)
        else:
            print("Failed to create event tap. Check Accessibility permissions.")
        # Load the custom launch trigger if the user set it.
        load_custom_launcher_trigger()
        # Set the delegate of the window to this parent application.
        self.window.setDelegate_(self)
        # Make sure this window is shown and focused.
        self.showWindow_(None)

    # Logic to show the overlay, make it the key window, and focus on the typing area.
    def showWindow_(self, sender):
        # Debug log
        print("ShowWindow_ called via", sender)
        # Unhide and activate the app
        NSApp.unhide_(None)
        NSApp.activateIgnoringOtherApps_(True)
        # Bring window to front
        self.window.orderFront_(None)
        self.window.makeKeyAndOrderFront_(None)
        # Re-enable event tap when showing overlay
        if self.eventTap:
            CGEventTapEnable(self.eventTap, True)
        # Focus the text area
        self.webview.evaluateJavaScript_completionHandler_(
            "document.querySelector('textarea').focus();", None
        )

    # Hide the overlay and allow focus to return to the next visible application.
    def hideWindow_(self, sender):
        # Do not disable event tap when hiding overlay, so the global hotkey remains active
        NSApp.hide_(None)
    
    # Go to the default landing website for the overlay (in case accidentally navigated away).
    def goToWebsite_(self, sender):
        url = NSURL.URLWithString_(WEBSITE)
        request = NSURLRequest.requestWithURL_(url)
        self.webview.loadRequest_(request)
    
    # Clear the webview cache data (in case cookies cause errors).
    def clearWebViewData_(self, sender):
        dataStore = self.webview.configuration().websiteDataStore()
        dataTypes = WKWebsiteDataStore.allWebsiteDataTypes()
        dataStore.removeDataOfTypes_modifiedSince_completionHandler_(
            dataTypes,
            NSDate.distantPast(),
            lambda: print("Data cleared")
        )

    # Go to the default landing website for the overlay (in case accidentally navigated away).
    def install_(self, sender):
        if install_startup():
            # Exit the current process since a new one will launch.
            print("Installation successful, exiting.", flush=True)
            NSApp.terminate_(None)
        else:
            print("Installation unsuccessful.", flush=True)

    # Go to the default landing website for the overlay (in case accidentally navigated away).
    def uninstall_(self, sender):
        if uninstall_startup():
            NSApp.hide_(None)

    # Handle the 'Set Trigger' menu item click.
    def setTrigger_(self, sender):
        set_custom_launcher_trigger(self)

    # For capturing key commands while the key window (in focus).
    def keyDown_(self, event):
        modifiers = event.modifierFlags()
        key_command = modifiers & NSCommandKeyMask
        key_alt = modifiers & NSAlternateKeyMask
        key_shift = modifiers & NSShiftKeyMask
        key_control = modifiers & NSControlKeyMask
        key = event.charactersIgnoringModifiers()
        # Command (NOT alt)
        if (key_command or key_control) and (not key_alt):
            # Select all
            if key == 'a':
                self.window.firstResponder().selectAll_(None)
            # Copy
            elif key == 'c':
                self.window.firstResponder().copy_(None)
            # Cut
            elif key == 'x':
                self.window.firstResponder().cut_(None)
            # Paste
            elif key == 'v':
                self.window.firstResponder().paste_(None)
            # Hide
            elif key == 'h':
                self.hideWindow_(None)
            # Quit
            elif key == 'q':
                NSApp.terminate_(None)
            # # Undo (causes crash for some reason)
            # elif key == 'z':
            #     self.window.firstResponder().undo_(None)

    # Handler for capturing a click-and-drag event when not already the key window.
    @objc.python_method
    def handleLocalMouseEvent(self, event):
        if event.window() == self.window:
            # Get the click location in window coordinates
            click_location = event.locationInWindow()
            # Use hitTest_ to determine which view receives the click
            hit_view = self.window.contentView().hitTest_(click_location)
            # Check if the hit view is the drag area
            if hit_view == self.drag_area:
                # Bring the window to the front and make it key
                self.showWindow_(None)
                # Initiate window dragging with the event
                self.window.performWindowDragWithEvent_(event)
                return None  # Consume the event
        return event  # Pass unhandled events along

    # Handler for when the window resizes (adjusts the drag area).
    def windowDidResize_(self, notification):
        bounds = self.window.contentView().bounds()
        w, h = bounds.size.width, bounds.size.height
        self.drag_area.setFrame_(NSMakeRect(0, h - DRAG_AREA_HEIGHT, w, DRAG_AREA_HEIGHT))
        self.webview.setFrame_(NSMakeRect(0, 0, w, h - DRAG_AREA_HEIGHT))

    # Handler for setting the background color based on the web page background color.
    def userContentController_didReceiveScriptMessage_(self, userContentController, message):
        if message.name() == "backgroundColorHandler":
            bg_color_str = message.body()
            # Convert CSS color to NSColor (assuming RGB for simplicity)
            if bg_color_str.startswith("rgb") and ("(" in bg_color_str) and (")" in bg_color_str):
                rgb_values = [float(val) for val in bg_color_str[bg_color_str.index("(")+1:bg_color_str.index(")")].split(",")]
                r, g, b = [val / 255.0 for val in rgb_values[:3]]
                color = NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, 1.0)
                self.drag_area.setBackgroundColor_(color)

    # Logic for checking what color the logo in the status bar should be, and setting appropriate logo.
    def updateStatusItemImage(self):
        appearance = self.status_item.button().effectiveAppearance()
        if appearance.bestMatchFromAppearancesWithNames_([NSAppearanceNameAqua, NSAppearanceNameDarkAqua]) == NSAppearanceNameDarkAqua:
            self.status_item.button().setImage_(self.logo_white)
        else:
            self.status_item.button().setImage_(self.logo_black)

    # Observer that is triggered whenever the color of the status bar logo might need to be updated.
    def observeValueForKeyPath_ofObject_change_context_(self, keyPath, object, change, context):
        if context == STATUS_ITEM_CONTEXT and keyPath == "effectiveAppearance":
            self.updateStatusItemImage()

    # System triggered appearance changes that might affect logo color.
    def appearanceDidChange_(self, notification):
        # Update the logo image when the system appearance changes
        self.updateStatusItemImage()
    # Handler to switch AI service based on dropdown selection
    def aiServiceChanged_(self, sender):
        selected_service = sender.titleOfSelectedItem()
        url = NSURL.URLWithString_(AI_SERVICES[selected_service])
        request = NSURLRequest.requestWithURL_(url)
        self.webview.loadRequest_(request)
    # Increase overlay transparency
    def increaseTransparency_(self, sender):
        current = self.window.alphaValue()
        new_alpha = min(current + 0.1, 1.0)
        self.window.setAlphaValue_(new_alpha)

    # Decrease overlay transparency
    def decreaseTransparency_(self, sender):
        current = self.window.alphaValue()
        new_alpha = max(current - 0.1, 0.2)
        self.window.setAlphaValue_(new_alpha)

    # Automatically grant microphone permission requests from the webview
    def webView_requestMediaCapturePermissionForOrigin_initiatedByFrame_type_decisionListener_(self, webView, origin, frame, mediaType, listener):
        # Grant all media capture requests (e.g., microphone)
        listener.grant()