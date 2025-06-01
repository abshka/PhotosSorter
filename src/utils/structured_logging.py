#!/usr/bin/env python3
"""
Structured Logging Module

This module provides enhanced logging functionality with JSON support,
structured data, and different detail levels for the PhotosSorter application.
"""

import json
import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Union
from enum import Enum


class LogLevel(Enum):
    """Enhanced log levels with additional detail levels."""
    TRACE = 5
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class DetailLevel(Enum):
    """Detail levels for different logging contexts."""
    MINIMAL = "minimal"      # Only essential information
    STANDARD = "standard"    # Standard operational information
    DETAILED = "detailed"    # Detailed information including file paths
    VERBOSE = "verbose"      # Very detailed including technical details
    DEBUG = "debug"          # Debug-level information


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def __init__(self, include_extra: bool = True):
        """
        Initialize JSON formatter.

        Args:
            include_extra (bool): Whether to include extra fields in output
        """
        super().__init__()
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record (logging.LogRecord): Log record to format

        Returns:
            str: JSON-formatted log message
        """
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
            }

        # Add extra fields if configured and present
        if self.include_extra:
            extra_fields = {}
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                              'filename', 'module', 'lineno', 'funcName', 'created', 'msecs',
                              'relativeCreated', 'thread', 'threadName', 'processName', 'process',
                              'getMessage', 'exc_info', 'exc_text', 'stack_info']:
                    extra_fields[key] = value

            if extra_fields:
                log_entry["extra"] = extra_fields

        return json.dumps(log_entry, default=str, ensure_ascii=False)


class HumanReadableFormatter(logging.Formatter):
    """Human-readable formatter with configurable detail levels."""

    def __init__(self, detail_level: DetailLevel = DetailLevel.STANDARD):
        """
        Initialize human-readable formatter.

        Args:
            detail_level (DetailLevel): Level of detail to include
        """
        self.detail_level = detail_level

        # Different format strings for different detail levels
        self.formats = {
            DetailLevel.MINIMAL: "%(levelname)s: %(message)s",
            DetailLevel.STANDARD: "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            DetailLevel.DETAILED: "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s",
            DetailLevel.VERBOSE: "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s",
            DetailLevel.DEBUG: "%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(funcName)s:%(lineno)d - %(message)s"
        }

        format_string = self.formats.get(detail_level, self.formats[DetailLevel.STANDARD])
        super().__init__(format_string, datefmt='%Y-%m-%d %H:%M:%S')

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with human-readable output.

        Args:
            record (logging.LogRecord): Log record to format

        Returns:
            str: Formatted log message
        """
        # Add extra fields to message if present and detail level is high enough
        formatted = super().format(record)

        if self.detail_level in [DetailLevel.VERBOSE, DetailLevel.DEBUG]:
            extra_fields = {}
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                              'filename', 'module', 'lineno', 'funcName', 'created', 'msecs',
                              'relativeCreated', 'thread', 'threadName', 'processName', 'process',
                              'getMessage', 'exc_info', 'exc_text', 'stack_info']:
                    extra_fields[key] = value

            if extra_fields:
                extra_str = " | ".join(f"{k}={v}" for k, v in extra_fields.items())
                formatted = f"{formatted} [{extra_str}]"

        return formatted


