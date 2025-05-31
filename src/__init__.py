"""
PhotosSorter - A tool for organizing photos by date based on EXIF metadata.

This package provides modules for:
- Extracting EXIF metadata from image files
- Organizing photos into date-based directory structures
- Command-line interface for photo sorting operations

Main modules:
- exif_extractor: Extract date/time information from EXIF metadata
- file_organizer: Organize files into date-based directory structures
- photos_sorter: Main application with CLI interface
"""

__version__ = "1.0.0"
__author__ = "PhotosSorter Team"
__description__ = "Organize photos by date based on EXIF metadata"

try:
    from .exif_extractor import ExifExtractor
    from .file_organizer import FileOrganizer
    from .photos_sorter import PhotosSorter
    from .video_processor import VideoProcessor
    from .mpg_thm_merger import MpgThmMerger
except ImportError:
    from exif_extractor import ExifExtractor
    from file_organizer import FileOrganizer
    from photos_sorter import PhotosSorter
    from video_processor import VideoProcessor
    from mpg_thm_merger import MpgThmMerger

__all__ = [
    'ExifExtractor',
    'FileOrganizer', 
    'PhotosSorter',
    'VideoProcessor',
    'MpgThmMerger'
]