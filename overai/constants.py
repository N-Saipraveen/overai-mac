"""
Constants for OverAI - Centralized configuration.
"""

# Try importing Quartz constants, fallback if not available
try:
    from Quartz import (
        kCGEventFlagMaskCommand,
        kCGEventFlagMaskOption,
        kCGEventFlagMaskControl,
        kCGEventFlagMaskShift,
    )
except ImportError:
    # Fallback values
    kCGEventFlagMaskCommand = 0x100000
    kCGEventFlagMaskOption = 0x80000
    kCGEventFlagMaskControl = 0x40000
    kCGEventFlagMaskShift = 0x20000

# App Info
APP_TITLE = "OverAI"
APP_VERSION = "2.0.0"
DEFAULT_WEBSITE = "https://grok.com"

# Window Settings
CORNER_RADIUS = 12.0
DRAG_AREA_HEIGHT = 32
DEFAULT_WINDOW_SIZE = (550, 580)
DEFAULT_OPACITY = 0.9
MIN_OPACITY = 0.2
MAX_OPACITY = 1.0
OPACITY_STEP = 0.1

# File Paths (relative to package)
LOGO_WHITE_PATH = "logo/logo_white.png"
LOGO_BLACK_PATH = "logo/logo_black.png"
FRAME_SAVE_NAME = "OverAIWindowFrame"

# Hotkey Settings
DEFAULT_HOTKEY_FLAGS = kCGEventFlagMaskCommand
DEFAULT_HOTKEY_KEYCODE = 5  # 'g' key

# AI Services
AI_SERVICES = {
    "grok": {"name": "Grok", "url": "https://grok.com", "icon": "bolt.fill"},
    "chatgpt": {"name": "ChatGPT", "url": "https://chat.openai.com", "icon": "bubble.left.fill"},
    "claude": {"name": "Claude", "url": "https://claude.ai/chat", "icon": "quote.bubble.fill"},
    "gemini": {"name": "Gemini", "url": "https://gemini.google.com", "icon": "sparkles"},
    "deepseek": {"name": "DeepSeek", "url": "https://chat.deepseek.com", "icon": "magnifyingglass"},
}

# Feature Flags
ENABLE_ANIMATIONS = True
ENABLE_HAPTIC_FEEDBACK = True
ENABLE_VOICE_INPUT = True

# User Agent
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.1 Safari/605.1.15"
)

# Accessibility
ACCESSIBILITY_ENABLED = True
VOICEOVER_ANNOUNCEMENTS = True
