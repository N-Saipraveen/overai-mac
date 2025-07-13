# setup.py
from setuptools import setup

APP = ["OverAI.py"]
DATA_FILES = []
OPTIONS = {
    # Bundle your package directory so imports “just work”
    "packages": ["overai"],
    "includes": [],
    # GUI app (no console window)
    "argv_emulation": False,
    # Optional: your .icns icon
    "iconfile": "overai/logo/icon.icns",
    # Allow microphone & Accessibility prompts by embedding Info.plist keys:
    "plist": {
        "NSMicrophoneUsageDescription": "OverAI needs your mic for voice input.",
        "NSAppleEventsUsageDescription": "OverAI needs accessibility permission for hotkeys."
    },
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)