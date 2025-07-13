

# OverAI

**OverAI** is a secure, always-on-top macOS overlay that runs locally via `overai.py`. Optimized for privacy, all processing happens in your browser and machine—no servers involved.

---

## 📦 Quick Start

1. **Download** the project archive (ZIP) or clone the Git repository:
   ```bash
   git clone https://github.com/N-Saipraveen/overai-mac.git
   cd overai-mac
   ```
2. **Create & activate a virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. **Install dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
4. **Run OverAI**:
   ```bash
   python overai.py
   ```

That’s it! OverAI will launch immediately.

---

## 🚀 Key Features

- **Frameless Overlay**  
  Always on top, blending into any workflow without distractions.
- **Universal AI Access**  
  Switch between Grok, ChatGPT, DeepSeek, or any custom endpoint.
- **Voice & Text Input**  
  Click the microphone icon or type your prompt directly.
- **Adjustable Transparency**  
  Use **+ / −** buttons or slide the transparency control to your liking.
- **Customizable Hotkey**  
  Default **⌘+G** to toggle visibility—configurable in `config.json`.
- **Meeting-Aware Hiding**  
  Automatically hides when conferencing apps (Zoom, Teams, Webex) are active.
- **Local & Private**  
  No data leaves your machine; all interactions flow through your browser session.

---

## 🔒 Permissions

On first launch, OverAI will request two macOS permissions:

1. **Microphone Access**  
   Needed to capture your voice for prompts.
2. **Accessibility Access**  
   Required for the global hotkey (⌘+G) to show/hide the overlay.

You can review and revoke these anytime in **System Settings → Privacy & Security**.

---

## 🤝 Contributing

Contributions are welcome!  
Fork the repo, create a feature branch, and submit a pull request.

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.