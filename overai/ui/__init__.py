"""
UI Components for OverAI.
"""

from .webview_manager import WebViewManager, AI_SERVICES
from .control_bar import ControlBar
from .status_bar import StatusBarManager
from .notifications import get_notification_manager, NotificationManager

__all__ = [
    "WebViewManager", "AI_SERVICES", "ControlBar", "StatusBarManager",
    "get_notification_manager", "NotificationManager"
]


