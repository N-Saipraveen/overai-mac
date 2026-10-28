# Native OverAI validation

15 October 2026. M3 / arm64, macOS 26.0.1 (25A362), Xcode 26.3, Swift 6.2.4. Build 3.0.0 beta 1, bundle `com.overai.native`.

**Automated checks**

Five XCTest cases pass: provider domain boundaries, Arena Direct-mode routing, navigation scheme/credential restrictions, safe download leaf names, and bounded renderer recovery.

Twenty-seven native lifecycle checks exercise the actual overlay and session classes, including bundled official provider artwork. They use a local synthetic page and nonpersistent WebKit storage. They cover lazy creation, same-WebView identity across hide and provider switches, textarea and rich-text drafts, JavaScript state, event listeners, background timer progress, opacity changes, layout, native hotkey registration/reacquisition, capture API return values, session-registry cleanup, expanded toolbar tray ownership/dismissal, and text/PNG attachment delivery through WebKit's native file input. Four permission-setup checks cover fresh-install detection, saved setup state, persistent folder bookmarks, and forgetting a folder without deleting it.

16 October update: first-launch setup offers microphone authorization followed by an upload-folder picker. Setup can be skipped and reopened in Settings. Tests never request or approve microphone/camera access and use only a synthetic temporary folder for bookmark checks. Live OS consent, deny/retry and folder-picker cancel paths need manual verification. Release packaging checks the microphone/camera capability entitlements and rejects debugger-attachment entitlements. No Screen Recording or Full Disk Access prompt is added to normal startup.

The attachment checks use local synthetic files and verify both names and readable contents in the page's real File objects. They do not upload anything to a provider. The toolbar accepts file URLs, PNG/TIFF image data and AppKit file promises. Temporary screenshot copies are local and removed when the overlay closes. Original user files are never deleted. Per-provider attachment input availability and upload restrictions still apply. Manual end-to-end Finder and screenshot-thumbnail drag coverage is separate from these file-input integration checks.

The explicit `--upload-lab` mode uses a nonpersistent synthetic page and local drag sources. A native fallback drop was observed to populate the real file input (`PICKER: OverAI-upload-fixture.txt`). Screenshot file-promise code is implemented, but the actual macOS floating screenshot thumbnail and each authenticated provider still require manual testing. This development-only lab window intentionally allows capture of its synthetic content; normal application windows retain capture protection.

The capture probe verifies an unprotected magenta control first, then checks the same synthetic window after region exclusion and after a resize. The control has a 1.000 sentinel fraction; protected/resized captures have 0.000. The window must remain visible for the protection assertions. The test uses ScreenCaptureKit's desktop-independent window filter and captures only the app's own synthetic window. It is not a full-display or meeting-app capture test.

The probe also opens the actual overlay's AI selector and More trays, places a synthetic sentinel inside each, and verifies they share the protected panel and produce a 0.000 sentinel fraction while visible. Six capture checks pass. The original AppKit popup menus used separate windows; those toolbar menus have been replaced by views inside the panel. Native system/website menus are outside this fix.

Two more checks write an expiring synthetic cookie to a fresh isolated persistent WebKit profile, quit normally, and read it in a second app process. Both pass. The first harness attempt exited the process abruptly before WebKit shutdown and failed the read; initializing a WebView and using normal AppKit termination corrected the normal-quit experiment. This does not prove survival of a force quit or provider-controlled session expiry. No user cookies are read or copied. The test profile's website data is cleared after reading.

The initial pixel classifier was too strict about color conversion and rejected a visibly magenta control image. It was corrected to compare sRGB with a display-conversion tolerance. The probe refuses to claim protection when the unprotected control is missing. No failed control is treated as a successful exclusion.

Results are in `native/Validation/lifecycle.json` and `native/Validation/capture.json`. `synthetic-preview.png` is composed from the native chrome and a WKWebView snapshot during the synthetic self-test; it is not an OS capture or an image of a user's account. Other PNGs contain only the capture sentinel.

**Interactive checks**

- Toolbar refresh: centered native provider picker, grouped navigation, native minus/plus opacity control, and no permanent bottom status strip. Load failures retain an error-only Retry banner. The synthetic preview was visually inspected; live minus/plus clicks changed opacity from 90% to 80% and back without navigating the website.
- The packaged Swift app launches through LaunchServices and shows its native overlay and menu bar controls.
- The updated selector shows ChatGPT, Claude, Gemini, Grok, Arena and Muse. Arena's live public page loaded at `https://arena.ai/text/direct?model_a=max`, with the Max model control and empty composer. No message was sent.
- Grok and ChatGPT public landing pages and Claude's login page load in WebKit.
- A synthetic draft was entered into Grok without submission, the provider switched to ChatGPT, then switched back. The Grok composer retained the complete draft. The synthetic text was removed afterwards.
- The app's quit menu shortcut terminates the process normally.
- Settings opens with ⌘, and displays the localized native shortcut recorder, opacity slider, startup preferences and capture status.
- Automated reassignment of the shortcut was not completed. The recorder UI loads; no reassignment or physical global-toggle delivery claim is made from that observation.

**Packaging**

The Xcode build produces a standalone arm64 app with its own app icon, official provider icons, usage descriptions, pinned dependency's localized resource bundle and third-party notices. `codesign --verify --deep --strict` checks the built and copied app. The DMG's checksums are validated with `hdiutil verify`. Disk size is not a RAM measurement.

The local app is ad-hoc signed, with no Developer ID certificate or Apple notarization. The build replaces only generated output in `dist/`.

**Remaining validation limits**