class PhotosSorterLogger:
    """Enhanced logger for PhotosSorter with structured logging capabilities."""

    def __init__(self, name: str, config: Dict[str, Any] = None):
        """
        Initialize PhotosSorter logger.

        Args:
            name (str): Logger name
            config (Dict[str, Any]): Logger configuration
        """
        self.name = name
        self.config = config or {}
        self.logger = logging.getLogger(name)
        self._setup_logger()

    def _setup_logger(self):
        """Setup logger with configured handlers and formatters."""
        # Clear existing handlers
        self.logger.handlers.clear()

        # Set log level
        log_level = self.config.get('level', 'INFO').upper()
        self.logger.setLevel(getattr(logging, log_level))

        # Setup console handler
        self._setup_console_handler()

        # Setup file handler
        self._setup_file_handler()

        # Setup JSON file handler if configured
        if self.config.get('json_logging', {}).get('enabled', False):
            self._setup_json_handler()

        # Prevent propagation to root logger
        self.logger.propagate = False

    def _setup_console_handler(self):
        """Setup console logging handler."""
        console_config = self.config.get('console', {})

        if console_config.get('enabled', True):
            handler = logging.StreamHandler(sys.stdout)

            detail_level = DetailLevel(console_config.get('detail_level', 'standard'))
            formatter = HumanReadableFormatter(detail_level)
            handler.setFormatter(formatter)

            # Set handler-specific log level
            handler_level = console_config.get('level', self.config.get('level', 'INFO')).upper()
            handler.setLevel(getattr(logging, handler_level))

            self.logger.addHandler(handler)

    def _setup_file_handler(self):
        """Setup file logging handler with rotation."""
        file_config = self.config.get('file', {})

        if file_config.get('enabled', True):
            log_file = file_config.get('path', 'logs/photos_sorter.log')
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            # Use rotating file handler
            max_size = file_config.get('max_size_mb', 10) * 1024 * 1024
            backup_count = file_config.get('backup_count', 5)

            handler = logging.handlers.RotatingFileHandler(
                log_path,
                maxBytes=max_size,
                backupCount=backup_count,
                encoding='utf-8'
            )

            detail_level = DetailLevel(file_config.get('detail_level', 'detailed'))
            formatter = HumanReadableFormatter(detail_level)
            handler.setFormatter(formatter)

            # Set handler-specific log level
            handler_level = file_config.get('level', 'DEBUG').upper()
            handler.setLevel(getattr(logging, handler_level))

            self.logger.addHandler(handler)

    def _setup_json_handler(self):
        """Setup JSON logging handler."""
        json_config = self.config.get('json_logging', {})

        json_file = json_config.get('path', 'logs/photos_sorter.json')
        json_path = Path(json_file)
        json_path.parent.mkdir(parents=True, exist_ok=True)

        # Use rotating file handler for JSON logs
        max_size = json_config.get('max_size_mb', 50) * 1024 * 1024
        backup_count = json_config.get('backup_count', 3)

        handler = logging.handlers.RotatingFileHandler(
            json_path,
            maxBytes=max_size,
            backupCount=backup_count,
            encoding='utf-8'
        )

        include_extra = json_config.get('include_extra_fields', True)
        formatter = JSONFormatter(include_extra=include_extra)
        handler.setFormatter(formatter)

        # Set handler-specific log level
        handler_level = json_config.get('level', 'INFO').upper()
        handler.setLevel(getattr(logging, handler_level))

        self.logger.addHandler(handler)

    def trace(self, message: str, **kwargs):
        """Log trace message (custom level)."""
        self._log(LogLevel.TRACE.value, message, **kwargs)

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message."""
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message."""
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self._log(logging.CRITICAL, message, **kwargs)

    def _log(self, level: int, message: str, **kwargs):
        """Internal logging method with extra context."""
        if self.logger.isEnabledFor(level):
            self.logger.log(level, message, extra=kwargs)

    def log_file_operation(self, operation: str, source: Path, target: Path = None,
                          success: bool = True, duration: float = None, **kwargs):
        """
        Log file operation with structured data.

        Args:
            operation (str): Type of operation (move, copy, merge, etc.)
            source (Path): Source file path
            target (Path): Target file path (optional)
            success (bool): Whether operation was successful
            duration (float): Operation duration in seconds
            **kwargs: Additional context data
        """
        extra_data = {
            'operation': operation,
            'source_path': str(source),
            'success': success,
            **kwargs
        }

        if target:
            extra_data['target_path'] = str(target)

        if duration is not None:
            extra_data['duration_seconds'] = duration

        level = logging.INFO if success else logging.ERROR
        message = f"{operation.title()} {'successful' if success else 'failed'}: {source.name}"

        if target and success:
            message += f" -> {target.name}"

        self._log(level, message, **extra_data)

    def log_processing_summary(self, stats: Dict[str, Any], duration: float = None):
        """
        Log processing summary with statistics.

        Args:
            stats (Dict[str, Any]): Processing statistics
            duration (float): Total processing duration
        """
        extra_data = {
            'processing_stats': stats,
            'summary': True
        }

        if duration is not None:
            extra_data['total_duration_seconds'] = duration

        message = f"Processing complete: {stats.get('processed', 0)} files processed"
        if stats.get('errors', 0) > 0:
            message += f", {stats['errors']} errors"

        self._log(logging.INFO, message, **extra_data)

    def log_performance_metric(self, metric_name: str, value: Union[int, float],
                             unit: str = None, **kwargs):
        """
        Log performance metric.

        Args:
            metric_name (str): Name of the metric
            value (Union[int, float]): Metric value
            unit (str): Unit of measurement
            **kwargs: Additional metric context
        """
        extra_data = {
            'metric_name': metric_name,
            'metric_value': value,
            'performance_metric': True,
            **kwargs
        }

        if unit:
            extra_data['unit'] = unit

        message = f"Performance metric - {metric_name}: {value}"
        if unit:
            message += f" {unit}"

        self._log(logging.DEBUG, message, **extra_data)

    def log_cache_event(self, event_type: str, key: str, hit: bool = None, **kwargs):
        """
        Log cache-related events.

        Args:
            event_type (str): Type of cache event (hit, miss, set, clear)
            key (str): Cache key
            hit (bool): Whether it was a cache hit (for get operations)
            **kwargs: Additional cache context
        """
        extra_data = {
            'cache_event': event_type,
            'cache_key': key,
            **kwargs
        }

        if hit is not None:
            extra_data['cache_hit'] = hit

        message = f"Cache {event_type}: {key}"
        self._log(LogLevel.TRACE.value, message, **extra_data)


