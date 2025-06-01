#!/usr/bin/env python3
"""
Utils Package

This package contains utility modules for the PhotosSorter application.
"""

from .statistics import StatisticsCollector, ProcessingStats
from .exceptions import (
    PhotoSorterError, ConfigurationError, PhotoSorterFileNotFoundError, DirectoryNotFoundError,
    PhotoSorterPermissionError, ExifError, VideoProcessingError, MergeError, DependencyError,
    ValidationError, BatchOperationError, DuplicateFileError, DateExtractionError,
    FFmpegError, CacheError, StatisticsError, handle_exception, format_error_report
)
from .config_validator import ConfigValidator
from .interfaces import (
    DateExtractor, FileProcessor, StatisticsProvider, FileGrouper, BatchProcessor,
    MediaFileDiscoverer, CacheProvider, ProgressReporter, ErrorHandler,
    VideoThumbnailMerger, OrganizationStrategy, DateExtractorFactory, FileProcessorFactory,
    LoggerMixin, ConfigurableMixin
)
from .structured_logging import (
    PhotosSorterLogger, LoggerManager, JSONFormatter, HumanReadableFormatter,
    LogLevel, DetailLevel, setup_structured_logging
)

__all__ = [
    # Statistics
    'StatisticsCollector', 'ProcessingStats',
    # Configuration
    'ConfigValidator',
    # Exceptions
    'PhotoSorterError', 'ConfigurationError', 'PhotoSorterFileNotFoundError', 'DirectoryNotFoundError',
    'PhotoSorterPermissionError', 'ExifError', 'VideoProcessingError', 'MergeError', 'DependencyError',
    'ValidationError', 'BatchOperationError', 'DuplicateFileError', 'DateExtractionError',
    'FFmpegError', 'CacheError', 'StatisticsError', 'handle_exception', 'format_error_report',
    # Interfaces and abstractions
    'DateExtractor', 'FileProcessor', 'StatisticsProvider', 'FileGrouper', 'BatchProcessor',
    'MediaFileDiscoverer', 'CacheProvider', 'ProgressReporter', 'ErrorHandler',
    'VideoThumbnailMerger', 'OrganizationStrategy', 'DateExtractorFactory', 'FileProcessorFactory',
    'LoggerMixin', 'ConfigurableMixin',
    # Structured logging
    'PhotosSorterLogger', 'LoggerManager', 'JSONFormatter', 'HumanReadableFormatter',
    'LogLevel', 'DetailLevel', 'setup_structured_logging'
]