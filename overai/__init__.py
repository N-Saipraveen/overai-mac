"""
OverAI - A macOS overlay app for OverAI.

Every AI in a single window.

-- Sai Praveen 
"""

import os

DIRECTORY = os.path.dirname(os.path.abspath(__file__))
ABOUT_DIR = os.path.join(DIRECTORY, "about")

def _read_about_file(fname, default=""):
    try:
        with open(os.path.join(ABOUT_DIR, fname)) as f:
            return f.read().strip()
    except Exception:
        return default

__version__ = _read_about_file("version.txt", "0.0.1")
__author__ = _read_about_file("author.txt", "Sai Praveen")

__all__ = ["main"]

from .main import main  

# Only import if you want "from overai import main" to work.