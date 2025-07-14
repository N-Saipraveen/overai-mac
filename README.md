# 🧠 OverAI — Stealth AI Overlay for macOS

**OverAI** is a local-first, always-on-top AI overlay for macOS that gives you seamless, private access to your favorite LLMs like ChatGPT, Grok, Perplexity, Claude, and Gemini.

> **No servers. No tracking. No nonsense. Just powerful AI where you need it.**

---

## 🚀 Quick Start

```bash
git clone https://github.com/N-Saipraveen/overai-mac.git
cd overai-mac

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

python overai.py
```

📅 OverAI launches instantly and stays ready on your screen.

---

## 🛠 Configuration

- **Hotkey**: Default is `⌘ + G` — customizable in `config.json`
- **AI Endpoints**: Choose ChatGPT, Grok, DeepSeek, etc. from the dropdown
- **Auto-hide on Meetings**: Detects Zoom, Teams, Webex and hides the overlay

---

## 🔐 Permissions Required

When you launch OverAI for the first time, macOS will request:

- 🎙️ **Microphone Access** — to capture voice commands
- ⌨️ **Accessibility Access** — to enable the global hotkey (⌘+G)

You can manage these anytime from: **System Settings → Privacy & Security**

---

## ✨ Features

| Feature                    | Description                                       |
| -------------------------- | ------------------------------------------------- |
| 🪟 Frameless Overlay       | Stays always on top, clean and distraction-free   |
| 🧠 Multi-AI Support        | Easily switch between ChatGPT, Grok, Claude, etc. |
| 🎙️ Voice & Text Input     | Speak or type your prompt directly                |
| 🎛️ Transparency Control   | Adjust overlay opacity to your preference         |
| 🎹 Hotkey Toggle           | `⌘+G` or any custom key combo to toggle overlay   |
| 🕵️ Hidden from Recordings | Invisible in screen sharing and screen recordings |
| 🖥️ Lightweight + Local    | No lag, no cloud storage, no external servers     |

---

## 💻 Tech Stack

- Python 3.10+
- AppKit, Quartz, WebKit
- PyObjC
- SpeechRecognition

---

## 🤝 Contributing

Contributions welcome!

- Fork the repo
- Create a feature branch
- Submit a pull request

---

## 📜 License

MIT License. See [LICENSE](LICENSE) for details.

---

## ⭐ Like it?

If this project helped you, **please star the repo 🌟** — it really helps!

