# OverAI Development Guide

This document provides essential information for AI agents and developers working on the OverAI codebase.

## Project Overview

OverAI is a macOS overlay application providing quick access to AI chat services. It's built with:
- Python 3.9+
- PyObjC for macOS framework access
- Native AppKit/WebKit for UI

## Architecture

### Core Philosophy

1. **Memory Efficiency**: Use weak references, lazy loading, and periodic cleanup
2. **Accessibility First**: All UI components must support VoiceOver and keyboard navigation
3. **Apple Design Compliance**: Follow HIG, use system colors, support dark mode
4. **State Persistence**: Save/restore user preferences and window state

### Module Structure

```
overai/
├── core/              # Application foundation
│   ├── app_delegate.py       # NSApplicationDelegate - main controller
│   ├── window_manager.py     # NSWindow management with state restoration
│   └── lifecycle_manager.py  # App lifecycle, memory pressure handling
├── ui/                # UI components
│   ├── webview_manager.py    # WKWebView wrapper with lazy loading
│   ├── control_bar.py        # Title bar controls (accessible)
│   └── status_bar.py         # NSStatusItem (menu bar)
└── utils/             # Utilities
    ├── logger.py             # File and console logging
    ├── theme.py              # Dynamic color adaptation
    ├── accessibility.py      # VoiceOver, keyboard nav
    ├── keyboard.py           # Global hotkey management
    └── memory_tracker.py     # Memory usage monitoring
```

## Development Guidelines

### Memory Management

Always use weak references to avoid retain cycles:

```python
import weakref

class MyClass:
    def __init__(self):
        self._weak_self = weakref.ref(self)
    
    def setup_observer(self):
        # Use weak reference in callbacks
        weak_self = self._weak_self
        observer = nc.addObserverForName_object_queue_usingBlock_(
            notification_name,
            None, None,
            lambda n: weak_self()._handle() if weak_self() else None
        )
```

### Accessibility Requirements

Every UI element must have:
1. **Label** - What VoiceOver reads
2. **Help text** - Detailed description
3. **Role** - Appropriate NSAccessibilityRole

```python
from overai.utils.accessibility import AccessibilityManager

accessibility = AccessibilityManager()
accessibility.configure_button(
    button,
    label="Close window",
    help_text="Hide the OverAI overlay",
    shortcut="Command+H"
)
```

### Error Handling

Use the logger for all logging:

```python
from overai.utils.logger import Logger

logger = Logger("ModuleName")

try:
    risky_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}")
    # Handle gracefully
```

### Configuration

Store user preferences in `~/Library/Application Support/OverAI/`:

```python
from pathlib import Path

CONFIG_DIR = Path.home() / "Library" / "Application Support" / "OverAI"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
```

Logs go to `~/Library/Logs/OverAI/`.

## Key Classes

### AppDelegate (core/app_delegate.py)

Main application controller. Responsibilities:
- Initialize all components
- Handle app lifecycle events
- Coordinate between modules
- Handle global keyboard shortcuts

### WindowManager (core/window_manager.py)

Manages the overlay window:
- Frameless, floating, borderless window
- State restoration (position, size, opacity)
- Animation support
- Proper cleanup

### WebViewManager (ui/webview_manager.py)

Manages WKWebView:
- Lazy loading
- Service switching
- Non-persistent data store (privacy)
- JavaScript injection for theme detection

### KeyboardManager (utils/keyboard.py)

Global hotkey handling:
- CGEventTap for global shortcuts
- Configurable hotkey
- Debouncing to prevent rapid triggers

## Testing

### Syntax Check

```bash
python3 -m py_compile overai/core/window_manager.py
```

### Import Check

```bash
python3 -c "from overai.main import main; print('OK')"
```

### Full Build

```bash
python setup.py py2app
```

## Common Tasks

### Adding a New AI Service

1. Edit `overai/ui/webview_manager.py`:
```python
AI_SERVICES = {
    "newservice": AIService(
        name="New Service",
        url="https://example.com",
        icon="symbol.name"
    ),
    # ...
}
```

2. Update `overai/constants.py` for consistency

### Adding a Menu Item

Edit `overai/ui/status_bar.py`:

```python
def _create_menu(self):
    # ... existing items ...
    self._add_menu_item(
        "New Action",
        "new_action:",
        "symbol.name",
        shortcut="n"
    )

def new_action_(self, sender):
    if self._callbacks['new_action']:
        self._callbacks['new_action']()
```

### Adding Keyboard Shortcut

Edit `overai/core/app_delegate.py`:

```python
def handleKeyEvent_(self, event):
    modifiers = event.modifierFlags()
    key = event.charactersIgnoringModifiers()
    
    if modifiers & AppKit.NSCommandKeyMask:
        if key == 'n':
            self._new_action()
            return
```

## Debugging

### Enable Debug Logging

Set in `overai/utils/logger.py`:
```python
_MIN_LEVEL = LogLevel.DEBUG
```

### View Logs

```bash
tail -f ~/Library/Logs/OverAI/overai.log
```

### Reset All State

```bash
rm -rf ~/Library/Application\ Support/OverAI
rm -rf ~/Library/Logs/OverAI
```

## Performance Tips

1. **Lazy Loading**: Don't create WebView until needed
2. **Timer Management**: Always invalidate timers in cleanup
3. **Notification Observers**: Remove in dealloc/cleanup
4. **Image Caching**: Load icons once, reuse
5. **Memory Pressure**: Respond to system warnings

## Security Considerations

1. User agent matches modern Safari
2. Non-persistent WebView data store
3. No external network calls from Python
4. Sandboxed WebView configuration

## macOS Version Support

- Minimum: macOS 11.0 (Big Sur)
- Recommended: macOS 13.0+ (Ventura)
- Tested on: macOS 14.x (Sonoma)

## Troubleshooting Common Issues

### Event tap not working
- Check Accessibility permissions
- Ensure app is in `/Applications` if sandboxed

### Window not visible
- Check `NSFloatingWindowLevel` is set
- Verify window is ordered front

### High memory usage
- Check for retain cycles with `objgraph`
- Verify WebView cleanup on service change
- Monitor with `memory_tracker`

## References

- [Apple HIG](https://developer.apple.com/design/human-interface-guidelines/)
- [PyObjC Docs](https://pyobjc.readthedocs.io/)
- [AppKit Framework](https://developer.apple.com/documentation/appkit)
- [WKWebView](https://developer.apple.com/documentation/webkit/wkwebview)
