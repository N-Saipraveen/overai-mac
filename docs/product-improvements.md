# OverAI product priorities

15 October 2026. These are recommendations; only the fixes identified below are implemented.

## Capture-safe controls — implemented

The AI selector used an `NSPopUpButton`. AppKit presents its menu in a separate window, outside the protected chat panel. The toolbar's More menu had the same architecture. Both now expand as ordinary AppKit views inside the already protected panel. No additional menu window or renderer is created. Choosing an item, clicking outside, pressing Escape, hiding the panel or moving focus away dismisses the choices. Escape closes a tray before hiding the overlay.

Synthetic lifecycle checks verify that the expanded controls share the panel. ScreenCaptureKit tests put a magenta sentinel inside each expanded tray and check exclusion while it is visible. These checks cover this Mac and capture path, not every meeting app. Validate the user's exact meeting app and share mode. macOS menu-bar menus, website-owned native menus, external browsers and system permission prompts have separate ownership and are not covered by this toolbar fix.

## Sign-in and storage

Production WebViews use `WKWebsiteDataStore.default()`, a persistent disk-backed store. All providers and their authentication popups use that store. Hiding, switching, upgrading the app under the same bundle identity, and normal quitting should not deliberately clear it. A separate-process synthetic cookie probe uses an isolated WebKit profile and never reads account cookies.

Persistence cannot override a provider's cookie expiry, session revocation, security checks, or restrictions on embedded login. Do not rewrite cookie lifetimes, copy credentials to JSON/UserDefaults, or add keep-alive timers to make a misleading “never log in again” promise.

Safari and Chrome are separate browser sessions. There is no supported general-purpose WKWebView API to adopt their Google account and all third-party website cookies. Apple's `ASWebAuthenticationSession` supports browser-mediated authentication with a cooperating OAuth flow and callback; it does not automatically populate arbitrary AI websites' WebView sessions. OverAI does not control those providers' OAuth registrations or callbacks. Google explicitly restricts embedded OAuth user agents. An external-browser fallback remains useful, but successful login there does not itself sign the embedded page in.

Sources: [Apple persistent WebKit storage](https://developer.apple.com/documentation/webkit/wkwebsitedatastore), [WebKit persistent profiles](https://webkit.org/blog/14423/building-profiles-with-new-webkit-api/), [Apple browser authentication](https://developer.apple.com/documentation/authenticationservices/aswebauthenticationsession), [Google OAuth policy](https://developers.google.com/identity/protocols/oauth2/policies).

## Recommended next features, in order

1. **Reliability before extras.** Repeatable overnight idle/sleep/wake and meeting-share tests on real authenticated sessions. Show a useful recovery state after network failure without silently discarding a draft. Measure host plus WebKit CPU and memory with the same providers and workload as Python.
2. **Keyboard-first use.** Provider switching with configurable shortcuts, arrow-key navigation within the selector, favourites/reordering, and a small shortcut reference. Preserve website editing shortcuts and input-method composition.
3. **Resume the exact conversation.** Opt-in restoration of the last safe conversation URL after quitting; never store authentication URLs/tokens. Draft restoration needs explicit consent, protected storage and provider compatibility work. Current in-memory drafts survive hiding and provider switching, not every crash or full app quit.
4. **Simple memory choices.** Keep current lazy loading and background CPU throttling. Add an explicit “Close this website to free memory” action with a draft/streaming warning. Do not automatically evict unknown active pages. Only offer an automatic light mode after reliable draft/streaming detection and measured benefit.
5. **Personal and work profiles.** Separate persistent WebKit stores with clear labels and an explicit switch. Prefer separate profiles to cookie copying. Per-site sign-out/data removal should warn about shared Google/SSO cookies before affecting other providers.
6. **Comfort and accessibility.** Per-provider text zoom, VoiceOver and keyboard focus checks, large click targets, reduced motion, remembered size/position per display, and optional compact toolbar. Keep the default interface quiet.

Avoid polling every few seconds, preloading all providers, stopping JavaScript timers inside websites, automatic cache clearing, or hidden credential backups. Those can consume resources, break responses or force repeated sign-in.
