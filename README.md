# 🧠 OverAI — Modern AI Overlay for macOS

**OverAI** is a beautifully designed, always-on-top AI overlay for macOS that gives you instant access to your favorite LLMs. Built with Apple Design principles and optimized for performance.

> **Privacy-first. Lightning fast. Accessible to everyone.**

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🎨 **Native Design** | Follows Apple's Human Interface Guidelines with system colors and vibrancy |
| ⌨️ **Global Hotkey** | Toggle with ⌘+G (customizable) from anywhere |
| 🧠 **Multi-AI Support** | Grok, ChatGPT, Claude, Gemini, DeepSeek |
| ♿ **Accessible** | Full VoiceOver support, keyboard navigation, reduced motion |
| 🪟 **Invisible to Recordings** | Hidden from screenshots and screen sharing |
| 🎛️ **Transparency Control** | Adjustable opacity to blend with your workflow |
| 💾 **State Restoration** | Remembers your position, size, and preferred AI |
| 🚀 **Lightweight** | Optimized memory usage with lazy loading |
| 🔒 **Privacy-First** | No external servers, local-only operation |

---

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/N-Saipraveen/overai-mac.git
cd overai-mac

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Run OverAI
python OverAI.py
```

---

## 🛠 Advanced Usage

### Command Line Options

```bash
# Install to run at login
overai --install-startup

# Remove from login items
overai --uninstall-startup

# Check permissions
overai --check-permissions

# Show version
overai --version
```

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| ⌘+G | Toggle overlay visibility |
| ⌘+H | Hide overlay |
| ⌘+Q | Quit application |
| ⌘+R | Reload current page |
| ⌘+Shift+G | Go to home |

---

## 🔐 Permissions

OverAI requires the following permissions:

- **Accessibility** — For global hotkey detection
- **Microphone** — For voice input to AI services

Grant these in: **System Settings → Privacy & Security**

---

## 🏗 Architecture

OverAI 2.0 features a complete architectural overhaul:

```
overai/
├── core/              # Application core
│   ├── app_delegate.py      # Main controller
│   ├── window_manager.py    # Optimized window handling
│   └── lifecycle_manager.py # App lifecycle & memory
├── ui/                # User interface
│   ├── webview_manager.py   # WKWebView with lazy loading
│   ├── control_bar.py       # Accessible controls
│   └── status_bar.py        # Menu bar integration
├── utils/             # Utilities
│   ├── logger.py            # Unified logging
│   ├── theme.py             # Dynamic theming
│   ├── accessibility.py     # VoiceOver & keyboard nav
│   ├── keyboard.py          # Global hotkey management
│   └── memory_tracker.py    # Memory optimization
└── _legacy/           # Previous version (reference)
```

### Key Improvements

- **Memory Efficiency**: Weak references, lazy loading, periodic cleanup
- **Accessibility**: Full VoiceOver support, keyboard navigation, announcements
- **Apple Design**: System colors, vibrancy, proper dark mode adaptation
- **State Restoration**: Saves window position, size, opacity, and AI preference
- **Crash Protection**: Smart crash loop detection with automatic recovery

---

## 💻 Tech Stack

- **Python 3.9+**
- **PyObjC 10.0+** — macOS framework bindings
- **AppKit/Quartz/WebKit** — Native macOS UI
- **psutil** — System monitoring

---

## 🏭 Building

### Standalone App

```bash
# Build .app bundle
python setup.py py2app

# The app will be in dist/OverAI.app
```

### Development Mode

```bash
# Install in editable mode
pip install -e .

# Run with module syntax
python -m overai
```

---

## 🐛 Troubleshooting

### App doesn't show up

Check Accessibility permissions:
```bash
overai --check-permissions
```

### Reset all settings

```bash
rm -rf ~/Library/Application\ Support/OverAI
rm -rf ~/Library/Logs/OverAI
```

### Crash loop detected

```bash
rm ~/Library/Logs/OverAI/crash_history.json
```

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure your code follows:
- PEP 8 style guidelines
- Type hints for public APIs
- Accessibility best practices
- Memory-efficient patterns

---

## 📜 License

MIT License. See [LICENSE](LICENSE) for details.

---

## ⭐ Support

If this project helped you, **please star the repo** — it really helps!

---

## 🙏 Acknowledgments

- Apple's [Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/)
- [PyObjC](https://pyobjc.readthedocs.io/) team for excellent macOS bindings
- The AI services for providing amazing APIs

---

<p align="center">
  <strong>Made with ❤️ by Sai Praveen</strong>
</p>
