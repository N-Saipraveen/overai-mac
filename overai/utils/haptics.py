"""
Haptic feedback manager for trackpad interactions.
Uses NSHapticFeedbackManager for Force Touch trackpads.
"""

import objc
from AppKit import NSHapticFeedbackManager, NSHapticFeedbackPatternAlignment, NSHapticFeedbackPatternLevelChange

from .logger import Logger

logger = Logger("Haptics")


class HapticFeedbackManager:
    """
    Provides haptic feedback for UI interactions.
    Falls back gracefully on non-Force Touch trackpads.
    """
    
    def __init__(self):
        self._feedback_performer = None
        self._initialize()
    
    def _initialize(self):
        """Initialize the haptic feedback performer."""
        try:
            # Get the default haptic feedback manager
            manager = NSHapticFeedbackManager.defaultHapticFeedbackManager()
            if manager:
                self._feedback_performer = manager
                logger.debug("Haptic feedback initialized")
        except Exception as e:
            logger.debug(f"Haptic feedback not available: {e}")
    
    def alignment_feedback(self):
        """
        Provides alignment feedback - used for snap-to points.
        Good for opacity adjustments reaching min/max.
        """
        if self._feedback_performer:
            try:
                self._feedback_performer.performFeedbackPattern_performancer_(
                    NSHapticFeedbackPatternAlignment,
                    None
                )
            except Exception as e:
                logger.debug(f"Alignment feedback failed: {e}")
    
    def level_change_feedback(self):
        """
        Provides level change feedback - used for discrete value changes.
        Good for service switching or opacity steps.
        """
        if self._feedback_performer:
            try:
                self._feedback_performer.performFeedbackPattern_performancer_(
                    NSHapticFeedbackPatternLevelChange,
                    None
                )
            except Exception as e:
                logger.debug(f"Level change feedback failed: {e}")
    
    def generic_feedback(self):
        """Generic feedback for general interactions."""
        self.level_change_feedback()


# Global instance
_haptics = None

def get_haptics() -> HapticFeedbackManager:
    """Get the global haptic feedback manager."""
    global _haptics
    if _haptics is None:
        _haptics = HapticFeedbackManager()
    return _haptics
