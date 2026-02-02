"""
OverAI - Main entry point for the macOS AI overlay application.
Optimized for memory efficiency and Apple Design compliance.
"""

import sys
import argparse

# Import AppKit early for NSApplication
from AppKit import NSApplication

from .utils.logger import Logger
from .core.app_delegate import AppDelegate
from .launcher import check_permissions, install_startup, uninstall_startup
from .health_checks import health_check_decorator

logger = Logger("main")

APP_TITLE = "OverAI"
PERMISSION_CHECK_EXIT = 1


def create_argument_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        description=f"{APP_TITLE} - AI Overlay for macOS"
    )
    
    parser.add_argument(
        "--install-startup",
        action="store_true",
        help="Install to run at login"
    )
    
    parser.add_argument(
        "--uninstall-startup",
        action="store_true",
        help="Uninstall from login items"
    )
    
    parser.add_argument(
        "--check-permissions",
        action="store_true",
        help="Check Accessibility permissions"
    )
    
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version information"
    )
    
    return parser


@health_check_decorator
def run_app():
    """Run the main application."""
    logger.info(f"Starting {APP_TITLE}")
    
    # Check if we're in a GUI environment
    import os
    if os.environ.get('SSH_CONNECTION') or os.environ.get('SSH_CLIENT'):
        print("Error: Cannot run OverAI over SSH. Please run locally.")
        sys.exit(1)
    
    # Check permissions
    check_permissions()
    
    # Create application
    app = NSApplication.sharedApplication()
    
    # Create and set delegate
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    
    # Print startup info
    print(f"\n{'='*50}")
    print(f"  🚀 {APP_TITLE} is starting...")
    print(f"  Press ⌘+G to toggle the overlay")
    print(f"  Look for the icon in your menu bar")
    print(f"{'='*50}\n")
    
    # Run the app
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        logger.info("Application terminated by user")


def main():
    """Main entry point."""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Handle version
    if args.version:
        from . import __version__
        print(f"{APP_TITLE} {__version__}")
        sys.exit(0)
    
    # Handle startup installation
    if args.install_startup:
        success = install_startup()
        sys.exit(0 if success else 1)
    
    # Handle startup uninstallation
    if args.uninstall_startup:
        success = uninstall_startup()
        sys.exit(0 if success else 1)
    
    # Handle permission check
    if args.check_permissions:
        is_trusted = check_permissions(ask=False)
        print("Accessibility permissions:", "granted" if is_trusted else "denied")
        sys.exit(0 if is_trusted else PERMISSION_CHECK_EXIT)
    
    # Run the application
    try:
        run_app()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