class LoggerManager:
    """Manager for PhotosSorter loggers."""

    _loggers: Dict[str, PhotosSorterLogger] = {}
    _default_config: Dict[str, Any] = {}

    @classmethod
    def set_default_config(cls, config: Dict[str, Any]):
        """Set default configuration for all loggers."""
        cls._default_config = config

    @classmethod
    def get_logger(cls, name: str, config: Dict[str, Any] = None) -> PhotosSorterLogger:
        """
        Get or create a logger instance.

        Args:
            name (str): Logger name
            config (Dict[str, Any]): Logger configuration (optional)

        Returns:
            PhotosSorterLogger: Logger instance
        """
        if name not in cls._loggers:
            logger_config = config or cls._default_config
            cls._loggers[name] = PhotosSorterLogger(name, logger_config)

        return cls._loggers[name]

    @classmethod
    def configure_all_loggers(cls, config: Dict[str, Any]):
        """Reconfigure all existing loggers."""
        cls._default_config = config

        for logger in cls._loggers.values():
            logger.config = config
            logger._setup_logger()

    @classmethod
    def shutdown(cls):
        """Shutdown all loggers and handlers."""
        for logger in cls._loggers.values():
            for handler in logger.logger.handlers:
                handler.close()
        cls._loggers.clear()


def setup_structured_logging(config: Dict[str, Any]) -> PhotosSorterLogger:
    """
    Setup structured logging for PhotosSorter.

    Args:
        config (Dict[str, Any]): Logging configuration

    Returns:
        PhotosSorterLogger: Configured main logger
    """
    # Add TRACE level to logging module
    logging.addLevelName(LogLevel.TRACE.value, "TRACE")

    # Set default configuration
    LoggerManager.set_default_config(config)

    # Return main application logger
    return LoggerManager.get_logger('photos_sorter')


def main():
    """Test function for structured logging."""
    from pathlib import Path
    import time

    # Test configuration
    config = {
        'level': 'DEBUG',
        'console': {
            'enabled': True,
            'detail_level': 'verbose',
            'level': 'INFO'
        },
        'file': {
            'enabled': True,
            'path': 'test_logs/test.log',
            'detail_level': 'detailed',
            'level': 'DEBUG',
            'max_size_mb': 1,
            'backup_count': 2
        },
        'json_logging': {
            'enabled': True,
            'path': 'test_logs/test.json',
            'level': 'INFO',
            'include_extra_fields': True
        }
    }

    # Setup logging
    logger = setup_structured_logging(config)

    # Test different log levels
    logger.trace("This is a trace message")
    logger.debug("This is a debug message")
    logger.info("Application started")
    logger.warning("This is a warning")
    logger.error("This is an error")

    # Test structured logging
    logger.log_file_operation(
        operation="copy",
        source=Path("test.jpg"),
        target=Path("photos/2024/01/15/test.jpg"),
        success=True,
        duration=0.123,
        file_size=1024000
    )

    # Test performance metrics
    logger.log_performance_metric("files_per_second", 15.7, "files/sec")

    # Test cache events
    logger.log_cache_event("hit", "photo_123.jpg", hit=True)

    # Test processing summary
    stats = {
        'processed': 150,
        'moved': 140,
        'errors': 2,
        'cache_hits': 45,
        'cache_misses': 105
    }
    logger.log_processing_summary(stats, duration=45.6)

    print("Structured logging test completed. Check test_logs/ directory for output.")


if __name__ == "__main__":
    main()
