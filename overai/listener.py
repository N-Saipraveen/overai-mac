"""
listener.py

Handles global keyboard listening and dynamic hotkey customization for OverAI overlay.
Allows users to set their own keyboard shortcut (trigger) for toggling the OverAI window.
"""

# Python libraries
import json
import time
from pathlib import Path

# Apple libraries
from AppKit import (
    NSColor,
    NSEvent,
    NSFont,
    NSKeyDown,
    NSMakeRect,
    NSRoundedBezelStyle,
    NSTextAlignmentCenter,
    NSTextField,
    NSView,
    NSButton,
)
from Quartz import (
    CGEventCreateKeyboardEvent,
    CGEventKeyboardGetUnicodeString,
    CGEventGetFlags,
    CGEventGetIntegerValueField,
    kCGEventKeyDown,
    kCGKeyboardEventKeycode,
    NSEvent,
    NSAlternateKeyMask,
    NSCommandKeyMask,
    NSControlKeyMask,
    NSShiftKeyMask,
)

# Local libraries
from .constants import LAUNCHER_TRIGGER, LAUNCHER_TRIGGER_MASK
from .health_checks import LOG_DIR

# File for storing the custom trigger
TRIGGER_FILE = LOG_DIR / "custom_trigger.json"
SPECIAL_KEY_NAMES = {
    49: "Space", 36: "Return", 53: "Escape",
    122: "F1", 120: "F2", 99: "F3", 118: "F4",
    96: "F5", 97: "F6", 98: "F7", 100: "F8",
    101: "F9", 109: "F10", 103: "F11", 111: "F12",
    123: "Left Arrow", 124: "Right Arrow",
    125: "Down Arrow", 126: "Up Arrow"
}
handle_new_trigger = None

def load_custom_launcher_trigger():
    """Load custom launcher trigger from JSON file if it exists."""
    if TRIGGER_FILE.exists():
        try:
            with open(TRIGGER_FILE, "r") as f:
                data = json.load(f)
                launcher_trigger = {"flags": data["flags"], "key": data["key"]}
            print(f"Overwriting default with a custom OverAI launch shortcut:\n  {launcher_trigger}", flush=True)
            print(f"To return to default, delete this file:\n  {TRIGGER_FILE}", flush=True)
            LAUNCHER_TRIGGER.update(launcher_trigger)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[OverAI] Failed to load custom trigger: {e}. Using default trigger.", flush=True)

