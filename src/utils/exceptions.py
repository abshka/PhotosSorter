#!/usr/bin/env python3
"""
Custom Exceptions Module

This module defines custom exceptions for the PhotosSorter application
to provide better error handling and more specific error information.
"""


class PhotoSorterError(Exception):
    """Base exception class for all PhotosSorter errors."""
    
    def __init__(self, message: str, file_path: str = None, details: dict = None):
        """
        Initialize PhotoSorterError.
        
        Args:
            message (str): Error message
            file_path (str): Path to file that caused the error (optional)
            details (dict): Additional error details (optional)
        """
        super().__init__(message)
        self.message = message
        self.file_path = file_path
        self.details = details if details is not None else {}
    
    def __str__(self):
        """Return formatted error message."""
        base_msg = self.message
        if self.file_path:
            base_msg = f"{base_msg} (file: {self.file_path})"
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            base_msg = f"{base_msg} [{details_str}]"
        return base_msg


class ConfigurationError(PhotoSorterError):
    """Raised when there are configuration-related errors."""
    pass


class PhotoSorterFileNotFoundError(PhotoSorterError):
    """Raised when a required file is not found."""
    pass


class DirectoryNotFoundError(PhotoSorterError):
    """Raised when a required directory is not found."""
    pass


class PhotoSorterPermissionError(PhotoSorterError):
    """Raised when there are file/directory permission issues."""
    pass


class ExifError(PhotoSorterError):
    """Raised when EXIF data extraction fails."""
    pass


class VideoProcessingError(PhotoSorterError):
    """Raised when video processing operations fail."""
    pass


class MergeError(PhotoSorterError):
    """Raised when MPG/THM merging fails."""
    pass


class DependencyError(PhotoSorterError):
    """Raised when required dependencies are missing."""
    
    def __init__(self, dependency_name: str, suggested_install: str = None):
        """
        Initialize DependencyError.
        
        Args:
            dependency_name (str): Name of missing dependency
            suggested_install (str): Suggested installation command
        """
        message = f"Required dependency '{dependency_name}' is not available"
        if suggested_install:
            message = f"{message}. Install with: {suggested_install}"
        
        super().__init__(message, details={'dependency': dependency_name})
        self.dependency_name = dependency_name
        self.suggested_install = suggested_install


class ValidationError(PhotoSorterError):
    """Raised when data validation fails."""
    pass


class BatchOperationError(PhotoSorterError):
    """Raised when batch operations fail."""
    
    def __init__(self, message: str, failed_operations: list = None):
        """
        Initialize BatchOperationError.
        
        Args:
            message (str): Error message
            failed_operations (list): List of failed operations
        """
        super().__init__(message)
        self.failed_operations = failed_operations if failed_operations is not None else []


class DuplicateFileError(PhotoSorterError):
    """Raised when duplicate files are encountered and handling fails."""
    pass


class DateExtractionError(ExifError):
    """Raised when date extraction from metadata fails."""
    pass


class FFmpegError(VideoProcessingError):
    """Raised when FFmpeg operations fail."""
    
    def __init__(self, message: str, command: list = None, stderr: str = None):
        """
        Initialize FFmpegError.
        
        Args:
            message (str): Error message
            command (list): FFmpeg command that failed
            stderr (str): FFmpeg stderr output
        """
        details = {}
        if command is not None:
            details['command'] = ' '.join(command)
        if stderr is not None:
            details['stderr'] = stderr
            
        super().__init__(message, details=details)
        self.command = command
        self.stderr = stderr


class CacheError(PhotoSorterError):
    """Raised when cache operations fail."""
    pass


class StatisticsError(PhotoSorterError):
    """Raised when statistics operations fail."""
    pass


def handle_exception(func):
    """
    Decorator to handle exceptions and convert them to PhotoSorterError.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except PhotoSorterError:
            # Re-raise PhotoSorterError as-is
            raise
        except FileNotFoundError as e:
            raise PhotoSorterFileNotFoundError(str(e), details={'original_error': type(e).__name__})
        except PermissionError as e:
            raise PhotoSorterPermissionError(str(e), details={'original_error': type(e).__name__})
        except Exception as e:
            raise PhotoSorterError(
                f"Unexpected error in {func.__name__}: {str(e)}",
                details={'original_error': type(e).__name__, 'function': func.__name__}
            )
    return wrapper


def format_error_report(error: PhotoSorterError) -> str:
    """
    Format a comprehensive error report.
    
    Args:
        error (PhotoSorterError): Error to format
        
    Returns:
        str: Formatted error report
    """
    lines = [
        "=" * 60,
        "PHOTOS SORTER ERROR REPORT",
        "=" * 60,
        f"Error Type: {type(error).__name__}",
        f"Message: {error.message}",
    ]
    
    if error.file_path:
        lines.append(f"File: {error.file_path}")
    
    if error.details:
        lines.append("Details:")
        for key, value in error.details.items():
            lines.append(f"  {key}: {value}")
    
    lines.append("=" * 60)
    
    return "\n".join(lines)


# Exception hierarchy for easy catching
RECOVERABLE_ERRORS = (
    DuplicateFileError,
    DateExtractionError,
    CacheError
)

CONFIGURATION_ERRORS = (
    ConfigurationError,
    ValidationError,
    DependencyError
)

FILE_SYSTEM_ERRORS = (
    PhotoSorterFileNotFoundError,
    DirectoryNotFoundError,
    PhotoSorterPermissionError
)

PROCESSING_ERRORS = (
    ExifError,
    VideoProcessingError,
    MergeError,
    FFmpegError,
    BatchOperationError
)

ALL_PHOTO_SORTER_ERRORS = (
    PhotoSorterError,
    ConfigurationError,
    PhotoSorterFileNotFoundError,
    DirectoryNotFoundError,
    PhotoSorterPermissionError,
    ExifError,
    VideoProcessingError,
    MergeError,
    DependencyError,
    ValidationError,
    BatchOperationError,
    DuplicateFileError,
    DateExtractionError,
    FFmpegError,
    CacheError,
    StatisticsError
)