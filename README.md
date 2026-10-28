<p align="center">
  <img src="Sources/OverAI/Resources/logo.png" width="88" alt="OverAI app icon" />
</p>

<h1 align="center">OverAI</h1>
<p align="center"><strong>All your AI. One button. Privacy first.</strong></p>
<p align="center">Your favorite AI websites in a floating window, a shortcut away from whatever you’re doing.</p>
<p align="center">
  <a href="https://github.com/N-Saipraveen/overai-mac/releases/tag/v3.0.0-beta.1"><strong>Download for Mac</strong></a>
  &nbsp; · &nbsp;
  <a href="https://n-saipraveen.github.io/overai-mac/">Website</a>
  &nbsp; · &nbsp;
  <a href="mailto:hello@saipraveen.dev">Support</a>
</p>
<p align="center">Free · Apple Silicon · macOS 14 or later · No AI API keys</p>

---

## A home for your AI websites

Press **⌘G**, choose a website, and carry on. OverAI brings ChatGPT, Claude, Gemini, Grok, Arena, Muse, and your own websites into one native Mac window. It opens their original websites using WebKit, with your existing accounts.

- **Your lineup.** Add websites, remove the ones you don’t use, and put everything in your preferred order.
- **Your shortcut.** Show or hide OverAI from anywhere. Change the shortcut in Settings.
- **Your space.** Resize the window, adjust its opacity, and keep your work in view.
- **Your sessions.** Website cookies persist between normal launches, so you can pick up where you left off.
- **A Mac app.** Built with Swift and AppKit, with a menu bar control, native settings, and support for Spaces.
- **Free to use.** No OverAI account, subscription, license key, or trial expiry.

AI providers keep their own account requirements, subscriptions, and usage limits. OverAI does not unlock paid models.

## Get started

1. [Download the Apple Silicon DMG](https://github.com/N-Saipraveen/overai-mac/releases/tag/v3.0.0-beta.1).
2. Quit any running copy of OverAI, open the DMG, and drag **OverAI.app** into **Applications**.
3. Open OverAI and choose **Show OverAI** or **Start Hidden**.
4. Press **⌘G** to bring up your window. Sign in to the websites you use.

> **Current release: free preview.** The app is ad-hoc signed and has not been notarized by Apple. macOS may block opening it. Read the release notes and [Apple’s guidance on opening apps safely](https://support.apple.com/en-us/102445) before installing. Checksums are included with the download.

Open **Settings → Websites** to customize your lineup. **Settings → General** controls your shortcut and startup behavior. Microphone setup is optional; macOS asks for consent. Files are shared only when you choose to attach them.

| Shortcut | Action |
| --- | --- |
| **⌘G** | Show or hide OverAI; customizable |
| **⌘R** | Reload the current website |
| **⌘,** | Open Settings |
| **Esc** | Dismiss an open selector, then hide the window |
| **⌘Q** | Quit OverAI |

## Privacy, with clear boundaries

**Your conversations go directly to your chosen website.** OverAI adds no prompt logging, analytics, account server, or payment verification. Each website handles your content under its own privacy policy.

**Capture protection is built in.** OverAI requests capture exclusion for its own windows and keeps the overlay hidden if protection cannot be enabled. Compatibility depends on macOS and the recording or meeting app. Test your setup before sharing sensitive content; this is not a guarantee of invisibility. System dialogs and external browser windows are outside OverAI’s protection.

**Sign-ins stay in OverAI’s local WebKit store.** Safari and Chrome sessions are separate and are not imported. Providers can expire sessions or restrict embedded-browser sign-ins. You can clear website data in Settings.

Websites load as you visit them. Visited pages stay alive to preserve their state, while background activity is throttled. Memory use depends on the websites and conversations you open.

## Build it yourself

Development requires an Apple Silicon Mac, **Xcode 26.3 / Swift 6.2 or later**, and Python 3 for the build tools. The app itself has no Python runtime.

Open `OverAI.xcodeproj` in Xcode, select the **OverAI** scheme, and run. Or build a local DMG:

```sh
python3 scripts/build.py --dmg
```

The app and DMG appear in `dist/`. Local builds are not notarized.

Run the core tests with `swift test`. For native lifecycle, UI, capture, and cookie-persistence checks:

```sh
python3 scripts/build.py --test
```

Full validation requires an unlocked desktop and existing Screen Recording permission for the test app. It uses synthetic content, not your accounts or conversations. Test windows and development modes are excluded from the final app.

To create a notarized distribution, install your Developer ID Application identity and configure a `notarytool` Keychain profile, then run:

```sh
OVERAI_SIGNING_IDENTITY='Developer ID Application: Your Name (TEAMID)' \
  python3 scripts/build.py --release --notary-profile OVERAI_NOTARY
```

`--release` requires signing, tests, notarization, and Gatekeeper validation. `--preview` produces an explicitly unnotarized preview with tests and a DMG. Version information lives in `Release.json`.

## Around the repository

```text
OverAI.xcodeproj/    Xcode project
Sources/            App, shared policies, and bundled resources
Tests/              Core tests and native integration fixtures
website/            Static product website
scripts/            Build, project generation, and website checks
```

The website deploys from this repository through GitHub Pages. Preview it with `python3 -m http.server 4173 --directory website` and check local links with `python3 scripts/check-website.py`.

KeyboardShortcuts is pinned through Swift Package Manager. Its required license notice is bundled in `Sources/OverAI/Resources/ThirdPartyNotices.txt`. Provider names and artwork belong to their respective owners; OverAI is independent and is not endorsed by them.

---

Built by **[Sai Praveen](https://github.com/N-Saipraveen)**. Questions or feedback? **[hello@saipraveen.dev](mailto:hello@saipraveen.dev)**
