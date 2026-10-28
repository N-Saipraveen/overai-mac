# UI, performance, and security review — 16 October 2026

## Design decisions and research

Apple's [Motion guidance](https://developer.apple.com/design/human-interface-guidelines/motion) favors purposeful feedback. Provider content and protected toolbar trays now reveal with a 120 ms compositor opacity animation. Dismissal stays immediate, so hiding private content never waits for an animation. There are no repeating timers, snapshot textures, spring effects, or duplicate web views for transitions. [Reduce Motion](https://developer.apple.com/documentation/appkit/nsworkspace/accessibilitydisplayshouldreducemotion) is checked at each reveal; enabled means no custom animation.

Apple's [macOS guidance](https://developer.apple.com/design/human-interface-guidelines/designing-for-macos/) and [Menus guidance](https://developer.apple.com/design/human-interface-guidelines/menus) informed keyboard navigation and visible selection. The provider tray marks the active provider, focuses it initially, supports arrow navigation, Tab, Return and Space, and dismisses with Escape. More initially focuses its first action. Original website icons remain bundled locally. Trays remain inside the capture-protected window.

## Correctness and security changes

- Promised screenshot/file delivery retains the callback from when the drag started. If the user switches providers before delivery, the files are discarded rather than attached to the newly selected provider. Closing invalidates outstanding delivery callbacks.
- Media requests must come from the main frame of the current HTTPS provider document, with matching host and default TLS port. Credentials embedded in URLs are rejected. Permission is rechecked against document generation and URL after the macOS prompt; navigating or closing cancels the grant.
- Login popup and download cleanup first detach the collections before closing/cancelling their members, avoiding reentrant collection mutation.
- Navigation cancels the previous page's crash-budget reset, so an earlier successful page cannot reset a newer crash loop.

## Resource policy

Only visited providers create web views; switching retains them to preserve drafts and streams. Inactive scheduling remains throttled. The changes introduce no new dependencies or background services. Website content is still the dominant potential RAM cost. No claim of measured total RAM reduction is made; it requires a repeatable signed-in workload and WebKit child-process measurements. Automatic eviction remains intentionally excluded because it loses unknown page state.

## Boundaries requiring further validation

Automated tests cover synthetic state retention, cookie persistence across processes, keyboard selection, rapid tray reopen, media-origin policy and local ScreenCaptureKit exclusion. They do not prove every third-party website upload/voice flow, Google Meet whole-screen behavior, overnight wake handling, or every macOS version. Actual microphone approval remains a user action.

The application uses hardened runtime and release signing without debugger attachment entitlement; it is locally ad-hoc signed and not notarized. The host app is not App Sandbox enabled. Capture exclusion uses a private compatibility API and cannot promise invisibility to every recorder. System-owned permission dialogs are outside its protection. A production release still needs Developer ID signing, notarization, and the real-service acceptance checks above.

## Settings and menu bar refinement

Settings now uses a native SwiftUI sidebar with General, Appearance, Privacy, App Status, and About. The fixed 760 × 620 content area gives controls space while each grouped form can scroll independently. Permission management, destructive website-data clearing, startup behavior, and resource settings have dedicated sections. The version comes from the application bundle; About includes the builder credit. No timer or telemetry was added. App Status samples the app's actual footprint on entry and explicit Refresh; its label explains that WebKit memory is additional.

The status menu uses the same bundled provider artwork as the floating picker and updates the selected-provider checkmark whenever opened. The dense modal Diagnostics alert has been replaced with App Status in the existing Settings window. Menu groups separate providers, settings/status, and Quit. The menu bar symbol remains a small template symbol that adapts to system appearance.

Design references: [Apple Settings guidance](https://developer.apple.com/design/human-interface-guidelines/settings), [Sidebars](https://developer.apple.com/design/human-interface-guidelines/sidebars), and [Menus](https://developer.apple.com/design/human-interface-guidelines/menus).

## User-managed websites

Built-in and custom websites now share an ordered, persisted catalog. Existing selected-provider preferences migrate by identifier. Invalid saved entries are rejected and an empty/corrupt catalog falls back to the built-ins. Users can remove every built-in but must retain at least one website. Restoring built-ins appends only missing presets and preserves custom entries and ordering.

Custom entries accept a name of up to 40 characters and an HTTPS URL up to 2048 characters; embedded credentials, control characters, and unsafe schemes are rejected. Custom ownership is limited to the configured hostname and port, rather than implicitly trusting all subdomains. Existing TLS, file-picker, media permission, and external navigation policies still apply. Custom icons use a bundled system globe, without background favicon downloads.

Removing the current site switches to a remaining site before closing its session. Reordering leaves existing web views intact. Adding entries does not create web views. Removing a visited entry closes its runtime and login windows but preserves persistent website data. The removal confirmation uses the existing protected native sheet path. Long picker lists scroll inside the same protected window; menu bar ordering and selection are rebuilt on menu opening.

## Removal confirmation repair and browser focus research

Website removal now confirms in the existing Settings content hierarchy instead of constructing a separate protected NSAlert window. The previous path silently returned if the app-wide key-window lookup or new alert capture-protection setup failed. The confirmation has explicit Cancel/Remove actions, disables background controls, and preserves website data. Regression checks exercise cancellation, custom and built-in removal, and rendering the confirmation inside Settings. Removing the final remaining site remains disabled, with a specific explanatory tooltip; add another site first.

The user's [CodePen demo](https://codepen.io/calebnance/pen/nXPaKN) listens to window blur/focus and labels blur as leaving a tab. This is focus loss, not proof of changing tabs. Apple documents that a [nonactivating panel](https://developer.apple.com/documentation/appkit/nswindow/stylemask-swift.struct/nonactivatingpanel) does not activate its owning app; that alone does not preserve another window's keyboard focus. [Window blur](https://developer.mozilla.org/en-US/docs/Web/API/Window/blur_event) is available to web pages. OverAI already uses a nonactivating panel, but interactive typing can transfer focus. No change is claimed to make it undetectable and no focus/visibility events are falsified.

## Deployment preparation — 20 October 2026

First launch now presents a protected, native startup choice before opening an AI website: Show OverAI or Start Hidden. The persisted selection remains editable in General. The permissions offer follows the choice; hidden startup then closes the welcome window without showing the chat. Normal hidden launches defer website page loading until the overlay is opened. About and onboarding credit Sai Praveen. The notices UI is removed, with required dependency license text retained in the app bundle.

Website-data clearing uses an in-window confirmation and disables Settings controls during clearing. Reload is blocked while website data is being removed. Invalid persisted nonfinite opacity values use a safe default. Custom URLs reject invalid TCP ports. Production builds exclude diagnostic runners and unprotected fixture windows. Packaging distinguishes local validation artifacts from notarized distribution output and verifies the actual mounted install image.


## Free build — 29 October 2026

Payment, trial, activation, license-network code and license UI were removed for the free preview. Dependency notices remain. Check counts for this build are recorded in the generated validation manifest; prior build counts do not describe this release.
