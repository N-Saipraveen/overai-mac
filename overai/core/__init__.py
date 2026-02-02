"""
Core module for OverAI - Application architecture foundation.
"""

from .app_delegate import AppDelegate
from .window_manager import WindowManager
from .lifecycle_manager import LifecycleManager

__all__ = ["AppDelegate", "WindowManager", "LifecycleManager"]

import objc