No production account was logged into and no AI message was submitted. Real authenticated streaming, 2FA, upload/download, voice/video, login item approval, secondary displays, full-screen applications, prolonged idle and overnight sleep/wake still need user-environment tests. The low-level register/unregister check does not prove physical keyboard delivery after many hours of inactivity.

Zoom, Google Meet, Teams, OBS, full-display/region screenshots and other macOS versions have not been validated. A successful private API call alone is never labeled a universal protection guarantee. System-owned permission prompts and external browser windows are outside this app's window ownership.

The user reported the selector leak specifically in Google Meet with whole-screen sharing. The toolbar fix and synthetic capture checks are complete; that exact meeting/share path still needs a user retest. A final live UI spot-check was unavailable because the Mac was locked.

Total RAM under equivalent live-provider workloads still needs measurement. The synthetic lifecycle result's footprint is the app process only and excludes WebKit. Background CPU throttling and lazy loading reduce avoidable work, while preserving live chat state retains renderer memory.

For manual acceptance: leave drafts in each provider, switch repeatedly, hide/show, complete an authenticated response while hidden, sleep and wake, then exercise the configured shortcut from another app. Use a harmless sentinel while checking each capture tool. Check Activity Monitor's app-associated WebKit helpers alongside the native process rather than comparing only the host process.

## UI/security pass — 16 October 2026

Final packaged build: 6 unit tests, 30 native lifecycle checks, 6 ScreenCaptureKit checks, and 2 persistent-cookie process checks passed (44 total). Strict code signing, media entitlements, absence of release debugger entitlement, and DMG checksum validation passed. The initial ScreenCaptureKit attempt failed to start a stream; the final full run passed all capture checks. Rendered synthetic picker preview inspected. See [review](ux-security-review.md) for scope and manual validation limits.

## Settings and status menu pass — 16 October 2026

Final build passed 54 checks: 6 core policy unit tests, 40 native checks (including ten Settings renders across five pages in light/dark), 6 capture checks, and 2 cookie persistence checks. All five Settings page layouts were visually inspected. Native status menu now uses bundled brand icons and selected-provider checkmarks; App Status opens Settings instead of a diagnostics alert. Build signing and DMG checksum verification passed. Tests do not change microphone permission, login items, chosen folders, or real website data.

## Website management — 16 October 2026

Final packaged build passed 65 checks: 7 core unit tests, 50 native lifecycle/render checks, 6 ScreenCaptureKit checks, and 2 cookie persistence checks. New checks cover unsafe custom addresses, host isolation, Codable round trip, saved ordering/selection, duplicate rejection, retaining one custom website, restoring built-ins, unchanged runtime on reorder, lazy addition, and active-site removal/session release. Settings Websites and protected picker previews were visually inspected. DMG checksum and strict signing passed. No external custom website sign-in was performed.

## Removal confirmation repair

Final packaged build passed 69 checks: 7 core unit tests, 54 native lifecycle/render checks, 6 ScreenCaptureKit checks, and 2 cookie persistence checks. Added custom/built-in removal and cancellation checks, plus an in-window confirmation render inspected visually. Settings no longer relies on a new alert window or app-global key-window lookup for removal. An earlier capture run had a picker visibility assertion failure; the final full run passed all six capture checks. Strict signing and DMG checksum validation passed.

## Deployment preparation — 20 October 2026

Version 3.0.0, build 3002. Final run passed 78 checks with no skips: 8 core policy tests, 62 native lifecycle/render checks, 6 ScreenCaptureKit checks, and 2 isolated cookie persistence checks. New coverage includes remembered startup choices, deferred page loading, nonfinite opacity recovery, custom-site port and saved-identity validation, and in-window website-data confirmation. Startup light/dark and the updated About and destructive confirmation layouts were visually inspected.

The production executable was rebuilt without OVERAI_VALIDATION after the synthetic tests. It rejects self-test, upload-lab, capture-probe, and storage-probe flags. Strict signing, arm64 architecture, version/build consistency, required MIT notice, microphone/camera capabilities, and absence of the debugger entitlement were verified. The DMG checksum passed; it was mounted read-only and its executable hash and Applications symlink matched the staged artifact. The JSON manifest accompanies the local DMG.

An earlier ScreenCaptureKit run encountered an internal capture-start error. The validation helper now permits at most two retries for SDK startup/internal errors only; assertions, permission failures, and missing baseline controls still fail. The final full run passed all capture checks. This helper is excluded from production.

The local output is ad-hoc signed and NOT notarized. This Mac currently has an Apple Development identity but no Developer ID Application identity. The --release workflow enforces Developer ID signing, secure timestamps, notarization acceptance, stapling, and Gatekeeper assessment; that external workflow remains unexecuted until the required identity/profile exist. No public deployment is claimed. See deployment.md for the exact commands and manual acceptance scope.


## Free build — 29 October 2026

Payment, trial, activation, license-network code and license UI were removed for the free preview. Dependency notices remain. Check counts for this build are recorded in the generated validation manifest; prior build counts do not describe this release.

Build 3004 passed **79 checks**: 8 core policy tests, 63 native lifecycle/rendering checks, 6 ScreenCaptureKit checks, and 2 isolated cookie-persistence checks. The capture probe now settles application focus before opening each tray and reports window/tray state, following an initial failed More-menu visibility assertion. Capture assertions were not skipped or relaxed. Production development options are rejected, payment configuration/endpoints are absent, arm64 architecture and media entitlements verify, and the mounted DMG executable matches the validated app. The preview is ad-hoc signed and not notarized.
