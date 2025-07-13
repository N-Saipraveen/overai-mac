

# OverAI

**OverAI** is a lightweight macOS overlay that brings your favorite AI chat services directly to your desktop. Enjoy seamless access to Grok, ChatGPT, DeepSeek, and more—all within a transparent, always-on-top window.

---

## 🚀 Features

- **Floating Overlay**  
  A frameless window that stays on top of all applications.
- **Adjustable Transparency**  
  Use the **+** and **−** buttons to set your preferred opacity.
- **Global Hotkey**  
  Press **⌘+G** to show or hide the overlay instantly.
- **AI Service Selector**  
  Switch between Grok, ChatGPT, DeepSeek, and custom endpoints via the dropdown.
- **Voice Input Support**  
  Click the microphone icon to speak your prompts directly.
- **Seamless macOS Integration**  
  Accessibility and microphone permissions handled automatically.

---

## 📦 Installation

1. **Download** the latest release ZIP (e.g., `OverAI.zip`).  
2. **Unzip**:
   ```bash
   unzip OverAI.zip
   ```
3. **Move** the app to your Applications folder:
   ```bash
   mv OverAI.app /Applications/
   ```
4. **Launch** **OverAI** from `/Applications`.  
5. **Grant Permissions**  
   - On first run, allow **Microphone** access when prompted.  
   - In **System Settings → Privacy & Security → Accessibility**, add and enable **OverAI** for global hotkeys.

---

## 💻 Usage

- **Toggle Overlay**: Press **⌘+G**.  
- **Select AI Service**: Top-left dropdown.  
- **Speak Prompt**: Click the mic icon and speak.  
- **Adjust Transparency**: Top-right **+** / **−** buttons.

---

## 🛠️ Building from Source

```bash
# Clone repo
git clone https://github.com/N-Saipraveen/overai-mac.git
cd overai-mac

# Set up virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Run directly
python run.py

# Or build a standalone app via py2app
python setup.py py2app
```

> You can also use PyInstaller:
> ```bash
> pyinstaller --name OverAI --windowed \
>   --icon overai/logo/AppIcon.icns \
>   --add-data "overai:overai" \
>   run.py
> ```

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!  
Feel free to open a pull request or submit an issue on GitHub.

---

## 📄 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

# OverAI

**OverAI** is a professional, always‑on‑top macOS overlay that runs locally via `overai.py`. Designed for seamless access to any AI chat service—Grok, ChatGPT, DeepSeek, or your own endpoint—OverAI sits hidden during meetings and presentations, then reappears at your command.

---

## 🚀 Core Features

- **Local Execution**  
  Runs directly from your machine with Python: no installer or DMG required.  
- **Meeting‑Aware Visibility**  
  Automatically hides when calendar events or conferencing apps (Zoom, Teams, Webex) are active.  
- **Universal AI Selector**  
  Instantly switch between Grok, ChatGPT, DeepSeek, or any custom HTTP endpoint.  
- **Voice & Text Input**  
  Click the microphone icon or type your prompt.  
- **Adjustable Transparency**  
  Slide or click **+ / −** to set your preferred overlay opacity.  
- **Configurable Global Hotkey**  
  Default **⌘+G** toggles visibility—fully customizable via `config.json`.  
- **Frameless & Lightweight**  
  A sleek, distraction‑free window that blends into your workflow.

---

## 📦 Installation & Setup

1. **Clone the repository**  
   ```bash
   git clone https://github.com/N-Saipraveen/overai-mac.git
   cd overai-mac
   ```

2. **Create and activate a virtual environment**  
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**  
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Configure (optional)**  
   Copy `config.example.json` to `config.json` and adjust service URLs, hotkey, transparency limits, or meeting‑app integration.

5. **Run OverAI**  
   ```bash
   python overai.py
   ```

The overlay will launch, ready to serve your AI needs—hidden when you’re in calls, visible on your hotkey.

---

## ⚙️ Configuration

Edit `config.json` to customize:

```jsonc
{
  "services": {
    "Grok": "https://grok.com",
    "ChatGPT": "https://chat.openai.com",
    "DeepSeek": "https://deepseek.com/chat"
  },
  "hotkey": "Command+G",
  "minOpacity": 0.2,
  "maxOpacity": 1.0,
  "meetingApps": ["zoom.us", "teams", "webex"]
}
```

- **services**: Add or remove AI endpoints.  
- **hotkey**: Use any standard key combination.  
- **minOpacity / maxOpacity**: Define transparency range.  
- **meetingApps**: Specify process names to auto-hide overlay.

---

## 🛠️ Development

- **Run tests** (if any): `pytest tests/`  
- **Lint & format**: `flake8` / `black .`  
- **Build**: Create a standalone macOS app via PyInstaller or py2app when needed.

---

## 🤝 Contributing

We welcome improvements, bug reports, and new features.  
Please fork the repo, create a feature branch, and submit a pull request.

---

## 📄 License

Licensed under the **MIT License**. See [LICENSE](LICENSE) for details.