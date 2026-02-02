"""
Theme management following Apple Design guidelines.
Supports dynamic color adaptation and accessibility.
"""

import objc
from AppKit import (
    NSColor, NSAppearance, NSAppearanceNameAqua, NSAppearanceNameDarkAqua,
    NSNotificationCenter, NSApplication, NSVisualEffectView
)
from Foundation import NSObject


class ThemeManager(NSObject):
    """
    Manages app theme with automatic dark/light mode adaptation.
    """
    
    def init(self):
        self = objc.super(ThemeManager, self).init()
        if self is None:
            return None
        
        self._is_dark = self._detect_dark_mode()
        self._setup_observer()
        
        return self
    
    def _detect_dark_mode(self) -> bool:
        """Detect if system is in dark mode."""
        try:
            appearance = NSAppearance.currentAppearance()
            return appearance.bestMatchFromAppearancesWithNames_(
                [NSAppearanceNameAqua, NSAppearanceNameDarkAqua]
            ) == NSAppearanceNameDarkAqua
        except:
            return False
    
    def _setup_observer(self):
        """Setup observer for appearance changes."""
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(
            self,
            'appearanceChanged:',
            'AppleInterfaceThemeChangedNotification',
            None
        )
    
    def appearanceChanged_(self, notification):
        """Handle appearance change."""
        self._is_dark = self._detect_dark_mode()
    
    @property
    def is_dark_mode(self) -> bool:
        return self._is_dark
    
    # Dynamic colors that adapt automatically
    @property
    def background_color(self):
        return NSColor.windowBackgroundColor()
    
    @property
    def text_color(self):
        return NSColor.labelColor()
    
    @property
    def secondary_text_color(self):
        return NSColor.secondaryLabelColor()
    
    @property
    def accent_color(self):
        return NSColor.controlAccentColor()
    
    @property
    def separator_color(self):
        return NSColor.separatorColor()
    
    @property
    def control_background(self):
        return NSColor.controlBackgroundColor()
    
    # Drag area specific colors
    @property
    def drag_area_color(self):
        if self._is_dark:
            return NSColor.colorWithCalibratedWhite_alpha_(0.15, 0.9)
        return NSColor.colorWithCalibratedWhite_alpha_(0.95, 0.9)