def set_custom_launcher_trigger(app):
    """Show UI to set a new global hotkey trigger."""
    app.showWindow_(None)
    print("Setting new OverAI launch shortcut. (Press keys or click Cancel to abort)", flush=True)
    # Disable the current trigger
    LAUNCHER_TRIGGER["flags"] = None
    LAUNCHER_TRIGGER["key"] = None
    # Get the content view bounds
    content_view = app.window.contentView()
    content_bounds = content_view.bounds()
    # Create the overlay view to shade the main application
    overlay_view = NSView.alloc().initWithFrame_(content_bounds)
    overlay_view.setWantsLayer_(True)
    overlay_view.layer().setBackgroundColor_(NSColor.colorWithWhite_alpha_(0.0, 0.5).CGColor())  # Semi-transparent black

    # Define container dimensions
    container_width = 400
    container_height = 200
    container_x = (content_bounds.size.width - container_width) / 2
    container_y = (content_bounds.size.height - container_height) / 2
    container_frame = NSMakeRect(container_x, container_y, container_width, container_height)
    container_view = NSView.alloc().initWithFrame_(container_frame)
    container_view.setWantsLayer_(True)
    # Slightly blueish background for OverAI branding (can tweak)
    container_view.layer().setBackgroundColor_(NSColor.colorWithCalibratedRed_green_blue_alpha_(0.12, 0.20, 0.32, 0.97).CGColor())
    container_view.layer().setCornerRadius_(12)  # Rounded corners

    # Message label
    message_label_frame = NSMakeRect(0, container_height - 60, container_width, 40)
    message_label = NSTextField.alloc().initWithFrame_(message_label_frame)
    message_label.setStringValue_("Press the new shortcut key combination now.")
    message_label.setBezeled_(False)
    message_label.setDrawsBackground_(False)
    message_label.setEditable_(False)
    message_label.setSelectable_(False)
    message_label.setAlignment_(NSTextAlignmentCenter)
    message_label.setFont_(NSFont.boldSystemFontOfSize_(17))

    # Trigger display container (light background)
    trigger_display_container_frame = NSMakeRect(60, container_height - 110, 280, 38)
    trigger_display_container = NSView.alloc().initWithFrame_(trigger_display_container_frame)
    trigger_display_container.setWantsLayer_(True)
    trigger_display_container.layer().setBackgroundColor_(NSColor.lightGrayColor().CGColor())
    trigger_display_container.layer().setCornerRadius_(7)

    # Trigger display (shows "Waiting..." or key combo)
    trigger_display_frame = NSMakeRect(0, -10, 280, 38)
    trigger_display = NSTextField.alloc().initWithFrame_(trigger_display_frame)
    trigger_display.setStringValue_("Waiting for key press...")
    trigger_display.setBezeled_(False)
    trigger_display.setDrawsBackground_(False)
    trigger_display.setEditable_(False)
    trigger_display.setSelectable_(False)
    trigger_display.setAlignment_(NSTextAlignmentCenter)
    trigger_display.setFont_(NSFont.systemFontOfSize_(16))

    # Cancel Button
    cancel_button_frame = NSMakeRect(container_width / 2 - 40, 20, 80, 32)
    cancel_button = NSButton.alloc().initWithFrame_(cancel_button_frame)
    cancel_button.setTitle_("Cancel")
    cancel_button.setBezelStyle_(NSRoundedBezelStyle)
    def cancel_action(sender):
        print("Cancelled custom shortcut selection.", flush=True)
        overlay_view.removeFromSuperview()
        global handle_new_trigger
        handle_new_trigger = None
        app.showWindow_(None)
    cancel_button.setTarget_(cancel_action)
    cancel_button.setAction_("callWithSender:")

    # Assemble hierarchy
    trigger_display_container.addSubview_(trigger_display)
    container_view.addSubview_(message_label)
    container_view.addSubview_(trigger_display_container)
    container_view.addSubview_(cancel_button)
    overlay_view.addSubview_(container_view)
    content_view.addSubview_(overlay_view)

    # Handler for new trigger
    def custom_handle_new_trigger(event, flags, keycode):
        launcher_trigger = {"flags": flags, "key": keycode}
        with open(TRIGGER_FILE, "w") as f:
            json.dump(launcher_trigger, f)
        LAUNCHER_TRIGGER.update(launcher_trigger)
        trigger_str = get_trigger_string(event, flags, keycode)
        print("New OverAI launch shortcut set:", flush=True)
        print(f"  {launcher_trigger}", flush=True)
        print(f"  {trigger_str}", flush=True)
        trigger_display.setStringValue_(trigger_str)
        # Remove overlay after 2 seconds
        overlay_view.performSelector_withObject_afterDelay_("removeFromSuperview", None, 2.0)
        global handle_new_trigger
        handle_new_trigger = None
        app.showWindow_(None)
        return None

    # Set the global handler
    global handle_new_trigger
    handle_new_trigger = custom_handle_new_trigger

def get_modifier_names(flags):
    """Helper to get modifier names as list."""
    modifier_names = []
    if flags & NSShiftKeyMask:
        modifier_names.append("Shift")
    if flags & NSControlKeyMask:
        modifier_names.append("Control")
    if flags & NSAlternateKeyMask:
        modifier_names.append("Option")
    if flags & NSCommandKeyMask:
        modifier_names.append("Command")
    return modifier_names

def get_trigger_string(event, flags, keycode):
    """Return a human-readable string for the trigger."""
    modifier_names = get_modifier_names(flags)
    if keycode in SPECIAL_KEY_NAMES:
        key_name = SPECIAL_KEY_NAMES[keycode]
    else:
        key_name = NSEvent.eventWithCGEvent_(event).characters()
    return " + ".join(modifier_names + [key_name]) if modifier_names else key_name

def global_show_hide_listener(app):
    """Global event listener for showing/hiding OverAI and for new trigger assignment."""
    def listener(proxy, event_type, event, refcon):
        if event_type == kCGEventKeyDown:
            keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
            flags = CGEventGetFlags(event)
            # Debug print for key/flag detection
            print("Key event detected:", keycode, "flags:", flags, "trigger:", LAUNCHER_TRIGGER)
            if (None in set(LAUNCHER_TRIGGER.values())) and handle_new_trigger:
                print("  Received keys, establishing new shortcut..", flush=True)
                handle_new_trigger(event, flags, keycode)
                return None
            # Use bitwise AND for modifier matching (CMD + G etc)
            elif keycode == LAUNCHER_TRIGGER["key"] and (flags & LAUNCHER_TRIGGER["flags"]) == LAUNCHER_TRIGGER["flags"]:
                if app.window.isKeyWindow():
                    app.hideWindow_(None)
                else:
                    app.showWindow_(None)
                return None
        return event
    return listener