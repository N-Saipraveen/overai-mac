"""
Lifecycle Manager - Handles app state, memory pressure, and background/foreground transitions.
Uses modern macOS lifecycle patterns with proper cleanup.
"""

import signal
from typing import Optional, Callable
from Foundation import NSObject, NSTimer, NSNotificationCenter, NSApplication
from AppKit import NSApplicationDidBecomeActiveNotification, NSApplicationDidResignActiveNotification

from ..utils.memory_tracker import MemoryTracker
from ..utils.logger import Logger

logger = Logger("LifecycleManager")


class LifecycleManager(NSObject):
    """
    Manages application lifecycle events with proper memory management.
    """
    
    def init(self):
        self = objc.super(LifecycleManager, self).init()
        if self is None:
            return None
            
        self._observers = []
        self._timers = []
        self._memory_tracker = MemoryTracker()
        self._is_active = False
        self._cleanup_handlers = []
        
        return self
    
    def setupLifecycle(self):
        """Setup lifecycle observers."""
        nc = NSNotificationCenter.defaultCenter()
        
        # App became active - use selector-based observer (no weak refs needed)
        did_become_observer = nc.addObserver_selector_name_object_(
            self,
            "handleBecomeActive:",
            NSApplicationDidBecomeActiveNotification,
            None
        )
        self._observers.append(did_become_observer)
        
        # App resigned active
        did_resign_observer = nc.addObserver_selector_name_object_(
            self,
            "handleResignActive:",
            NSApplicationDidResignActiveNotification,
            None
        )
        self._observers.append(did_resign_observer)
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)
        
        # Memory pressure timer - check every 30 seconds
        self._setup_memory_timer()
        
        logger.info("Lifecycle manager initialized")
    
    def _setup_memory_timer(self):
        """Setup periodic memory check timer (less frequent to save CPU)."""
        timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            60.0,  # Check every 60 seconds instead of 30
            self,
            "handleMemoryCheck:",
            None,
            True
        )
        self._timers.append(timer)
    
    def handleMemoryCheck_(self, timer):
        """Handle periodic memory check."""
        if self._memory_tracker.should_cleanup():
            logger.debug("Memory pressure detected, triggering cleanup")
            self._perform_cleanup()
    
    def handleBecomeActive_(self, notification):
        """App became active - resume operations."""
        self._is_active = True
        logger.debug("App became active")
    
    def handleResignActive_(self, notification):
        """App resigned active - for accessory apps this is normal."""
        self._is_active = False
        logger.debug("App resigned active")
        # NOTE: Don't cleanup here! LSUIElement apps resign immediately
        # Only cleanup on actual memory pressure, not on resign active
    
    def _handle_signal(self, signum, frame):
        """Handle termination signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down gracefully")
        self.shutdown()
        NSApplication.sharedApplication().terminate_(None)
    
    def register_cleanup_handler(self, handler: Callable):
        """Register a cleanup handler to be called during memory pressure."""
        self._cleanup_handlers.append(handler)
    
    def _perform_cleanup(self):
        """Perform memory cleanup."""
        logger.debug("Performing memory cleanup")
        for handler in self._cleanup_handlers:
            try:
                handler()
            except Exception as e:
                logger.error(f"Cleanup handler failed: {e}")
    
    def shutdown(self):
        """Graceful shutdown - clean up all resources."""
        logger.info("Shutting down lifecycle manager")
        
        # Invalidate all timers
        for timer in self._timers:
            timer.invalidate()
        self._timers.clear()
        
        # Remove notification observers
        nc = NSNotificationCenter.defaultCenter()
        for observer in self._observers:
            nc.removeObserver_(observer)
        self._observers.clear()
        
        # Run cleanup handlers
        self._perform_cleanup()
        self._cleanup_handlers.clear()


# Import objc at the end to avoid circular imports
import objc
