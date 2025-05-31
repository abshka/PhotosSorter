#!/usr/bin/env python3
"""
Video Processor Module

This module handles video files and their associated thumbnails/metadata files.
It can extract dates from video metadata and process video files together
with their thumbnail files (.thm, .jpg, etc.).
"""

import os
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Set
import json

try:
    from .exif_extractor import ExifExtractor
    from .mpg_thm_merger import MpgThmMerger
except ImportError:
    from exif_extractor import ExifExtractor
    from mpg_thm_merger import MpgThmMerger


class VideoProcessor:
    """
    Processes video files and their associated thumbnail/metadata files.
    """
    
    def __init__(self, config: Dict):
        """
        Initialize the video processor with configuration.
        
        Args:
            config (Dict): Configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.exif_extractor = ExifExtractor()
        self.mpg_merger = MpgThmMerger(config)
        
        # Video-related configuration
        self.video_config = config.get('video', {})
        self.enabled = self.video_config.get('enabled', True)
        self.process_with_thumbnails = self.video_config.get('process_with_thumbnails', True)
        self.thumbnail_extensions = set(
            ext.lower() for ext in self.video_config.get('thumbnail_extensions', ['.thm', '.jpg'])
        )
        self.keep_thumbnails_together = self.video_config.get('keep_thumbnails_together', True)
        self.extract_video_metadata = self.video_config.get('extract_video_metadata', False)
        self.use_thumbnail_date = self.video_config.get('use_thumbnail_date', True)
        
        # Video extensions
        self.video_extensions = {'.mpg', '.mpeg', '.mp4', '.avi', '.mov', '.mkv', '.wmv'}
        
        # Check for ffprobe availability
        self.ffprobe_available = self._check_ffprobe_available()
        if self.extract_video_metadata and not self.ffprobe_available:
            self.logger.warning("ffprobe not available. Video metadata extraction disabled.")
            self.extract_video_metadata = False
    
    def _check_ffprobe_available(self) -> bool:
        """
        Check if ffprobe is available on the system.
        
        Returns:
            bool: True if ffprobe is available
        """
        try:
            subprocess.run(['ffprobe', '-version'], 
                         capture_output=True, check=True, timeout=5)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def is_video_file(self, file_path: Path) -> bool:
        """
        Check if file is a video file.
        
        Args:
            file_path (Path): Path to check
            
        Returns:
            bool: True if file is a video
        """
        return file_path.suffix.lower() in self.video_extensions
    
    def is_thumbnail_file(self, file_path: Path) -> bool:
        """
        Check if file is a thumbnail file.
        
        Args:
            file_path (Path): Path to check
            
        Returns:
            bool: True if file is a thumbnail
        """
        return file_path.suffix.lower() in self.thumbnail_extensions
    
    def find_video_thumbnail_pairs(self, directory: Path) -> List[Tuple[Path, List[Path], str]]:
        """
        Find video files and their associated thumbnail files.
        
        Args:
            directory (Path): Directory to search
            
        Returns:
            List[Tuple[Path, List[Path], str]]: List of (video_file, [thumbnail_files], processing_type)
        """
        if not self.enabled:
            return []
        
        video_files = {}
        thumbnail_files = {}
        
        # Scan directory for video and thumbnail files
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = Path(root) / file
                file_stem = file_path.stem.lower()
                
                if self.is_video_file(file_path):
                    if file_stem not in video_files:
                        video_files[file_stem] = []
                    video_files[file_stem].append(file_path)
                
                elif self.is_thumbnail_file(file_path):
                    if file_stem not in thumbnail_files:
                        thumbnail_files[file_stem] = []
                    thumbnail_files[file_stem].append(file_path)
        
        # Match videos with their thumbnails
        pairs = []
        processed_thumbnails = set()
        
        for stem, videos in video_files.items():
            for video_file in videos:
                thumbnails = thumbnail_files.get(stem, [])
                
                # Filter out already processed thumbnails
                available_thumbnails = [
                    thumb for thumb in thumbnails 
                    if thumb not in processed_thumbnails
                ]
                
                # Determine processing type
                processing_type = "standard"
                if (video_file.suffix.lower() in ['.mpg', '.mpeg'] and 
                    any(thumb.suffix.lower() == '.thm' for thumb in available_thumbnails)):
                    processing_type = "mpg_merge"
                
                pairs.append((video_file, available_thumbnails, processing_type))
                processed_thumbnails.update(available_thumbnails)
        
        # Handle orphaned thumbnails (thumbnails without matching videos)
        for stem, thumbnails in thumbnail_files.items():
            if stem not in video_files:
                for thumbnail in thumbnails:
                    if thumbnail not in processed_thumbnails:
                        # Treat orphaned thumbnails as standalone files
                        pairs.append((thumbnail, [], "orphaned"))
        
        return pairs
    
    def extract_date_from_video(self, video_path: Path) -> Optional[datetime]:
        """
        Extract creation date from video file.
        
        Args:
            video_path (Path): Path to video file
            
        Returns:
            Optional[datetime]: Extracted date or None
        """
        # Try video metadata extraction first
        if self.extract_video_metadata and self.ffprobe_available:
            date = self._extract_date_with_ffprobe(video_path)
            if date:
                self.logger.debug(f"Extracted date from video metadata: {video_path}")
                return date
        
        # Fallback to file modification time
        try:
            mtime = video_path.stat().st_mtime
            return datetime.fromtimestamp(mtime)
        except Exception as e:
            self.logger.debug(f"Could not get file date for {video_path}: {e}")
            return None
    
    def _extract_date_with_ffprobe(self, video_path: Path) -> Optional[datetime]:
        """
        Extract date from video metadata using ffprobe.
        
        Args:
            video_path (Path): Path to video file
            
        Returns:
            Optional[datetime]: Extracted date or None
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(video_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                self.logger.debug(f"ffprobe failed for {video_path}: {result.stderr}")
                return None
            
            metadata = json.loads(result.stdout)
            
            # Try to find creation date in various metadata fields
            date_fields = [
                'creation_time',
                'date',
                'DATE',
                'com.apple.quicktime.creationdate',
                'creation_date'
            ]
            
            # Check format metadata
            format_tags = metadata.get('format', {}).get('tags', {})
            for field in date_fields:
                if field in format_tags:
                    date_str = format_tags[field]
                    parsed_date = self._parse_video_datetime(date_str)
                    if parsed_date:
                        return parsed_date
            
            # Check stream metadata
            for stream in metadata.get('streams', []):
                stream_tags = stream.get('tags', {})
                for field in date_fields:
                    if field in stream_tags:
                        date_str = stream_tags[field]
                        parsed_date = self._parse_video_datetime(date_str)
                        if parsed_date:
                            return parsed_date
            
        except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
            self.logger.debug(f"Error extracting video metadata from {video_path}: {e}")
        
        return None
    
    def _parse_video_datetime(self, date_str: str) -> Optional[datetime]:
        """
        Parse video metadata datetime string.
        
        Args:
            date_str (str): Date string from video metadata
            
        Returns:
            Optional[datetime]: Parsed datetime or None
        """
        if not date_str or date_str.strip() == "":
            return None
        
        # Common video metadata datetime formats
        formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',      # ISO format with microseconds
            '%Y-%m-%dT%H:%M:%SZ',         # ISO format
            '%Y-%m-%dT%H:%M:%S',          # ISO format without Z
            '%Y-%m-%d %H:%M:%S',          # Standard format
            '%Y:%m:%d %H:%M:%S',          # EXIF-like format
            '%Y-%m-%d',                   # Date only
            '%Y:%m:%d',                   # Date only EXIF-like
        ]
        
        date_str = date_str.strip()
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        self.logger.debug(f"Could not parse video date string: {date_str}")
        return None
    
    def extract_date_from_video_group(self, video_path: Path, thumbnail_paths: List[Path]) -> Optional[datetime]:
        """
        Extract date from video file or its thumbnails.
        
        Args:
            video_path (Path): Path to video file
            thumbnail_paths (List[Path]): List of thumbnail file paths
            
        Returns:
            Optional[datetime]: Best available date
        """
        # If it's actually a thumbnail file being processed as main file
        if self.is_thumbnail_file(video_path):
            date = self.exif_extractor.extract_date_from_file(str(video_path))
            if date:
                self.logger.debug(f"Extracted date from thumbnail EXIF: {video_path}")
                return date
            
            # Fallback to file date
            try:
                mtime = video_path.stat().st_mtime
                return datetime.fromtimestamp(mtime)
            except Exception as e:
                self.logger.debug(f"Could not get file date for {video_path}: {e}")
                return None
        
        # For video files, try video metadata first
        if self.is_video_file(video_path):
            video_date = self.extract_date_from_video(video_path)
            if video_date:
                return video_date
        
        # Try thumbnail EXIF data if enabled
        if self.use_thumbnail_date and thumbnail_paths:
            for thumbnail_path in thumbnail_paths:
                try:
                    thumbnail_date = self.exif_extractor.extract_date_from_file(str(thumbnail_path))
                    if thumbnail_date:
                        self.logger.debug(f"Extracted date from thumbnail EXIF: {thumbnail_path}")
                        return thumbnail_date
                except Exception as e:
                    self.logger.debug(f"Error reading thumbnail EXIF {thumbnail_path}: {e}")
        
        # Fallback to video file modification time
        try:
            mtime = video_path.stat().st_mtime
            return datetime.fromtimestamp(mtime)
        except Exception as e:
            self.logger.debug(f"Could not get file date for {video_path}: {e}")
            return None
    
    def get_video_file_info(self, video_path: Path, thumbnail_paths: List[Path] = None) -> Dict:
        """
        Get information about a video file and its thumbnails.
        
        Args:
            video_path (Path): Path to video file
            thumbnail_paths (List[Path]): Optional list of thumbnail paths
            
        Returns:
            Dict: Video file information
        """
        if thumbnail_paths is None:
            thumbnail_paths = []
        
        info = {
            'video_path': str(video_path),
            'is_video': self.is_video_file(video_path),
            'is_thumbnail': self.is_thumbnail_file(video_path),
            'thumbnail_paths': [str(p) for p in thumbnail_paths],
            'thumbnail_count': len(thumbnail_paths),
            'video_exists': video_path.exists(),
            'video_size': None,
            'total_size': 0,
            'extracted_date': None,
            'ffprobe_available': self.ffprobe_available,
            'video_metadata_available': False,
            'can_merge_mpg_thm': False,
            'mpg_merger_available': False
        }
        
        # Check MPG/THM merge capability
        if (self.is_video_file(video_path) and 
            video_path.suffix.lower() in ['.mpg', '.mpeg'] and
            thumbnail_paths):
            thm_files = [p for p in thumbnail_paths if p.suffix.lower() == '.thm']
            if thm_files:
                info['can_merge_mpg_thm'] = self.mpg_merger.can_merge_files(video_path, thm_files[0])
                info['mpg_merger_available'] = self.mpg_merger.ffmpeg_available
        
        # Get file sizes
        try:
            if video_path.exists():
                info['video_size'] = video_path.stat().st_size
                info['total_size'] += info['video_size']
        except Exception as e:
            self.logger.debug(f"Error getting video file size: {e}")
        
        for thumb_path in thumbnail_paths:
            try:
                if thumb_path.exists():
                    info['total_size'] += thumb_path.stat().st_size
            except Exception as e:
                self.logger.debug(f"Error getting thumbnail file size: {e}")
        
        # Extract date
        info['extracted_date'] = self.extract_date_from_video_group(video_path, thumbnail_paths)
        
        # Check if video metadata is available
        if self.is_video_file(video_path) and self.ffprobe_available:
            video_metadata_date = self._extract_date_with_ffprobe(video_path)
            info['video_metadata_available'] = video_metadata_date is not None
        
        return info


