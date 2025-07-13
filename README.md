

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
