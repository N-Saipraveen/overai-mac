"""
launcher.py
Startup/permission utilities for OverAI - the universal Mac AI overlay.
"""

# Python libraries.
import getpass
import os
import subprocess
import sys
import time
from pathlib import Path

# Apple libraries.
import plistlib
from Foundation import NSDictionary
from ApplicationServices import AXIsProcessTrustedWithOptions, kAXTrustedCheckOptionPrompt

# Local libraries
from .constants import APP_TITLE
from .health_checks import reset_crash_counter

# --- App Path Utilities ---

def get_executable():
    """
    Return the appropriate executable/program_args list for LaunchAgent or CLI usage.
    """
    if getattr(sys, "frozen", False):  # Running from a py2app bundle
        assert (".app" in sys.argv[0]), f"Expected .app in sys.argv[0], got {sys.argv[0]}"
        # Find the .app bundle path
        app_path = sys.argv[0]
        while not app_path.endswith(".app"):
            app_path = os.path.dirname(app_path)
        # Main binary inside .app/Contents/MacOS/OverAI
        executable = os.path.join(app_path, "Contents", "MacOS", APP_TITLE)
        program_args = [executable]
    else:  # Running from source (pip install or python -m ...)
        program_args = [sys.executable, "-m", APP_TITLE.lower()]
    return program_args

# --- LaunchAgent Install/Uninstall ---

def install_startup():
    """
    Install OverAI as a LaunchAgent (run at login) for this user.
    """
    username = getpass.getuser()
    program_args = get_executable()
    plist = {
        "Label": f"com.{username}.{APP_TITLE.lower()}",
        "ProgramArguments": program_args,
        "RunAtLoad": True,
        "KeepAlive": True,
    }
    launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
    launch_agents_dir.mkdir(parents=True, exist_ok=True)
    plist_path = launch_agents_dir / f"com.{username}.{APP_TITLE.lower()}.plist"
    with open(plist_path, "wb") as f:
        plistlib.dump(plist, f)
    result = os.system(f"launchctl load {plist_path}")
    if result != 0:
        print(f"Failed to load LaunchAgent. Exit code: {result}")
        return False
    print(f"✅ OverAI installed as a startup app (LaunchAgent created at {plist_path}).")
    print(f"To uninstall, run: {APP_TITLE.lower()} --uninstall-startup")
    return True

def uninstall_startup():
    """
    Remove OverAI LaunchAgent from user login items.
    """
    username = getpass.getuser()
    launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
    plist_path = launch_agents_dir / f"com.{username}.{APP_TITLE.lower()}.plist"
    if plist_path.exists():
        try:
            os.system(f"launchctl unload {plist_path}")
            print(f"OverAI LaunchAgent unloaded.")
        except Exception as e:
            print(f"Failed to unload LaunchAgent. Exception:\n{e}")
        print(f"LaunchAgent file removed: {plist_path}")
        os.remove(plist_path)
        return True
    else:
        print("No OverAI LaunchAgent found. Nothing to uninstall.")
        return False

# --- Accessibility Permissions ---

def check_permissions(ask=True):
    """
    Check (and optionally prompt for) macOS Accessibility permissions.
    """
    print(f"\nChecking macOS Accessibility permissions for OverAI. If not already granted, a dialog may appear.\n", flush=True)
    options = NSDictionary.dictionaryWithObject_forKey_(
        True, kAXTrustedCheckOptionPrompt
    )
    is_trusted = AXIsProcessTrustedWithOptions(options if ask else None)
    return is_trusted

def get_updated_permission_status():
    """
    Check current permission status by spawning a subprocess.
    """
    result = subprocess.run(
        get_executable() + ["--check-permissions"],
        capture_output=True,
        text=True
    )
    return result.returncode == 0

def wait_for_permissions(max_wait_sec=60, wait_interval_sec=5):
    """
    Poll for permissions for up to max_wait_sec seconds.
    """
    elapsed = 0
    while elapsed < max_wait_sec:
        if get_updated_permission_status():
            return True
        time.sleep(wait_interval_sec)
        elapsed += wait_interval_sec
        reset_crash_counter()
    return False

def ensure_accessibility_permissions():
    """
    Ensure Accessibility permissions are granted; otherwise, exit/uninstall.
    """
    if check_permissions():  # Initial call to prompt
        return
    if wait_for_permissions():
        print("Permissions granted! Exiting for auto-restart...")
        return
    else:
        print("Permissions NOT granted within time limit. Uninstalling OverAI.")
        uninstall_startup()