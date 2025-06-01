#!/usr/bin/env python3
"""
Interfaces and Abstractions Module

This module defines interfaces and abstract base classes for the PhotosSorter
application to provide better code organization and extensibility.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union


class DateExtractor(ABC):
    """
    Abstract base class for date extraction from files.
    """
    
    @abstractmethod
    def extract_date(self, file_path: Path) -> Optional[datetime]:
        """
        Extract date from a file.
        
        Args:
            file_path (Path): Path to the file
            
        Returns:
            Optional[datetime]: Extracted date or None if not found
        """
        pass
    
    @abstractmethod
    def supports_file(self, file_path: Path) -> bool:
        """
        Check if this extractor supports the given file type.
        
        Args:
            file_path (Path): Path to check
            
        Returns:
            bool: True if file type is supported
        """
        pass
    
    @abstractmethod
    def get_priority(self) -> int:
        """
        Get the priority of this extractor (higher = more preferred).
        
        Returns:
            int: Priority value
        """
        pass


class FileProcessor(ABC):
    """
    Abstract base class for file processors.
    """
    
    @abstractmethod
    def can_process(self, file_path: Path) -> bool:
        """
        Check if this processor can handle the given file.
        
        Args:
            file_path (Path): Path to check
            
        Returns:
            bool: True if file can be processed
        """
        pass
    
    @abstractmethod
    def process_file(self, file_path: Path, target_dir: Path, **kwargs) -> bool:
        """
        Process a single file.
        
        Args:
            file_path (Path): Source file path
            target_dir (Path): Target directory
            **kwargs: Additional processing options
            
        Returns:
            bool: True if processing was successful
        """
        pass
    
    @abstractmethod
    def get_file_type(self) -> str:
        """
        Get the type of files this processor handles.
        
        Returns:
            str: File type identifier
        """
        pass


class StatisticsProvider(ABC):
    """
    Abstract base class for statistics providers.
    """
    
    @abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get current statistics.
        
        Returns:
            Dict[str, Any]: Statistics dictionary
        """
        pass
    
    @abstractmethod
    def reset_statistics(self):
        """Reset all statistics."""
        pass
    
    @abstractmethod
    def increment_counter(self, counter: str, amount: int = 1):
        """
        Increment a counter.
        
        Args:
            counter (str): Counter name
            amount (int): Amount to increment
        """
        pass


