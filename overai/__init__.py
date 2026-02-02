"""
OverAI - A modern, accessible AI overlay for macOS.

Every AI in a single window.
Designed with Apple Human Interface Guidelines.
Optimized for memory efficiency and accessibility.

-- Sai Praveen
"""

import os
from pathlib import Path

# Package directory
PACKAGE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
ABOUT_DIR = PACKAGE_DIR / "about"


def _read_about_file(filename: str, default: str = "") -> str:
    """Read metadata from about directory."""
    try:
        filepath = ABOUT_DIR / filename
        if filepath.exists():
            return filepath.read_text().strip()
    except Exception:
        pass
    return default


# Version info
__version__ = _read_about_file("version.txt", "2.0.0")
__author__ = _read_about_file("author.txt", "Sai Praveen")

# Public API
__all__ = ["main", "__version__", "__author__"]

# Import main for easy access
from .main import main
