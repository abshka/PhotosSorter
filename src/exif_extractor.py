#!/usr/bin/env python3
"""
EXIF Metadata Extractor Module

This module provides functionality to extract date and time information
from image files using EXIF metadata.
"""

import logging
from datetime import datetime
import importlib.util
from functools import lru_cache
from typing import Optional, Dict, Any
from pathlib import Path

# Check for optional dependencies
PILLOW_AVAILABLE = importlib.util.find_spec("PIL") is not None
EXIFREAD_AVAILABLE = importlib.util.find_spec("exifread") is not None

# Conditional imports with proper typing
if PILLOW_AVAILABLE:
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS
    except ImportError:
        Image = None
        TAGS = None
        PILLOW_AVAILABLE = False
        logging.warning("Pillow import failed. Some image formats may not be supported.")
else:
    Image = None
    TAGS = None
    logging.warning("Pillow not available. Some image formats may not be supported.")

if EXIFREAD_AVAILABLE:
    try:
        import exifread
    except ImportError:
        exifread = None
        EXIFREAD_AVAILABLE = False
        logging.warning("exifread import failed. RAW format support may be limited.")
else:
    exifread = None
    logging.warning("exifread not available. RAW format support may be limited.")


class ExifExtractor:
    """
    Extracts EXIF metadata from image files, specifically focusing on date/time information.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # EXIF tags that contain date/time information (in order of preference)
        self.datetime_tags = [
            'DateTime',           # Camera date/time
            'DateTimeOriginal',   # Original photo date/time
            'DateTimeDigitized',  # Digitization date/time
            'DateTime_Original',  # Alternative format
            'Date_Time_Original', # Alternative format
        ]

    def extract_date_from_file(self, file_path: str) -> Optional[datetime]:
        """
        Extract the creation date from an image file.
        
        Args:
            file_path (str): Path to the image file
            
        Returns:
            Optional[datetime]: The extracted date or None if not found
        """
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            self.logger.error(f"File does not exist: {file_path}")
            return None
        
        if not self._is_image_file(file_path_obj):
            self.logger.debug(f"Skipping non-image file: {file_path}")
            return None
        
        # Use cached extraction based on file path, size, and modification time
        return self._extract_date_cached(
            str(file_path_obj),
            file_path_obj.stat().st_size,
            file_path_obj.stat().st_mtime
        )
    
    @lru_cache(maxsize=1000)
    def _extract_date_cached(self, file_path: str, file_size: int, file_mtime: float) -> Optional[datetime]:
        """
        Cached version of date extraction based on file path, size, and modification time.
        
        Args:
            file_path (str): Path to the image file
            file_size (int): File size in bytes
            file_mtime (float): File modification time
            
        Returns:
            Optional[datetime]: The extracted date or None if not found
        """
        file_path_obj = Path(file_path)
        
        # Try Pillow first (most reliable for common formats)
        if PILLOW_AVAILABLE:
            date = self._extract_with_pillow(file_path_obj)
            if date:
                return date
        
        # Fallback to exifread for RAW and other formats
        if EXIFREAD_AVAILABLE:
            date = self._extract_with_exifread(file_path_obj)
            if date:
                return date
        
        # Last resort: use file modification time
        return self._get_file_modification_date(file_path_obj)

    def _extract_with_pillow(self, file_path: Path) -> Optional[datetime]:
        """
        Extract EXIF date using Pillow library.

        Args:
            file_path (Path): Path to the image file

        Returns:
            Optional[datetime]: Extracted date or None
        """
        try:
            if not PILLOW_AVAILABLE or Image is None or TAGS is None:
                return None
            with Image.open(file_path) as img:
                exif_data = getattr(img, '_getexif', lambda: None)()

                if not exif_data:
                    self.logger.debug(f"No EXIF data found in {file_path}")
                    return None

                # Convert EXIF data to readable format
                exif_dict = {TAGS.get(tag, tag): value for tag, value in exif_data.items()}

                # Try to find date/time in EXIF data
                for tag in self.datetime_tags:
                    if tag in exif_dict:
                        date_str = str(exif_dict[tag])
                        parsed_date = self._parse_exif_datetime(date_str)
                        if parsed_date:
                            self.logger.debug(f"Found {tag} in {file_path}: {parsed_date}")
                            return parsed_date

        except Exception as e:
            self.logger.debug(f"Pillow failed to read EXIF from {file_path}: {e}")

        return None

    def _extract_with_exifread(self, file_path: Path) -> Optional[datetime]:
        """
        Extract EXIF date using exifread library (better for RAW files).

        Args:
            file_path (Path): Path to the image file

        Returns:
            Optional[datetime]: Extracted date or None
        """
        try:
            if not EXIFREAD_AVAILABLE or exifread is None:
                return None
            with open(file_path, 'rb') as f:
                tags = exifread.process_file(f, details=False)

                # Try to find date/time in EXIF tags
                for tag_name in self.datetime_tags:
                    # Check both with and without 'EXIF' prefix
                    possible_keys = [
                        f'EXIF {tag_name}',
                        f'Image {tag_name}',
                        tag_name
                    ]

                    for key in possible_keys:
                        if key in tags:
                            date_str = str(tags[key])
                            parsed_date = self._parse_exif_datetime(date_str)
                            if parsed_date:
                                self.logger.debug(f"Found {key} in {file_path}: {parsed_date}")
                                return parsed_date

        except Exception as e:
            self.logger.debug(f"exifread failed to read EXIF from {file_path}: {e}")

        return None

    def _parse_exif_datetime(self, date_str: str) -> Optional[datetime]:
        """
        Parse EXIF datetime string to datetime object.

        Args:
            date_str (str): EXIF datetime string

        Returns:
            Optional[datetime]: Parsed datetime or None
        """
        if not date_str or date_str.strip() == "":
            return None

        # Common EXIF datetime formats
        formats = [
            '%Y:%m:%d %H:%M:%S',     # Most common: 2024:01:15 14:30:25
            '%Y-%m-%d %H:%M:%S',     # Alternative: 2024-01-15 14:30:25
            '%Y:%m:%d',              # Date only: 2024:01:15
            '%Y-%m-%d',              # Date only: 2024-01-15
            '%Y:%m:%d %H:%M',        # Without seconds: 2024:01:15 14:30
            '%Y-%m-%d %H:%M',        # Without seconds: 2024-01-15 14:30
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue

        self.logger.debug(f"Could not parse date string: {date_str}")
        return None

    def _get_file_modification_date(self, file_path: Path) -> Optional[datetime]:
        """
        Get file modification date as fallback.

        Args:
            file_path (Path): Path to the file

        Returns:
            Optional[datetime]: File modification date
        """
        try:
            mtime = file_path.stat().st_mtime
            return datetime.fromtimestamp(mtime)
        except Exception as e:
            self.logger.error(f"Could not get modification date for {file_path}: {e}")
            return None

    def _is_image_file(self, file_path: Path) -> bool:
        """
        Check if file is an image based on extension.

        Args:
            file_path (Path): Path to check

        Returns:
            bool: True if file appears to be an image
        """
        image_extensions = {
            '.jpg', '.jpeg', '.png', '.tiff', '.tif',
            '.raw', '.cr2', '.nef', '.arw', '.dng',
            '.bmp', '.gif', '.webp', '.heic', '.heif'
        }

        return file_path.suffix.lower() in image_extensions

    def get_exif_summary(self, file_path: str) -> Dict[str, Any]:
        """
        Get a summary of EXIF data for debugging purposes.
        
        Args:
            file_path (str): Path to the image file
            
        Returns:
            Dict[str, Any]: Summary of EXIF data
        """
        file_path_obj = Path(file_path)
        summary = {
            'file_path': str(file_path_obj),
            'file_exists': file_path_obj.exists(),
            'is_image': self._is_image_file(file_path_obj),
            'file_size': None,
            'modification_date': None,
            'exif_date': None,
            'exif_available': False,
            'datetime_tags_found': [],
            'cache_info': self._extract_date_cached.cache_info()._asdict()
        }
        
        if not file_path_obj.exists():
            return summary
        
        # File info
        try:
            summary['file_size'] = file_path_obj.stat().st_size
            summary['modification_date'] = self._get_file_modification_date(file_path_obj)
        except Exception as e:
            self.logger.error(f"Error getting file info: {e}")
        
        # EXIF info
        summary['exif_date'] = self.extract_date_from_file(str(file_path))
        
        # Check which EXIF tags are available
        if PILLOW_AVAILABLE and Image is not None and TAGS is not None:
            try:
                with Image.open(file_path_obj) as img:
                    exif_data = getattr(img, '_getexif', lambda: None)()
                    if exif_data:
                        summary['exif_available'] = True
                        exif_dict = {TAGS.get(tag, tag): value for tag, value in exif_data.items()}
                        summary['datetime_tags_found'] = [
                            tag for tag in self.datetime_tags if tag in exif_dict
                        ]
            except Exception:
                pass
        
        return summary
    
    def clear_cache(self):
        """Clear the EXIF extraction cache."""
        self._extract_date_cached.cache_clear()
        self.logger.debug("EXIF extraction cache cleared")


def main():
    """Test function for the EXIF extractor."""
    import sys

    if len(sys.argv) != 2:
        print("Usage: python exif_extractor.py <image_file>")
        sys.exit(1)

    # Setup basic logging
    logging.basicConfig(level=logging.DEBUG)

    extractor = ExifExtractor()
    file_path = sys.argv[1]

    print(f"Analyzing: {file_path}")
    print("-" * 50)

    # Get summary
    summary = extractor.get_exif_summary(file_path)
    for key, value in summary.items():
        print(f"{key}: {value}")

    print("-" * 50)

    # Extract date
    date = extractor.extract_date_from_file(file_path)
    if date:
        print(f"Extracted date: {date}")
        print(f"Formatted: {date.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("No date could be extracted from this file.")


if __name__ == "__main__":
    main()