def main():
    """Test function for the video processor."""
    import sys
    import yaml
    
    if len(sys.argv) < 2:
        print("Usage: python video_processor.py <directory_or_video_file>")
        sys.exit(1)
    
    # Setup basic logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Load configuration
    try:
        config_path = Path(__file__).parent.parent / "config.yaml"
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        config = {'video': {'enabled': True}}
    
    processor = VideoProcessor(config)
    target_path = Path(sys.argv[1])
    
    if target_path.is_file():
        # Test single file
        print(f"Analyzing file: {target_path}")
        print("-" * 50)
        
        if processor.is_video_file(target_path):
            info = processor.get_video_file_info(target_path)
            for key, value in info.items():
                print(f"{key}: {value}")
        else:
            print("Not a video file")
    
    elif target_path.is_dir():
        # Test directory
        print(f"Scanning directory: {target_path}")
        print("-" * 50)
        
        pairs = processor.find_video_thumbnail_pairs(target_path)
        print(f"Found {len(pairs)} video/thumbnail groups:")
        
        for i, (video, thumbnails, processing_type) in enumerate(pairs, 1):
            print(f"\nGroup {i}:")
            print(f"  Video: {video}")
            if thumbnails:
                print(f"  Thumbnails: {', '.join(str(t) for t in thumbnails)}")
            else:
                print(f"  Thumbnails: None")
            print(f"  Processing type: {processing_type}")
            
            info = processor.get_video_file_info(video, thumbnails)
            print(f"  Date: {info['extracted_date']}")
            print(f"  Total size: {info['total_size']} bytes")
            if info.get('can_merge_mpg_thm'):
                print(f"  Can merge MPG/THM: Yes")
            if info.get('mpg_merger_available'):
                print(f"  ffmpeg available for merging: Yes")
    
    else:
        print(f"Path does not exist: {target_path}")


if __name__ == "__main__":
    main()