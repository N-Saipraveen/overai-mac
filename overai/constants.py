# Apple libraries
from Quartz import (
    kCGEventFlagMaskAlternate,
    kCGEventFlagMaskCommand,
    kCGEventFlagMaskControl,
    kCGEventFlagMaskShift,
)

# Main settings and constants for OverAI
WEBSITE = "https://www.grok.com"  
LOGO_WHITE_PATH = "logo/logo_white.png"
LOGO_BLACK_PATH = "logo/logo_black.png"
FRAME_SAVE_NAME = "OverAIWindowFrame"
APP_TITLE = "OverAI"
PERMISSION_CHECK_EXIT = 1
CORNER_RADIUS = 15.0
DRAG_AREA_HEIGHT = 30
STATUS_ITEM_CONTEXT = 1

# Hotkey config: Command+G (key 5 is "g" in macOS virtual keycodes)
LAUNCHER_TRIGGER_MASK = kCGEventFlagMaskCommand
LAUNCHER_TRIGGER = {
    "flags": kCGEventFlagMaskCommand,
    "key": 5  # 'g' key
}
