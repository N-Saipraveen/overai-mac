"""
Launcher utilities for OverAI - Startup and permissions management.
Optimized for macOS with proper error handling.
"""

import os
import sys
import getpass
import subprocess
import plistlib
from pathlib import Path
from typing import List, Optional

from Foundation import NSDictionary
from ApplicationServices import AXIsProcessTrustedWithOptions, kAXTrustedCheckOptionPrompt

from .utils.logger import Logger

logger = Logger("launcher")

APP_TITLE = "OverAI"
APP_BUNDLE_ID = f"com.{getpass.getuser()}.overai"


def get_executable_path() -> List[str]:
    """
    Get the executable path for LaunchAgent.
    Returns list suitable for ProgramArguments.
    """
    if getattr(sys, "frozen", False):
        # Running from py2app bundle
        app_path = sys.argv[0]
        while not app_path.endswith(".app"):
            app_path = os.path.dirname(app_path)
        
        executable = os.path.join(app_path, "Contents", "MacOS", APP_TITLE)
        return [executable]
    else:
        # Running from source
        return [sys.executable, "-m", "overai"]


def get_launch_agent_path() -> Path:
    """Get the LaunchAgent plist path."""
    return Path.home() / "Library" / "LaunchAgents" / f"{APP_BUNDLE_ID}.plist"


def install_startup() -> bool:
    """
    Install OverAI as a LaunchAgent to run at login.
    Returns True on success.
    """
    logger.info("Installing startup item")
    
    try:
        plist_path = get_launch_agent_path()
        plist_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create LaunchAgent plist
        plist = {
            "Label": APP_BUNDLE_ID,
            "ProgramArguments": get_executable_path(),
            "RunAtLoad": True,
            "KeepAlive": True,
            "StandardOutPath": str(Path.home() / "Library" / "Logs" / "OverAI" / "launchd.out.log"),
            "StandardErrorPath": str(Path.home() / "Library" / "Logs" / "OverAI" / "launchd.err.log"),
        }
        
        # Write plist
        with open(plist_path, "wb") as f:
            plistlib.dump(plist, f)
        
        # Load the agent
        result = subprocess.run(
            ["launchctl", "load", str(plist_path)],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"Failed to load LaunchAgent: {result.stderr}")
            print(f"❌ Failed to install startup item")
            return False
        
        print(f"✅ {APP_TITLE} will start at login")
        print(f"   Config: {plist_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to install startup: {e}")
        print(f"❌ Error installing startup item: {e}")
        return False


def uninstall_startup() -> bool:
    """
    Uninstall OverAI from startup items.
    Returns True on success.
    """
    logger.info("Uninstalling startup item")
    
    try:
        plist_path = get_launch_agent_path()
        
        if not plist_path.exists():
            print("ℹ️ No startup item found")
            return True
        
        # Unload the agent
        subprocess.run(
            ["launchctl", "unload", str(plist_path)],
            capture_output=True
        )
        
        # Remove plist
        plist_path.unlink()
        
        print(f"✅ {APP_TITLE} removed from startup items")
        return True
        
    except Exception as e:
        logger.error(f"Failed to uninstall startup: {e}")
        print(f"❌ Error removing startup item: {e}")
        return False


def check_permissions(ask: bool = True) -> bool:
    """
    Check and optionally request Accessibility permissions.
    Returns True if granted.
    """
    logger.info(f"Checking permissions (ask={ask})")
    
    try:
        options = NSDictionary.dictionaryWithObject_forKey_(
            True, kAXTrustedCheckOptionPrompt
        ) if ask else None
        
        is_trusted = AXIsProcessTrustedWithOptions(options)
        
        if not is_trusted and ask:
            print("\n⚠️  Accessibility permissions required")
            print("   Please grant permissions in:")
            print("   System Settings → Privacy & Security → Accessibility\n")
        
        return is_trusted
        
    except Exception as e:
        logger.error(f"Error checking permissions: {e}")
        return False


def ensure_accessibility_permissions() -> bool:
    """
    Ensure accessibility permissions are granted.
    Prompts user and waits for permission.
    Returns True if granted, exits if denied.
    """
    if check_permissions(ask=True):
        return True
    
    print("\n⏳ Waiting for Accessibility permissions...")
    print("   (Press Ctrl+C to cancel)\n")
    
    import time
    max_wait = 60  # seconds
    elapsed = 0
    
    try:
        while elapsed < max_wait:
            if check_permissions(ask=False):
                print("✅ Permissions granted!")
                return True
            
            time.sleep(1)
            elapsed += 1
            
            # Show progress every 10 seconds
            if elapsed % 10 == 0:
                print(f"   Still waiting... ({elapsed}s)")
        
        print("\n❌ Permissions not granted within time limit")
        print("   Please run the app again after granting permissions")
        sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n\nCancelled by user")
        sys.exit(0)
