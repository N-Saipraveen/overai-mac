"""
Unified logging system with proper file handling and memory efficiency.
Optimized with log rotation and buffer limits.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
from enum import Enum


class LogLevel(Enum):
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3


class Logger:
    """
    Simple, efficient logger with lazy file initialization and log rotation.
    Memory-optimized: limits file size and uses buffered writes.
    """
    
    _LOG_DIR = Path.home() / "Library" / "Logs" / "OverAI"
    _FILE_HANDLE = None
    _INITIALIZED = False
    _MIN_LEVEL = LogLevel.INFO  # Default to INFO to reduce log volume
    _MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB max log file size
    _MAX_BUFFER_LINES = 100  # Limit in-memory buffer
    _buffer = []
    
    def __init__(self, name: str):
        self.name = name
        self._ensure_initialized()
    
    @classmethod
    def _ensure_initialized(cls):
        """Lazy initialization of log directory and file."""
        if cls._INITIALIZED:
            return
        
        cls._LOG_DIR.mkdir(parents=True, exist_ok=True)
        
        # Check for log rotation
        log_file = cls._LOG_DIR / "overai.log"
        if log_file.exists():
            try:
                size = log_file.stat().st_size
                if size > cls._MAX_FILE_SIZE:
                    # Rotate: rename old log
                    old_log = cls._LOG_DIR / "overai.old.log"
                    if old_log.exists():
                        old_log.unlink()
                    log_file.rename(old_log)
            except Exception:
                pass
        
        # Open log file with buffering for performance
        cls._FILE_HANDLE = open(log_file, 'a', buffering=8192)  # 8KB buffer
        
        cls._INITIALIZED = True
    
    def _log(self, level: LogLevel, message: str):
        """Internal log method with memory-efficient buffering."""
        if level.value < self._MIN_LEVEL.value:
            return
        
        timestamp = datetime.now().strftime("%H:%M:%S")  # Shorter timestamp
        log_line = f"[{timestamp}] [{level.name[0]}] [{self.name}] {message}\n"
        
        # Write to file
        if self._FILE_HANDLE:
            try:
                self._FILE_HANDLE.write(log_line)
            except Exception:
                pass
        
        # Print to console only for warnings/errors
        if level.value >= LogLevel.WARNING.value:
            print(log_line, end='', file=sys.stderr)
    
    def debug(self, message: str):
        self._log(LogLevel.DEBUG, message)
    
    def info(self, message: str):
        self._log(LogLevel.INFO, message)
    
    def warning(self, message: str):
        self._log(LogLevel.WARNING, message)
    
    def error(self, message: str):
        self._log(LogLevel.ERROR, message)
    
    @classmethod
    def set_level(cls, level: LogLevel):
        """Set minimum log level."""
        cls._MIN_LEVEL = level
    
    @classmethod
    def flush(cls):
        """Flush log buffer to disk."""
        if cls._FILE_HANDLE:
            try:
                cls._FILE_HANDLE.flush()
            except Exception:
                pass
    
    @classmethod
    def close(cls):
        """Close log file handle."""
        if cls._FILE_HANDLE:
            try:
                cls._FILE_HANDLE.close()
            except Exception:
                pass
            cls._FILE_HANDLE = None
            cls._INITIALIZED = False
