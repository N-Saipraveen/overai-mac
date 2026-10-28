# Deployment

Built by Sai Praveen. Current version and build number are defined in `native/Release.json`.

## Tested local build

```sh
python3 native/scripts/build.py --test --dmg
```

The build first compiles an instrumented Release configuration to run core policy, native lifecycle, rendering, capture-exclusion, and isolated-cookie checks. Test failures, missing test results, skipped capture checks, invalid signatures, missing media entitlements, or debugger entitlements stop packaging. ScreenCaptureKit tests require existing Screen Recording authorization for the validation executable and an unlocked desktop; the script does not grant permissions.

It then rebuilds the production app without `OVERAI_VALIDATION`. The production executable rejects development launch options and contains no self-test runner or unprotected upload laboratory. Its version, arm64 architecture, bundled dependency license, media entitlements, and signature are checked. The DMG is verified and mounted read-only to compare the installed executable and Applications link before final artifacts replace previous generated output.

A `*-local-arm64.dmg` is a local validation artifact. Its readme explicitly identifies it as not notarized. Do not publish it as an Apple-notarized release. A matching JSON manifest records executed check counts and SHA-256 hashes.

## Distribution release

Install a **Developer ID Application** certificate and its private key in your macOS keychain. An Apple Development identity does not satisfy this requirement. Configure an existing notarytool Keychain profile using Apple's documented workflow; never commit credentials or provide passwords in build arguments.

```sh
export OVERAI_SIGNING_IDENTITY='Developer ID Application: Your Certificate Name (TEAMID)'
python3 native/scripts/build.py --release --notary-profile OVERAI_NOTARY
```

Release mode requires the exact installed Developer ID identity and a Keychain profile, runs all checks, signs with hardened runtime and a secure timestamp, submits a ZIP of the app to Apple, verifies acceptance, and staples the app's ticket. It then builds and signs the DMG, submits it to Apple, staples it, and validates both the app and DMG with Gatekeeper. Notarization rejection or failed verification stops publication. Reports stay in ignored `native/Validation/`; only generated app/DMG/manifests go to `dist/`.

Only `*-release-arm64.dmg` from a successful `--release` run is an output of that distribution workflow. The local build does not pretend to pass notarization. The workflow is implemented but must be exercised with a real Developer ID identity and Keychain profile before distributing to users.

Apple references: [Developer ID](https://developer.apple.com/developer-id/), [Notarizing macOS software](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution), [Customizing notarization](https://developer.apple.com/documentation/security/customizing-the-notarization-workflow).

## User-facing startup

The first launch asks **Show OverAI** or **Start Hidden**. The choice applies to later launches and can be changed under Settings → General. The initial permissions offer runs after that choice, with the existing skip option. Normal hidden launches make no website page request until the user opens OverAI. Existing website storage and the bundle identifier `com.overai.native` are preserved.

Launch at login remains a separate user-controlled setting. Merely choosing Start Hidden does not register a login item. About and onboarding credit **Built by Sai Praveen**. The third-party notices interface is removed; the required KeyboardShortcuts MIT notice remains inside the distributed resources.

## Acceptance before public release

No test suite proves the absence of bugs. The automated checks use synthetic content and do not log in to real providers, upload user files, grant microphone permissions, or create a meeting. Validate real provider sign-in, attachment and voice flows, long sleep/wake shortcut behavior, and Google Meet whole-screen capture on the supported macOS versions before public release.

Capture exclusion uses a private macOS compatibility API. It can change with macOS and is not a universal invisibility guarantee. The app fails closed when capture exclusion cannot be enabled. This is a direct-distribution app; no Mac App Store acceptance is claimed.

## Free public preview

Build 3004 removes all payment and license enforcement. No Dodo endpoints, local trial, activation screen, or license key are part of this build. Required dependency license notices remain.

`python3 native/scripts/build.py --preview` runs the validation suite and packages a `*-preview-arm64.dmg` with an explicit unnotarized-preview readme and a manifest. Preview mode does not claim Developer ID signing or notarization, and does not weaken the `--release` signing/notarization gates. Publish preview artifacts only as clearly labeled prereleases.
