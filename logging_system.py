#!/usr/bin/env python3
"""
Comprehensive Logging System for Rubix Recorder API Server

Features:
- Rotating file logs with size and time-based rotation
- Multiple log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Structured JSON logs for easy parsing
- Crash detection and recovery tracking
- Remote log management via API
- Automatic log purging
"""

import logging
import logging.handlers
import os
import sys
import json
import gzip
import shutil
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any


class JSONFormatter(logging.Formatter):
    """Format log records as JSON for structured logging"""

    def format(self, record):
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': self.formatException(record.exc_info)
            }

        # Add extra fields if present
        if hasattr(record, 'extra_data'):
            log_data['extra'] = record.extra_data

        return json.dumps(log_data)


class LoggingSystem:
    """Central logging system manager"""

    def __init__(self,
                 log_dir: str = 'logs',
                 max_file_size: int = 10 * 1024 * 1024,  # 10 MB
                 backup_count: int = 10,
                 log_level: str = 'INFO'):
        """
        Initialize logging system

        Args:
            log_dir: Directory for log files
            max_file_size: Maximum size of each log file in bytes
            backup_count: Number of backup log files to keep
            log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)

        # Track server start time and crashes
        self.start_time = datetime.now()
        self.crash_file = self.log_dir / '.crash_tracker.json'
        self._load_crash_tracker()

        # Setup loggers
        self._setup_loggers()

    def _load_crash_tracker(self):
        """Load crash tracking data"""
        if self.crash_file.exists():
            try:
                with open(self.crash_file, 'r') as f:
                    self.crash_data = json.load(f)
            except Exception:
                self.crash_data = {'crashes': [], 'clean_shutdowns': 0}
        else:
            self.crash_data = {'crashes': [], 'clean_shutdowns': 0}

        # Check if last shutdown was clean
        if self.crash_data.get('running', False):
            # Server was running but is starting now = crash detected
            last_start = self.crash_data.get('last_start')
            self.crash_data['crashes'].append({
                'detected_at': datetime.now().isoformat(),
                'last_start': last_start,
                'type': 'unexpected_shutdown'
            })

        # Mark as running
        self.crash_data['running'] = True
        self.crash_data['last_start'] = self.start_time.isoformat()
        self._save_crash_tracker()

    def _save_crash_tracker(self):
        """Save crash tracking data"""
        try:
            with open(self.crash_file, 'w') as f:
                json.dump(self.crash_data, f, indent=2)
        except Exception as e:
            print(f"Failed to save crash tracker: {e}", file=sys.stderr)

    def mark_clean_shutdown(self):
        """Mark that server is shutting down cleanly"""
        self.crash_data['running'] = False
        self.crash_data['clean_shutdowns'] = self.crash_data.get('clean_shutdowns', 0) + 1
        self.crash_data['last_shutdown'] = datetime.now().isoformat()
        self._save_crash_tracker()

    def _setup_loggers(self):
        """Setup all log handlers"""
        # Main application log (rotating)
        self.app_log = self.log_dir / 'app.log'
        app_handler = logging.handlers.RotatingFileHandler(
            self.app_log,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count
        )
        app_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        app_handler.setLevel(self.log_level)

        # JSON structured log (rotating)
        self.json_log = self.log_dir / 'app.json.log'
        json_handler = logging.handlers.RotatingFileHandler(
            self.json_log,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count
        )
        json_handler.setFormatter(JSONFormatter())
        json_handler.setLevel(self.log_level)

        # Error log (errors only, rotating)
        self.error_log = self.log_dir / 'errors.log'
        error_handler = logging.handlers.RotatingFileHandler(
            self.error_log,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count
        )
        error_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s\n%(pathname)s:%(lineno)d\n'
        ))
        error_handler.setLevel(logging.ERROR)

        # Console handler (stdout)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        console_handler.setLevel(logging.INFO)

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)

        # Remove existing handlers
        root_logger.handlers.clear()

        # Add all handlers
        root_logger.addHandler(app_handler)
        root_logger.addHandler(json_handler)
        root_logger.addHandler(error_handler)
        root_logger.addHandler(console_handler)

        # Log startup
        logging.info("=" * 60)
        logging.info("Logging system initialized")
        logging.info(f"Log directory: {self.log_dir.absolute()}")
        logging.info(f"Log level: {logging.getLevelName(self.log_level)}")
        logging.info(f"Max file size: {self.max_file_size / 1024 / 1024:.1f} MB")
        logging.info(f"Backup count: {self.backup_count}")
        logging.info("=" * 60)

        # Log crash history
        if self.crash_data['crashes']:
            logging.warning(f"Detected {len(self.crash_data['crashes'])} previous crashes")
            for crash in self.crash_data['crashes'][-3:]:  # Show last 3
                logging.warning(f"  - {crash['type']} at {crash['detected_at']}")

    def get_log_files(self) -> List[Dict[str, Any]]:
        """Get list of all log files with metadata"""
        log_files = []

        for log_file in self.log_dir.glob('*.log*'):
            if log_file.name.startswith('.'):
                continue  # Skip hidden files

            stat = log_file.stat()
            log_files.append({
                'name': log_file.name,
                'path': str(log_file),
                'size': stat.st_size,
                'size_mb': round(stat.st_size / 1024 / 1024, 2),
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'is_gzip': log_file.suffix == '.gz'
            })

        # Sort by modification time (newest first)
        log_files.sort(key=lambda x: x['modified'], reverse=True)
        return log_files

    def read_log(self, filename: str, lines: int = 100, offset: int = 0) -> List[str]:
        """
        Read log file

        Args:
            filename: Name of log file
            lines: Number of lines to read
            offset: Number of lines to skip from end

        Returns:
            List of log lines
        """
        log_path = self.log_dir / filename

        if not log_path.exists():
            raise FileNotFoundError(f"Log file not found: {filename}")

        # Handle gzipped files
        if log_path.suffix == '.gz':
            with gzip.open(log_path, 'rt') as f:
                all_lines = f.readlines()
        else:
            with open(log_path, 'r') as f:
                all_lines = f.readlines()

        # Return last N lines with offset
        start = max(0, len(all_lines) - lines - offset)
        end = len(all_lines) - offset if offset > 0 else len(all_lines)

        return all_lines[start:end]

    def purge_old_logs(self, days: int = 30) -> Dict[str, Any]:
        """
        Delete logs older than specified days

        Args:
            days: Delete logs older than this many days

        Returns:
            Statistics about purged files
        """
        cutoff_time = datetime.now() - timedelta(days=days)
        deleted_files = []
        total_size = 0

        for log_file in self.log_dir.glob('*.log*'):
            if log_file.name.startswith('.'):
                continue

            stat = log_file.stat()
            mod_time = datetime.fromtimestamp(stat.st_mtime)

            if mod_time < cutoff_time:
                size = stat.st_size
                log_file.unlink()
                deleted_files.append({
                    'name': log_file.name,
                    'size': size,
                    'modified': mod_time.isoformat()
                })
                total_size += size

        result = {
            'deleted_count': len(deleted_files),
            'total_size_mb': round(total_size / 1024 / 1024, 2),
            'files': deleted_files
        }

        logging.info(f"Purged {len(deleted_files)} old log files ({result['total_size_mb']} MB)")
        return result

    def get_crash_history(self) -> Dict[str, Any]:
        """Get crash and uptime statistics"""
        uptime_seconds = (datetime.now() - self.start_time).total_seconds()

        return {
            'current_uptime_seconds': uptime_seconds,
            'current_uptime_human': self._format_duration(uptime_seconds),
            'start_time': self.start_time.isoformat(),
            'total_crashes': len(self.crash_data.get('crashes', [])),
            'clean_shutdowns': self.crash_data.get('clean_shutdowns', 0),
            'recent_crashes': self.crash_data.get('crashes', [])[-5:],  # Last 5
            'running': self.crash_data.get('running', False)
        }

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format duration in human-readable form"""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if secs > 0 or not parts:
            parts.append(f"{secs}s")

        return " ".join(parts)


# Global logging system instance
_logging_system: Optional[LoggingSystem] = None


def get_logging_system() -> LoggingSystem:
    """Get or create global logging system instance"""
    global _logging_system
    if _logging_system is None:
        _logging_system = LoggingSystem()
    return _logging_system


def setup_exception_logging():
    """Setup global exception handler to log all uncaught exceptions"""
    def exception_handler(exc_type, exc_value, exc_traceback):
        """Log uncaught exceptions"""
        if issubclass(exc_type, KeyboardInterrupt):
            # Let KeyboardInterrupt pass through
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logging.critical(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )

    sys.excepthook = exception_handler
