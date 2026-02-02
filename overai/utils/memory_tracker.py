"""
Memory tracking and pressure detection with singleton pattern and cleanup handlers.
Optimized for low-RAM usage in macOS menu bar applications.
"""

import os
import gc
import weakref
from typing import Optional, Callable, List

# Try to import psutil, fallback to basic measurement
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


# Singleton instance
_memory_tracker: Optional['MemoryTracker'] = None


def get_memory_tracker() -> 'MemoryTracker':
    """Get the singleton MemoryTracker instance."""
    global _memory_tracker
    if _memory_tracker is None:
        _memory_tracker = MemoryTracker()
    return _memory_tracker


class MemoryTracker:
    """
    Tracks memory usage and detects pressure for cleanup.
    Uses singleton pattern - access via get_memory_tracker().
    """
    
    # Thresholds in MB - lowered for menu bar app
    WARNING_THRESHOLD = 200   # 200MB - start cleanup
    CRITICAL_THRESHOLD = 400  # 400MB - aggressive cleanup
    
    def __init__(self):
        self._process = None
        if HAS_PSUTIL:
            self._process = psutil.Process(os.getpid())
        self._last_memory_mb = 0.0
        self._cleanup_handlers: List[weakref.ref] = []
    
    def get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        try:
            if self._process:
                info = self._process.memory_info()
                return info.rss / (1024 * 1024)
            else:
                # Fallback: use resource module
                import resource
                usage = resource.getrusage(resource.RUSAGE_SELF)
                return usage.ru_maxrss / (1024 * 1024)  # Convert to MB
        except Exception:
            return 0.0
    
    def register_cleanup_handler(self, handler: Callable[[], None]) -> None:
        """
        Register a cleanup handler to be called on memory pressure.
        Uses weak references to avoid preventing garbage collection.
        """
        # Store as weak reference if possible
        try:
            ref = weakref.ref(handler.__self__, self._remove_dead_refs)
            self._cleanup_handlers.append((ref, handler.__name__))
        except (AttributeError, TypeError):
            # Not a bound method, store directly
            self._cleanup_handlers.append((None, handler))
    
    def _remove_dead_refs(self, ref):
        """Remove dead weak references."""
        self._cleanup_handlers = [
            (r, h) for r, h in self._cleanup_handlers 
            if r is None or r() is not None
        ]
    
    def should_cleanup(self) -> bool:
        """Check if memory cleanup should be triggered."""
        current = self.get_memory_usage_mb()
        
        # Trigger cleanup if above warning threshold
        if current > self.WARNING_THRESHOLD:
            return True
        
        # Also cleanup if memory increased significantly (>50MB) since last check
        if current - self._last_memory_mb > 50:
            self._last_memory_mb = current
            return True
        
        self._last_memory_mb = current
        return False
    
    def is_critical(self) -> bool:
        """Check if memory is at critical level."""
        return self.get_memory_usage_mb() > self.CRITICAL_THRESHOLD
    
    def run_cleanup(self) -> float:
        """
        Run all registered cleanup handlers and garbage collection.
        Returns the amount of memory freed in MB.
        """
        before = self.get_memory_usage_mb()
        
        # Call registered cleanup handlers
        for ref_or_handler, name_or_func in self._cleanup_handlers[:]:
            try:
                if ref_or_handler is None:
                    # Direct function reference
                    name_or_func()
                else:
                    # Weak reference to object
                    obj = ref_or_handler()
                    if obj is not None:
                        getattr(obj, name_or_func)()
            except Exception:
                pass  # Don't let one handler break others
        
        # Force garbage collection - all generations
        gc.collect(2)
        gc.collect(1) 
        gc.collect(0)
        
        after = self.get_memory_usage_mb()
        self._last_memory_mb = after
        
        return before - after
    
    def force_cleanup(self) -> None:
        """Force garbage collection and memory cleanup (legacy method)."""
        self.run_cleanup()
    
    def check_and_cleanup(self) -> bool:
        """
        Check memory and cleanup if needed.
        Returns True if cleanup was performed.
        """
        if self.should_cleanup():
            freed = self.run_cleanup()
            return freed > 0
        return False
    
    def get_stats(self) -> dict:
        """Get memory statistics."""
        current = self.get_memory_usage_mb()
        return {
            'current_mb': round(current, 1),
            'warning_threshold': self.WARNING_THRESHOLD,
            'critical_threshold': self.CRITICAL_THRESHOLD,
            'status': 'critical' if current > self.CRITICAL_THRESHOLD 
                     else 'warning' if current > self.WARNING_THRESHOLD 
                     else 'normal',
            'handlers_count': len(self._cleanup_handlers)
        }
