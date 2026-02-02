"""
Setup script for OverAI - macOS AI Overlay Application.
Uses py2app for building standalone .app bundles.
"""

from setuptools import setup, find_packages

# Read version
version = "2.0.0"
try:
    with open("overai/about/version.txt") as f:
        version = f.read().strip()
except:
    pass

# Read long description
try:
    with open("README.md", encoding="utf-8") as f:
        long_description = f.read()
except:
    long_description = "AI Overlay for macOS"

APP = ["OverAI.py"]

# py2app options
OPTIONS = {
    "packages": ["overai"],
    "includes": [
        "objc",
        "AppKit",
        "Foundation",
        "WebKit",
        "Quartz",
        "AVFoundation",
        "ApplicationServices",
        "psutil",
    ],
    "excludes": [
        "tkinter",
        "matplotlib",
        "numpy",
        "pandas",
        "PIL",
        "scipy",
        "tensorflow",
        "torch",
    ],
    "argv_emulation": False,
    "iconfile": "overai/logo/icon.icns",
    "plist": {
        "CFBundleName": "OverAI",
        "CFBundleDisplayName": "OverAI",
        "CFBundleVersion": version,
        "CFBundleShortVersionString": version,
        "NSHumanReadableCopyright": "© 2024 Sai Praveen",
        # Permissions
        "NSMicrophoneUsageDescription": "OverAI needs microphone access for voice input to AI services.",
        "NSAppleEventsUsageDescription": "OverAI needs accessibility permission for global hotkeys.",
        # Security
        "LSBackgroundOnly": False,
        "LSUIElement": True,  # Agent app (no dock icon)
        # App category
        "LSApplicationCategoryType": "public.app-category.productivity",
    },
    # Optimization
    "optimize": 1,
    "compressed": True,
    "strip": True,
}

setup(
    name="OverAI",
    version=version,
    description="AI Overlay for macOS",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Sai Praveen",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "overai": [
            "about/*.txt",
            "logo/*.png",
            "logo/*.icns",
        ],
    },
    install_requires=[
        "pyobjc>=10.0",
        "pyobjc-framework-Cocoa>=10.0",
        "pyobjc-framework-Quartz>=10.0",
        "pyobjc-framework-WebKit>=10.0",
        "pyobjc-framework-AVFoundation>=10.0",
        "pyobjc-framework-ApplicationServices>=10.0",
        "psutil>=5.9.0",
    ],
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "overai=overai.main:main",
        ],
    },
    app=APP,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: MacOS X :: Cocoa",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS :: MacOS X",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Utilities",
    ],
)