class ConfigValidator(ABC):
    """
    Abstract base class for configuration validators.
    """
    
    @abstractmethod
    def validate(self, config: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        """
        Validate configuration.
        
        Args:
            config (Dict[str, Any]): Configuration to validate
            
        Returns:
            Tuple[bool, List[str], List[str]]: (is_valid, errors, warnings)
        """
        pass
    
    @abstractmethod
    def apply_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply default values to configuration.
        
        Args:
            config (Dict[str, Any]): Configuration to update
            
        Returns:
            Dict[str, Any]: Configuration with defaults applied
        """
        pass


class FileGrouper(ABC):
    """
    Abstract base class for file grouping strategies.
    """
    
    @abstractmethod
    def group_files(self, files: List[Path]) -> Dict[Tuple, List[Path]]:
        """
        Group files by some criteria.
        
        Args:
            files (List[Path]): Files to group
            
        Returns:
            Dict[Tuple, List[Path]]: Grouped files
        """
        pass
    
    @abstractmethod
    def get_group_key(self, file_path: Path) -> Optional[Tuple]:
        """
        Get grouping key for a file.
        
        Args:
            file_path (Path): File to get key for
            
        Returns:
            Optional[Tuple]: Grouping key or None
        """
        pass


class BatchProcessor(ABC):
    """
    Abstract base class for batch processing operations.
    """
    
    @abstractmethod
    def add_operation(self, operation_type: str, source: Path, target: Path, **kwargs):
        """
        Add operation to batch.
        
        Args:
            operation_type (str): Type of operation
            source (Path): Source path
            target (Path): Target path
            **kwargs: Additional operation parameters
        """
        pass
    
    @abstractmethod
    def flush_batch(self) -> int:
        """
        Execute all pending operations.
        
        Returns:
            int: Number of operations executed
        """
        pass
    
    @abstractmethod
    def get_batch_size(self) -> int:
        """
        Get current batch size.
        
        Returns:
            int: Number of pending operations
        """
        pass


class MediaFileDiscoverer(ABC):
    """
    Abstract base class for media file discovery.
    """
    
    @abstractmethod
    def discover_files(self, directory: Path) -> List[Path]:
        """
        Discover files in directory.
        
        Args:
            directory (Path): Directory to scan
            
        Returns:
            List[Path]: Found files
        """
        pass
    
    @abstractmethod
    def get_supported_extensions(self) -> List[str]:
        """
        Get list of supported file extensions.
        
        Returns:
            List[str]: Supported extensions
        """
        pass
    
    @abstractmethod
    def is_excluded_directory(self, directory: Path) -> bool:
        """
        Check if directory should be excluded from scanning.
        
        Args:
            directory (Path): Directory to check
            
        Returns:
            bool: True if directory should be excluded
        """
        pass


class CacheProvider(ABC):
    """
    Abstract base class for caching providers.
    """
    
    @abstractmethod
    def get(self, key: str) -> Any:
        """
        Get value from cache.
        
        Args:
            key (str): Cache key
            
        Returns:
            Any: Cached value or None if not found
        """
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value in cache.
        
        Args:
            key (str): Cache key
            value (Any): Value to cache
            ttl (Optional[int]): Time to live in seconds
        """
        pass
    
    @abstractmethod
    def clear(self):
        """Clear all cached values."""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.
        
        Returns:
            Dict[str, int]: Cache statistics
        """
        pass


class ProgressReporter(ABC):
    """
    Abstract base class for progress reporting.
    """
    
    @abstractmethod
    def start(self, total: int, description: str = "Processing"):
        """
        Start progress tracking.
        
        Args:
            total (int): Total number of items to process
            description (str): Description of the operation
        """
        pass
    
    @abstractmethod
    def update(self, amount: int = 1):
        """
        Update progress.
        
        Args:
            amount (int): Amount to increment progress
        """
        pass
    
    @abstractmethod
    def finish(self):
        """Finish progress tracking."""
        pass
    
    @abstractmethod
    def set_description(self, description: str):
        """
        Set progress description.
        
        Args:
            description (str): New description
        """
        pass


class ErrorHandler(ABC):
    """
    Abstract base class for error handling strategies.
    """
    
    @abstractmethod
    def handle_error(self, error: Exception, context: Dict[str, Any]) -> bool:
        """
        Handle an error.
        
        Args:
            error (Exception): The error that occurred
            context (Dict[str, Any]): Context information
            
        Returns:
            bool: True if error was handled and processing should continue
        """
        pass
    
    @abstractmethod
    def should_retry(self, error: Exception, attempt: int) -> bool:
        """
        Check if operation should be retried.
        
        Args:
            error (Exception): The error that occurred
            attempt (int): Current attempt number
            
        Returns:
            bool: True if should retry
        """
        pass
    
    @abstractmethod
    def get_max_retries(self) -> int:
        """
        Get maximum number of retries.
        
        Returns:
            int: Maximum retry attempts
        """
        pass


class VideoThumbnailMerger(ABC):
    """
    Abstract base class for video thumbnail merging.
    """
    
    @abstractmethod
    def can_merge(self, video_path: Path, thumbnail_path: Path) -> bool:
        """
        Check if video and thumbnail can be merged.
        
        Args:
            video_path (Path): Video file path
            thumbnail_path (Path): Thumbnail file path
            
        Returns:
            bool: True if files can be merged
        """
        pass
    
    @abstractmethod
    def merge(self, video_path: Path, thumbnail_path: Path, output_path: Path) -> bool:
        """
        Merge video with thumbnail.
        
        Args:
            video_path (Path): Video file path
            thumbnail_path (Path): Thumbnail file path
            output_path (Path): Output file path
            
        Returns:
            bool: True if merge was successful
        """
        pass
    
    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """
        Get supported video formats.
        
        Returns:
            List[str]: Supported formats
        """
        pass


class OrganizationStrategy(ABC):
    """
    Abstract base class for file organization strategies.
    """
    
    @abstractmethod
    def organize(self, files: List[Path], target_directory: Path) -> Dict[str, Any]:
        """
        Organize files according to strategy.
        
        Args:
            files (List[Path]): Files to organize
            target_directory (Path): Target directory
            
        Returns:
            Dict[str, Any]: Organization results
        """
        pass
    
    @abstractmethod
    def get_target_path(self, file_path: Path, base_target: Path) -> Path:
        """
        Get target path for a file.
        
        Args:
            file_path (Path): Source file path
            base_target (Path): Base target directory
            
        Returns:
            Path: Target file path
        """
        pass
    
    @abstractmethod
    def supports_file_type(self, file_path: Path) -> bool:
        """
        Check if strategy supports file type.
        
        Args:
            file_path (Path): File to check
            
        Returns:
            bool: True if file type is supported
        """
        pass


# Factory pattern interfaces

class DateExtractorFactory:
    """Factory for creating date extractors."""
    
    _extractors: Dict[str, type] = {}
    
    @classmethod
    def register(cls, name: str, extractor_class: type):
        """Register a date extractor class."""
        cls._extractors[name] = extractor_class
    
    @classmethod
    def create(cls, name: str, **kwargs) -> DateExtractor:
        """Create a date extractor instance."""
        if name not in cls._extractors:
            raise ValueError(f"Unknown date extractor: {name}")
        return cls._extractors[name](**kwargs)
    
    @classmethod
    def get_available(cls) -> List[str]:
        """Get list of available extractors."""
        return list(cls._extractors.keys())


class FileProcessorFactory:
    """Factory for creating file processors."""
    
    _processors: Dict[str, type] = {}
    
    @classmethod
    def register(cls, name: str, processor_class: type):
        """Register a file processor class."""
        cls._processors[name] = processor_class
    
    @classmethod
    def create(cls, name: str, **kwargs) -> FileProcessor:
        """Create a file processor instance."""
        if name not in cls._processors:
            raise ValueError(f"Unknown file processor: {name}")
        return cls._processors[name](**kwargs)
    
    @classmethod
    def get_available(cls) -> List[str]:
        """Get list of available processors."""
        return list(cls._processors.keys())


# Utility mixins

class LoggerMixin:
    """Mixin to provide logging functionality."""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        if not hasattr(self, '_logger'):
            self._logger = logging.getLogger(self.__class__.__module__ + '.' + self.__class__.__name__)
        return self._logger


class ConfigurableMixin:
    """Mixin to provide configuration functionality."""
    
    def __init__(self, config: Dict[str, Any] = None, **kwargs):
        """Initialize with configuration."""
        super().__init__(**kwargs)
        self.config = config or {}
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value with optional default."""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set_config_value(self, key: str, value: Any):
        """Set configuration value."""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value


# Type aliases for better readability
FilePath = Union[str, Path]
DateInfo = Tuple[int, int, int]  # (year, month, day)
FileGroup = Dict[DateInfo, List[Path]]
ProcessingResult = Dict[str, Any]
ValidationResult = Tuple[bool, List[str], List[str]]  # (is_valid, errors, warnings)