"""Build/test local artifacts or sign, notarize and verify a distribution release.

Local: python3 scripts/build.py --test --dmg
Release: OVERAI_SIGNING_IDENTITY='Developer ID Application: ...' python3 scripts/build.py --release --notary-profile PROFILE
Notary credentials remain in an existing macOS Keychain profile.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile
import uuid
import re
from datetime import datetime, timezone

parser = argparse.ArgumentParser()
parser.add_argument("--dmg", action="store_true")
parser.add_argument("--test", action="store_true")
parser.add_argument("--preview", action="store_true", help="Package an explicitly unnotarized public preview")
parser.add_argument("--release", action="store_true", help="Require Developer ID, tests, notarization and Gatekeeper validation")
parser.add_argument("--notary-profile", help="Existing notarytool Keychain profile; no passwords on the command line")
args = parser.parse_args()
repo = Path(__file__).resolve().parents[1]
release = json.loads((repo / "Release.json").read_text())
output = repo / "dist"
identity = os.environ.get("OVERAI_SIGNING_IDENTITY", "-")
if args.release and args.preview:
    parser.error("Choose --preview or --release, not both.")
if args.preview:
    args.test = args.dmg = True

if args.release:
    if not identity.startswith("Developer ID Application:"):
        parser.error("--release requires OVERAI_SIGNING_IDENTITY='Developer ID Application: …'. Apple Development and ad-hoc signatures cannot be distributed as a notarized release.")
    if not args.notary_profile:
        parser.error("--release requires --notary-profile with an existing notarytool Keychain profile.")
    installed = subprocess.check_output(["security", "find-identity", "-v", "-p", "codesigning"], text=True)
    if identity not in installed:
        parser.error("The requested Developer ID Application identity is not installed in this Mac's keychain.")
    args.test = args.dmg = True
elif args.notary_profile:
    parser.error("Use --notary-profile only with --release.")
if args.dmg:
    try:
        import dmgbuild
    except ImportError:
        parser.error("DMG packaging requires dmgbuild. Install requirements-build.txt in a virtual environment and run this script with that environment's Python.")
output.mkdir(exist_ok=True)
validation = repo / "Validation"
validation.mkdir(exist_ok=True)


def run(*command, timeout=600):
    return subprocess.run([str(part) for part in command], check=True, cwd=repo, timeout=timeout)


def verify(app):
    run("codesign", "--verify", "--deep", "--strict", app)
    values = plistlib.loads(subprocess.check_output(["codesign", "-d", "--entitlements", ":-", str(app)], stderr=subprocess.DEVNULL))
    for entitlement in ("com.apple.security.device.audio-input", "com.apple.security.device.camera"):
        if values.get(entitlement) is not True:
            raise RuntimeError("Required media entitlement missing: " + entitlement)
    if values.get("com.apple.security.get-task-allow"):
        raise RuntimeError("Release build must not allow debugger attachment")
    info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
    if info["CFBundleShortVersionString"] != release["version"] or info["CFBundleVersion"] != release["build"]:
        raise RuntimeError("Bundle version does not match Release.json")
    notices = app / "Contents/Resources/ThirdPartyNotices.txt"
    if not notices.is_file() or "MIT License" not in notices.read_text():
        raise RuntimeError("Required dependency license text is missing")
    if (app / "Contents/Resources/LicenseConfiguration.json").exists():
        raise RuntimeError("Free app must not bundle payment configuration")
    binary = app / "Contents/MacOS/OverAI"
    if b"dodopayments.com" in binary.read_bytes():
        raise RuntimeError("Free app must not contain Dodo payment endpoints")
    architecture = subprocess.check_output(["lipo", "-archs", str(binary)], text=True).strip()
    if architecture != "arm64":
        raise RuntimeError("Expected an Apple Silicon arm64 binary")
    return binary


def build(with_validation=False):
    command = ["xcodebuild", "-project", repo / "OverAI.xcodeproj", "-scheme", "OverAI", "-configuration", "Release",
               "-derivedDataPath", repo / ".deriveddata", "-destination", "platform=macOS,arch=arm64",
               "CODE_SIGN_IDENTITY=" + identity,
               "SWIFT_ACTIVE_COMPILATION_CONDITIONS=" + ("OVERAI_VALIDATION" if with_validation else ""),
               "build", "-quiet"]
    if identity.startswith("Developer ID Application:"):
        command.insert(-2, "OTHER_CODE_SIGN_FLAGS=--timestamp")
    run(*command)
    product = repo / ".deriveddata/Build/Products/Release/OverAI.app"
    verify(product)
    return product


def notarize(path, label):
    result = subprocess.run(["xcrun", "notarytool", "submit", str(path), "--keychain-profile", args.notary_profile,
                             "--wait", "--timeout", "20m", "--output-format", "json"],
                            check=True, capture_output=True, text=True, timeout=1260)
    data = json.loads(result.stdout)
    (validation / ("notarization-" + label + ".json")).write_text(json.dumps(data, indent=2) + "\n")
    if data.get("status") != "Accepted":
        raise RuntimeError("Apple notarization did not accept " + label + "; see Validation/notarization-" + label + ".json")


run("python3", repo / "scripts/generate-project.py")
checks = {}
if args.test:
    product = build(with_validation=True)
    unit_run = subprocess.run(["swift", "test", "--package-path", str(repo)],
                              check=True, cwd=repo, timeout=600, capture_output=True, text=True)
    print(unit_run.stdout, end="")
    print(unit_run.stderr, end="")
    unit_log = unit_run.stdout + unit_run.stderr
    (validation / "unit-tests.log").write_text(unit_log)
    unit_counts = re.findall(r"Executed (\d+) tests, with 0 failures", unit_log)
    if not unit_counts or max(map(int, unit_counts)) == 0:
        raise RuntimeError("No executed XCTest policy cases were reported")
    checks["unit"] = max(map(int, unit_counts))
    test_binary = product / "Contents/MacOS/OverAI"
    # Only this instrumented build contains the test runners and unprotected upload lab.
    run(test_binary, "--self-test", "--output", validation / "lifecycle.json", "--preview", validation / "synthetic-preview.png", timeout=180)
    run(test_binary, "--capture-probe", "--output", validation / "capture.json", timeout=90)
    profile = str(uuid.uuid4())
    for phase in ("write", "read"):
        run(test_binary, "--storage-probe", phase, profile, "--output", validation / ("storage-" + phase + ".json"), timeout=60)
    for name in ("lifecycle", "capture", "storage-write", "storage-read"):
        result = json.loads((validation / (name + ".json")).read_text())
        if result.get("failures") != 0 or not result.get("checks") or any(check.get("passed") is not True or check.get("skipped") for check in result["checks"]):
            raise RuntimeError("Validation failed or no checks ran: " + name)
        checks[name] = len(result["checks"])

# Rebuild after validation to remove test-only entry points and unprotected test windows.
product = build()
with tempfile.TemporaryDirectory(prefix="overai-release-stage-", dir=output) as temp:
    stage = Path(temp)
    app = stage / "OverAI.app"
    shutil.copytree(product, app, symlinks=True)
    binary = verify(app)
    run(binary, "--version", timeout=15)
    for option in ("--self-test", "--upload-lab", "--capture-probe", "--storage-probe"):
        probe = subprocess.run([str(binary), option], capture_output=True, timeout=15)
        if probe.returncode != 2:
            raise RuntimeError("Production app unexpectedly accepts development option " + option)
    if args.release:
        archive = stage / "OverAI.zip"
        run("ditto", "-c", "-k", "--keepParent", app, archive)
        notarize(archive, "app")
        run("xcrun", "stapler", "staple", app)
        run("xcrun", "stapler", "validate", app)
        run("spctl", "--assess", "--type", "execute", "--verbose=2", app)
        verify(app)
    dmg = None
    mode = "release" if args.release else "preview" if args.preview else "local"
    if args.dmg:
        image_folder = stage / "image"
        image_folder.mkdir()
        shutil.copytree(app, image_folder / app.name, symlinks=True)
        (image_folder / "Read Me.txt").write_text(
            "OverAI " + release["version"] + " — Built by Sai Praveen\n\n"
            "Quit the running OverAI app before updating.\n"
            "Drag OverAI.app to Applications, then open it. Your existing native-app sign-ins are preserved.\n"
            "On first launch, choose Show OverAI or Start Hidden. Change this in Settings → General.\n"
            "Default shortcut: Command-G. Change it in Settings.\n"
            "Capture exclusion depends on macOS and your recorder; verify your meeting setup.\n\n" +
            ("Signed with Developer ID and notarized by Apple.\n" if args.release else
             "UNNOTARIZED PREVIEW — ad-hoc signed, not verified by Apple. macOS Gatekeeper may block opening.\n" if args.preview else "LOCAL VALIDATION BUILD — not notarized.\n"), encoding="utf-8")
        dmg = stage / ("OverAI-" + release["version"] + "-" + release["build"] + "-" + mode + "-arm64.dmg")
        dmgbuild.build_dmg(str(dmg), "OverAI", settings={
            "format": "UDZO", "filesystem": "HFS+",
            "files": [str(image_folder / "OverAI.app"), str(image_folder / "Read Me.txt")],
            "symlinks": {"Applications": "/Applications"},
            "hide": ["Read Me.txt"],
            # Changing FinderInfo on a signed .app invalidates strict verification.
            "hide_extensions": [],
            "icon": str(repo / "Sources/OverAI/Resources/icon.icns"),
            "background": str(repo / "assets/dmg-background.png"),
            "window_rect": ((200, 150), (720, 512)),
            "default_view": "icon-view", "arrange_by": None,
            "show_toolbar": False, "show_sidebar": False, "show_status_bar": False,
            "show_pathbar": False, "show_tab_view": False,
            "icon_size": 96, "text_size": 12, "label_pos": "bottom",
            "icon_locations": {"OverAI.app": (205, 268), "Applications": (515, 268)},
            "include_icon_view_settings": True,
        })
        run("hdiutil", "verify", dmg)
        if args.release:
            run("codesign", "--sign", identity, "--timestamp", dmg)
            notarize(dmg, "dmg")
            run("xcrun", "stapler", "staple", dmg)
            run("xcrun", "stapler", "validate", dmg)
            run("spctl", "--assess", "--type", "open", "--context", "context:primary-signature", "--verbose=2", dmg)
        # Validate the actual install image and its Applications link.
        mount = stage / "mount"
        run("hdiutil", "attach", "-readonly", "-nobrowse", "-mountpoint", mount, dmg)
        try:
            mounted_binary = verify(mount / "OverAI.app")
            if hashlib.sha256(mounted_binary.read_bytes()).digest() != hashlib.sha256(binary.read_bytes()).digest():
                raise RuntimeError("Disk image does not contain the validated executable")
            if os.readlink(mount / "Applications") != "/Applications":
                raise RuntimeError("Disk image Applications link is invalid")
            if not (mount / ".DS_Store").is_file() or not list(mount.glob(".background*")):
                raise RuntimeError("Disk image installer layout or background is missing")
        finally:
            run("hdiutil", "detach", mount)
    # Publish generated artifacts only after every requested gate succeeds.
    target_app = output / "OverAI.app"
    backup = stage / "previous.app"
    if target_app.exists():
        target_app.rename(backup)
    try:
        app.rename(target_app)
    except BaseException:
        if backup.exists():
            backup.rename(target_app)
        raise
    final_dmg = output / dmg.name if dmg else None
    if dmg:
        os.replace(dmg, final_dmg)
    manifest = {
        "validatedAt": datetime.now(timezone.utc).isoformat(), "version": release["version"], "build": release["build"],
        "builder": release["builder"], "bundleIdentifier": "com.overai.native", "architecture": "arm64",
        "pricing": "free", "licenseKeyRequired": False,
        "signature": identity, "notarized": args.release, "mode": mode, "checks": checks,
        "developmentModesExcluded": True, "mediaEntitlementsVerified": True, "releaseDebuggerEntitlement": False,
        "requiredLicenseIncluded": True, "dmgMountVerified": dmg is not None, "installerLayoutVerified": dmg is not None,
        "executableSHA256": hashlib.sha256((target_app / "Contents/MacOS/OverAI").read_bytes()).hexdigest(),
        "dmg": final_dmg.name if final_dmg else None,
        "dmgSHA256": hashlib.sha256(final_dmg.read_bytes()).hexdigest() if final_dmg else None,
    }
    manifest_path = output / ("OverAI-" + release["version"] + "-" + release["build"] + "-" + mode + "-manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print("Built:", target_app)
    if final_dmg:
        print("Packaged:", final_dmg)
    print("Manifest:", manifest_path)
