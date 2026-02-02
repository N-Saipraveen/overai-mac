"""
Accessibility support following Apple guidelines.
VoiceOver, keyboard navigation, and accessibility features.
"""

import objc
from AppKit import (
    NSView, NSButton, NSPopUpButton, NSTextField,
    NSAccessibilityRole, NSAccessibilityButtonRole,
    NSAccessibilityPopUpButtonRole, NSAccessibilityStaticTextRole,
    NSAccessibilityDescriptionAttribute
)
from Foundation import NSObject


class AccessibilityManager:
    """
    Manages accessibility features for the app.
    Ensures VoiceOver and keyboard navigation work properly.
    """
    
    def __init__(self):
        self._elements = []
    
    def configure_button(self, button: NSButton, 
                         label: str, 
                         help_text: str = None,
                         shortcut: str = None):
        """Configure button with full accessibility."""
        # Set accessibility label (what VoiceOver reads)
        button.setAccessibilityLabel_(label)
        
        # Set help text (tooltip)
        if help_text:
            button.setAccessibilityHelp_(help_text)
            button.setToolTip_(help_text)
        
        # Set role
        button.setAccessibilityRole_(NSAccessibilityButtonRole)
        
        # Add shortcut to label if provided
        if shortcut:
            full_label = f"{label}, keyboard shortcut {shortcut}"
            button.setAccessibilityLabel_(full_label)
    
    def configure_popUpButton(self, popup: NSPopUpButton, 
                              label: str,
                              help_text: str = None):
        """Configure popup button with accessibility."""
        popup.setAccessibilityLabel_(label)
        if help_text:
            popup.setAccessibilityHelp_(help_text)
            popup.setToolTip_(help_text)
        popup.setAccessibilityRole_(NSAccessibilityPopUpButtonRole)
    
    def configure_drag_area(self, view: NSView):
        """Configure drag area with accessibility."""
        view.setAccessibilityLabel_("Window drag area")
        view.setAccessibilityHelp_("Drag to move the window")
        view.setAccessibilityRole_("AXGroup")
    
    def configure_webview_container(self, view: NSView):
        """Configure webview container."""
        view.setAccessibilityLabel_("AI Chat Web View")
        view.setAccessibilityHelp_("Main content area showing AI chat interface")
    
    def is_voiceover_running(self) -> bool:
        """Check if VoiceOver is running."""
        try:
            from ApplicationServices import AXIsProcessTrusted
            # VoiceOver typically runs as VoiceOver.app
            import subprocess
            result = subprocess.run(
                ["pgrep", "-x", "VoiceOver"],
                capture_output=True
            )
            return result.returncode == 0
        except:
            return False
    
    def announce(self, message: str):
        """Announce message to VoiceOver users."""
        if self.is_voiceover_running():
            # Use AppleScript to announce
            import subprocess
            script = f'display notification "{message}" with title "OverAI"'
            subprocess.run(["osascript", "-e", script], capture_output=True)


class KeyboardNavigator:
    """
    Manages keyboard navigation for accessibility.
    Tab order and keyboard shortcuts.
    """
    
    def __init__(self):
        self._focus_order = []
        self._current_focus = 0
    
    def register_focusable(self, view, order: int):
        """Register a view in the focus order."""
        self._focus_order.append((order, view))
        self._focus_order.sort(key=lambda x: x[0])
    
    def next_focus(self):
        """Move focus to next element."""
        if not self._focus_order:
            return
        
        self._current_focus = (self._current_focus + 1) % len(self._focus_order)
        _, view = self._focus_order[self._current_focus]
        
        if hasattr(view, 'becomeFirstResponder'):
            view.becomeFirstResponder()
    
    def previous_focus(self):
        """Move focus to previous element."""
        if not self._focus_order:
            return
        
        self._current_focus = (self._current_focus - 1) % len(self._focus_order)
        _, view = self._focus_order[self._current_focus]
        
        if hasattr(view, 'becomeFirstResponder'):
            view.becomeFirstResponder()
