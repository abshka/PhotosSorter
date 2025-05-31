#!/usr/bin/env python3
"""
File Organizer Module

This module handles the organization of photos into directory structures
based on date information extracted from EXIF metadata.
"""

import os
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from collections import defaultdict

try:
    from .exif_extractor import ExifExtractor
    from .video_processor import VideoProcessor
    from .mpg_thm_merger import MpgThmMerger
except ImportError:
    from exif_extractor import ExifExtractor
    from video_processor import VideoProcessor
    from mpg_thm_merger import MpgThmMerger


class FileOrganizer:
    """
    Organizes photo files into date-based directory structures.
    """
    
    def __init__(self, config: Dict):
        """
        Initialize the file organizer with configuration.
        
        Args:
            config (Dict): Configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.exif_extractor = ExifExtractor()
        self.video_processor = VideoProcessor(config)
        self.mpg_merger = MpgThmMerger(config)
        
        # Statistics tracking
        self.stats = {
            'processed': 0,
            'moved': 0,
            'copied': 0,
            'skipped': 0,
            'errors': 0,
            'no_date': 0,
            'videos_processed': 0,
            'thumbnails_processed': 0,
            'mpg_merged': 0,
            'thm_deleted': 0
        }
    
    def organize_photos(self, source_dir: str, target_dir: Optional[str] = None) -> Dict:
        """
        Main method to organize photos from source directory.
        
        Args:
            source_dir (str): Source directory containing photos
            target_dir (Optional[str]): Target directory for organized photos
            
        Returns:
            Dict: Statistics about the organization process
        """
        source_path = Path(source_dir)
        if not source_path.exists():
            raise ValueError(f"Source directory does not exist: {source_dir}")
        
        if target_dir:
            target_path = Path(target_dir)
            target_path.mkdir(parents=True, exist_ok=True)
        else:
            target_path = source_path
        
        self.logger.info(f"Starting photo organization from {source_path} to {target_path}")
        
        # Find all media files (images and videos)
        image_files = self._find_image_files(source_path)
        video_groups = self._find_video_groups(source_path)
        
        total_files = len(image_files) + len(video_groups)
        self.logger.info(f"Found {len(image_files)} image files and {len(video_groups)} video groups to process")
        
        if self.config.get('safety', {}).get('max_files_per_run', 0) > 0:
            max_files = self.config['safety']['max_files_per_run']
            if total_files > max_files:
                self.logger.warning(f"Limiting processing to {max_files} files")
                # Limit both images and video groups proportionally
                image_limit = int(max_files * len(image_files) / total_files) if total_files > 0 else 0
                video_limit = max_files - image_limit
                image_files = image_files[:image_limit]
                video_groups = video_groups[:video_limit]
        
        # Group files by date for batch processing
        date_groups = self._group_files_by_date(image_files)
        video_date_groups = self._group_video_files_by_date(video_groups)
        
        # Merge video groups into date groups
        for date_info, video_files in video_date_groups.items():
            if date_info in date_groups:
                date_groups[date_info].extend(video_files)
            else:
                date_groups[date_info] = video_files
        
        # Process each date group
        for date_info, files in date_groups.items():
            self._process_date_group(files, date_info, target_path)
        
        self.logger.info(f"Organization complete. Stats: {self.stats}")
        return self.stats
    
    def _find_image_files(self, directory: Path) -> List[Path]:
        """
        Recursively find all image files in directory.
        
        Args:
            directory (Path): Directory to search
            
        Returns:
            List[Path]: List of image file paths
        """
        supported_extensions = [
            ext.lower() for ext in self.config.get('supported_extensions', [])
        ]
        
        # Filter out video and thumbnail extensions for image-only processing
        video_extensions = {'.mpg', '.mpeg', '.mp4', '.avi', '.mov', '.mkv', '.wmv'}
        thumbnail_extensions = set(
            ext.lower() for ext in self.config.get('video', {}).get('thumbnail_extensions', ['.thm'])
        )
        
        image_extensions = set(supported_extensions) - video_extensions - thumbnail_extensions
        
        image_files = []
        
        for root, dirs, files in os.walk(directory):
            # Skip already organized directories if configured
            if self.config.get('processing', {}).get('skip_organized', True):
                if self._is_organized_directory(Path(root)):
                    self.logger.debug(f"Skipping organized directory: {root}")
                    continue
            
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix.lower() in image_extensions:
                    image_files.append(file_path)
        
        return sorted(image_files)
    
    def _is_organized_directory(self, directory: Path) -> bool:
        """
        Check if directory appears to be already organized by date.
        
        Args:
            directory (Path): Directory to check
            
        Returns:
            bool: True if directory appears organized
        """
        # Check if directory name matches date patterns
        dir_name = directory.name
        
        # Common organized patterns
        patterns = [
            r'^\d{4}$',           # 2024
            r'^\d{4}-\d{2}$',     # 2024-01
            r'^\d{4}-\d{2}-\d{2}$',  # 2024-01-15
            r'^\d{2}$'            # 01 (month)
        ]
        
        import re
        for pattern in patterns:
            if re.match(pattern, dir_name):
                return True
        
        return False
    
    def _group_files_by_date(self, files: List[Path]) -> Dict[Tuple, List[Path]]:
        """
        Group files by their extracted dates.
        
        Args:
            files (List[Path]): List of image files
            
        Returns:
            Dict[Tuple, List[Path]]: Files grouped by (year, month, day) tuple
        """
        date_groups = defaultdict(list)
        
        for file_path in files:
            self.stats['processed'] += 1
            
            try:
                # Extract date from file
                extracted_date = self.exif_extractor.extract_date_from_file(str(file_path))
                
                if extracted_date:
                    date_key = (extracted_date.year, extracted_date.month, extracted_date.day)
                    date_groups[date_key].append(file_path)
                else:
                    # Handle files without date
                    self.stats['no_date'] += 1
                    fallback_date = self._get_fallback_date(file_path)
                    if fallback_date:
                        date_key = (fallback_date.year, fallback_date.month, fallback_date.day)
                        date_groups[date_key].append(file_path)
                    else:
                        # Group files without any date
                        date_groups[('no_date',)].append(file_path)
                
            except Exception as e:
                self.logger.error(f"Error processing {file_path}: {e}")
                self.stats['errors'] += 1
        
        return dict(date_groups)
    
    def _find_video_groups(self, directory: Path) -> List[Tuple[Path, List[Path]]]:
        """
        Find video files and their associated thumbnails.
        
        Args:
            directory (Path): Directory to search
            
        Returns:
            List[Tuple[Path, List[Path]]]: List of (video_file, [thumbnail_files])
        """
        if not self.video_processor.enabled:
            return []
        
        return self.video_processor.find_video_thumbnail_pairs(directory)
    
    def _group_video_files_by_date(self, video_groups: List[Tuple[Path, List[Path], str]]) -> Dict[Tuple, List[Tuple[Path, List[Path], str]]]:
        """
        Group video files and their thumbnails by date.
        
        Args:
            video_groups (List[Tuple[Path, List[Path]]]): Video groups to process
            
        Returns:
            Dict[Tuple, List[Tuple[Path, List[Path]]]]: Video groups grouped by date
        """
        date_groups = defaultdict(list)
        
        for video_file, thumbnail_files, processing_type in video_groups:
            self.stats['processed'] += 1
            
            try:
                # Extract date from video or thumbnails
                extracted_date = self.video_processor.extract_date_from_video_group(video_file, thumbnail_files)
                
                if extracted_date:
                    date_key = (extracted_date.year, extracted_date.month, extracted_date.day)
                    date_groups[date_key].append((video_file, thumbnail_files, processing_type))
                    if self.video_processor.is_video_file(video_file):
                        self.stats['videos_processed'] += 1
                    self.stats['thumbnails_processed'] += len(thumbnail_files)
                else:
                    # Handle files without date
                    self.stats['no_date'] += 1
                    fallback_date = self._get_fallback_date(video_file)
                    if fallback_date:
                        date_key = (fallback_date.year, fallback_date.month, fallback_date.day)
                        date_groups[date_key].append((video_file, thumbnail_files, processing_type))
                    else:
                        # Group files without any date
                        date_groups[('no_date',)].append((video_file, thumbnail_files, processing_type))
                
            except Exception as e:
                self.logger.error(f"Error processing video group {video_file}: {e}")
                self.stats['errors'] += 1
        
        return dict(date_groups)
    
    def _get_fallback_date(self, file_path: Path) -> Optional[datetime]:
        """
        Get fallback date for files without EXIF date.
        
        Args:
            file_path (Path): Path to the file
            
        Returns:
            Optional[datetime]: Fallback date or None
        """
        if self.config.get('fallback', {}).get('use_file_date', True):
            try:
                mtime = file_path.stat().st_mtime
                return datetime.fromtimestamp(mtime)
            except Exception as e:
                self.logger.debug(f"Could not get file date for {file_path}: {e}")
        
        return None
    
    def _process_date_group(self, files: List[Path], date_info: Tuple, target_base: Path):
        """
        Process a group of files with the same date.
        
        Args:
            files (List[Path]): Files to process
            date_info (Tuple): Date information tuple
            target_base (Path): Base target directory
        """
        if date_info == ('no_date',):
            # Handle files without date
            target_dir = target_base / self.config.get('fallback', {}).get('no_date_folder', 'Unknown_Date')
        else:
            # Create date-based directory structure
            year, month, day = date_info
            target_dir = self._create_date_directory(target_base, year, month, day)
        
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Process each file in the group
        for item in files:
            try:
                if isinstance(item, tuple):
                    # This is a video group (video_file, thumbnail_files, processing_type)
                    if len(item) == 3:
                        video_file, thumbnail_files, processing_type = item
                        self._move_or_copy_video_group(video_file, thumbnail_files, target_dir, processing_type)
                    else:
                        # Legacy format for backward compatibility
                        video_file, thumbnail_files = item
                        self._move_or_copy_video_group(video_file, thumbnail_files, target_dir, "standard")
                else:
                    # This is a regular image file
                    self._move_or_copy_file(item, target_dir)
            except Exception as e:
                self.logger.error(f"Error moving/copying {item}: {e}")
                self.stats['errors'] += 1
    
    def _create_date_directory(self, base_dir: Path, year: int, month: int, day: int) -> Path:
        """
        Create directory path based on date format configuration.
        
        Args:
            base_dir (Path): Base directory
            year (int): Year
            month (int): Month
            day (int): Day
            
        Returns:
            Path: Target directory path
        """
        date_format = self.config.get('date_format', 'YYYY/MM')
        
        if date_format == 'YYYY/MM/DD':
            return base_dir / f"{year:04d}" / f"{month:02d}" / f"{day:02d}"
        elif date_format == 'YYYY/MM':
            return base_dir / f"{year:04d}" / f"{month:02d}"
        elif date_format == 'YYYY-MM-DD':
            return base_dir / f"{year:04d}-{month:02d}-{day:02d}"
        elif date_format == 'YYYY-MM':
            return base_dir / f"{year:04d}-{month:02d}"
        else:
            # Default to YYYY/MM
            return base_dir / f"{year:04d}" / f"{month:02d}"
    
    def _move_or_copy_file(self, source_file: Path, target_dir: Path):
        """
        Move or copy file to target directory.
        
        Args:
            source_file (Path): Source file path
            target_dir (Path): Target directory
        """
        target_file = target_dir / source_file.name
        
        # Handle duplicate filenames
        if target_file.exists():
            target_file = self._handle_duplicate(source_file, target_file)
            if not target_file:  # Skip if duplicate handling says so
                self.stats['skipped'] += 1
                return
        
        # Check if we're in dry run mode
        if self.config.get('safety', {}).get('dry_run', False):
            action = "move" if self.config.get('processing', {}).get('move_files', False) else "copy"
            self.logger.info(f"[DRY RUN] Would {action} {source_file} -> {target_file}")
            return
        
        # Create backup if configured
        if self.config.get('processing', {}).get('create_backup', False):
            self._create_backup(source_file)
        
        # Move or copy the file
        try:
            if self.config.get('processing', {}).get('move_files', False):
                shutil.move(str(source_file), str(target_file))
                self.stats['moved'] += 1
                self.logger.debug(f"Moved {source_file} -> {target_file}")
            else:
                shutil.copy2(str(source_file), str(target_file))
                self.stats['copied'] += 1
                self.logger.debug(f"Copied {source_file} -> {target_file}")
                
        except Exception as e:
            self.logger.error(f"Failed to move/copy {source_file}: {e}")
            self.stats['errors'] += 1
            raise
    
    def _move_or_copy_video_group(self, video_file: Path, thumbnail_files: List[Path], target_dir: Path, processing_type: str = "standard"):
        """
        Move or copy video file and its thumbnails to target directory.
        
        Args:
            video_file (Path): Video file path
            thumbnail_files (List[Path]): List of thumbnail file paths
            target_dir (Path): Target directory
            processing_type (str): Type of processing ("standard", "mpg_merge", "orphaned")
        """
        if processing_type == "mpg_merge" and thumbnail_files:
            # Handle MPG/THM merging
            thm_files = [f for f in thumbnail_files if f.suffix.lower() == '.thm']
            if thm_files and self.mpg_merger.can_merge_files(video_file, thm_files[0]):
                try:
                    success, merged_path = self.mpg_merger.process_mpg_thm_pair(video_file, thm_files[0], target_dir)
                    if success:
                        self.stats['mpg_merged'] += 1
                        # Update merger stats
                        merger_stats = self.mpg_merger.get_statistics()
                        if 'thm_deleted' in merger_stats:
                            self.stats['thm_deleted'] += merger_stats['thm_deleted'] - self.stats.get('prev_thm_deleted', 0)
                            self.stats['prev_thm_deleted'] = merger_stats['thm_deleted']
                        
                        # Process any remaining thumbnails
                        remaining_thumbnails = [f for f in thumbnail_files if f not in thm_files]
                        for thumbnail_file in remaining_thumbnails:
                            try:
                                self._move_or_copy_file(thumbnail_file, target_dir)
                            except Exception as e:
                                self.logger.error(f"Failed to move/copy remaining thumbnail {thumbnail_file}: {e}")
                                self.stats['errors'] += 1
                        return
                    else:
                        self.logger.warning(f"MPG merge failed for {video_file}, falling back to standard processing")
                except Exception as e:
                    self.logger.error(f"Error in MPG merge for {video_file}: {e}")
                    self.stats['errors'] += 1
        
        # Standard processing (no merging) or fallback
        self._move_or_copy_file(video_file, target_dir)
        
        # Process associated thumbnails if keeping them together
        if self.video_processor.keep_thumbnails_together:
            for thumbnail_file in thumbnail_files:
                try:
                    self._move_or_copy_file(thumbnail_file, target_dir)
                except Exception as e:
                    self.logger.error(f"Failed to move/copy thumbnail {thumbnail_file}: {e}")
                    self.stats['errors'] += 1
    
    def _handle_duplicate(self, source_file: Path, target_file: Path) -> Optional[Path]:
        """
        Handle duplicate filenames according to configuration.
        
        Args:
            source_file (Path): Source file
            target_file (Path): Target file that already exists
            
        Returns:
            Optional[Path]: New target path or None to skip
        """
        duplicate_handling = self.config.get('processing', {}).get('duplicate_handling', 'rename')
        
        if duplicate_handling == 'skip':
            self.logger.info(f"Skipping duplicate: {source_file}")
            return None
        
        elif duplicate_handling == 'overwrite':
            self.logger.warning(f"Overwriting: {target_file}")
            return target_file
        
        elif duplicate_handling == 'rename':
            # Find a unique filename
            counter = 1
            base_name = target_file.stem
            extension = target_file.suffix
            parent = target_file.parent
            
            while True:
                new_name = f"{base_name}_{counter:03d}{extension}"
                new_target = parent / new_name
                if not new_target.exists():
                    self.logger.info(f"Renaming duplicate: {target_file} -> {new_target}")
                    return new_target
                counter += 1
                
                if counter > 999:  # Safety limit
                    self.logger.error(f"Too many duplicates for {source_file}")
                    return None
        
        return target_file
    
    def _create_backup(self, file_path: Path):
        """
        Create a backup of the file before moving/copying.
        
        Args:
            file_path (Path): File to backup
        """
        backup_dir = file_path.parent / "backup"
        backup_dir.mkdir(exist_ok=True)
        
        backup_file = backup_dir / file_path.name
        counter = 1
        
        while backup_file.exists():
            stem = file_path.stem
            suffix = file_path.suffix
            backup_file = backup_dir / f"{stem}_backup_{counter:03d}{suffix}"
            counter += 1
        
        try:
            shutil.copy2(str(file_path), str(backup_file))
            self.logger.debug(f"Created backup: {backup_file}")
        except Exception as e:
            self.logger.warning(f"Failed to create backup for {file_path}: {e}")
    
    def get_statistics(self) -> Dict:
        """
        Get current processing statistics.
        
        Returns:
            Dict: Statistics dictionary
        """
        return self.stats.copy()
    
    def reset_statistics(self):
        """Reset processing statistics."""
        self.stats = {
            'processed': 0,
            'moved': 0,
            'copied': 0,
            'skipped': 0,
            'errors': 0,
            'no_date': 0,
            'videos_processed': 0,
            'thumbnails_processed': 0,
            'mpg_merged': 0,
            'thm_deleted': 0
        }


def main():
    """Test function for the file organizer."""
    import yaml
    
    # Load configuration
    config_path = Path(__file__).parent.parent / "config.yaml"
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, config.get('logging', {}).get('level', 'INFO')),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create organizer
    organizer = FileOrganizer(config)
    
    # Test with dry run
    config['safety']['dry_run'] = True
    
    try:
        stats = organizer.organize_photos(
            config['source_directory'],
            config.get('target_directory')
        )
        print(f"Organization test completed: {stats}")
    except Exception as e:
        print(f"Error during organization: {e}")


if __name__ == "__main__":
    main()