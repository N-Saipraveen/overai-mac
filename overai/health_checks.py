"""
Health checks and crash prevention for OverAI.
Optimized with proper error handling and resource management.
"""

import os
import sys
import time
import json
import traceback
import functools
from pathlib import Path
from typing import Callable, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from .utils.logger import Logger

logger = Logger("health_checks")

# Constants
CRASH_THRESHOLD = 3
CRASH_WINDOW_SECONDS = 60
LOG_DIR = Path.home() / "Library" / "Logs" / "OverAI"
CRASH_FILE = LOG_DIR / "crash_history.json"


@dataclass
class CrashRecord:
    """Record of a crash event."""
    timestamp: float
    exception_type: str
    message: str


class CrashHistory:
    """
    Manages crash history with proper persistence.
    """
    
    def __init__(self):
        self.crashes: list = []
        self._load()
    
    def _load(self):
        """Load crash history from disk."""
        try:
            if CRASH_FILE.exists():
                with open(CRASH_FILE, 'r') as f:
                    data = json.load(f)
                    self.crashes = [
                        CrashRecord(**record) for record in data.get('crashes', [])
                    ]
                # Clean old crashes
                self._clean_old()
        except Exception as e:
            logger.error(f"Failed to load crash history: {e}")
            self.crashes = []
    
    def _save(self):
        """Save crash history to disk."""
        try:
            CRASH_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                'crashes': [
                    asdict(crash) for crash in self.crashes
                ]
            }
            with open(CRASH_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save crash history: {e}")
    
    def _clean_old(self):
        """Remove crashes older than window."""
        cutoff = time.time() - CRASH_WINDOW_SECONDS
        self.crashes = [c for c in self.crashes if c.timestamp > cutoff]
    
    def record(self, exception_type: str, message: str):
        """Record a crash."""
        self._clean_old()
        self.crashes.append(CrashRecord(
            timestamp=time.time(),
            exception_type=exception_type,
            message=message
        ))
        self._save()
    
    def is_crash_loop(self) -> bool:
        """Check if we're in a crash loop."""
        self._clean_old()
        return len(self.crashes) >= CRASH_THRESHOLD
    
    def reset(self):
        """Clear crash history."""
        self.crashes = []
        try:
            if CRASH_FILE.exists():
                CRASH_FILE.unlink()
        except Exception as e:
            logger.error(f"Failed to reset crash history: {e}")
    
    def get_recent_count(self) -> int:
        """Get number of recent crashes."""
        self._clean_old()
        return len(self.crashes)


# Global crash history instance
_crash_history = CrashHistory()


def check_crash_loop() -> bool:
    """
    Check if we're in a crash loop.
    Returns True if safe to continue, False if should abort.
    """
    if _crash_history.is_crash_loop():
        print("\n" + "="*60)
        print("  ⚠️  CRASH LOOP DETECTED")
        print("="*60)
        print(f"\n  OverAI has crashed {_crash_history.get_recent_count()} times")
        print(f"  in the last {CRASH_WINDOW_SECONDS} seconds.")
        print("\n  To reset and try again, run:")
        print(f"    rm {CRASH_FILE}")
        print("\n  Check the log for details:")
        print(f"    {LOG_DIR}/overai.log")
        print("="*60 + "\n")
        return False
    return True


def reset_crash_counter():
    """Reset crash counter after successful run."""
    _crash_history.reset()


def health_check_decorator(func: Callable) -> Callable:
    """
    Decorator that wraps main function with health checks.
    Handles crash detection and logging.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Check for crash loop
        if not check_crash_loop():
            sys.exit(1)
        
        try:
            # Run the function
            result = func(*args, **kwargs)
            
            # Success - reset crash counter
            reset_crash_counter()
            return result
            
        except Exception as e:
            # Get exception info
            exc_type = type(e).__name__
            exc_trace = traceback.format_exc()
            
            # Log the crash
            _crash_history.record(exc_type, str(e))
            
            # Log to file
            logger.error(f"Unhandled exception: {exc_type}: {e}")
            logger.error(exc_trace)
            
            # Show error to user
            print("\n" + "="*60)
            print("  ❌ OverAI encountered an error")
            print("="*60)
            print(f"\n  Error: {exc_type}: {e}")
            print(f"\n  Details logged to:")
            print(f"    {LOG_DIR}/overai.log")
            print("="*60 + "\n")
            
            raise
    
    return wrapper
