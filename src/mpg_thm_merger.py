#!/usr/bin/env python3
"""
MPG/THM Merger Module

This module handles merging MPG video files with their THM thumbnail files
to create a single video file with embedded thumbnail, then optionally
removes the original THM file.
"""

import logging
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from .exif_extractor import ExifExtractor
except ImportError:
    from exif_extractor import ExifExtractor


class MpgThmMerger:
    """
    Handles merging MPG video files with THM thumbnail files.
    """

    def __init__(self, config: Dict):
        """
        Initialize the MPG/THM merger with configuration.

        Args:
            config (Dict): Configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.exif_extractor = ExifExtractor()

        # MPG processing configuration
        self.mpg_config = config.get('video', {}).get('mpg_processing', {})
        self.enable_merging = self.mpg_config.get('enable_merging', True)
        self.delete_thm_after_merge = self.mpg_config.get('delete_thm_after_merge', True)
        self.backup_original_mpg = self.mpg_config.get('backup_original_mpg', False)
        self.merge_quality = self.mpg_config.get('merge_quality', 'same')
        self.thumbnail_method = self.mpg_config.get('thumbnail_method', 'embedded')
        self.require_ffmpeg = self.mpg_config.get('require_ffmpeg', True)

        # Statistics tracking
        self.stats = {
            'mpg_processed': 0,
            'thm_processed': 0,
            'merged_successfully': 0,
            'merge_errors': 0,
            'thm_deleted': 0,
            'backups_created': 0
        }

        # Check for ffmpeg availability
        self.ffmpeg_available = self._check_ffmpeg_available()
        if self.enable_merging and self.require_ffmpeg and not self.ffmpeg_available:
            self.logger.warning("ffmpeg not available. MPG/THM merging disabled.")
            self.enable_merging = False

    def _check_ffmpeg_available(self) -> bool:
        """
        Check if ffmpeg is available on the system.

        Returns:
            bool: True if ffmpeg is available
        """
        try:
            # Check if ffmpeg is available
            ffmpeg_version = subprocess.run(['ffmpeg', '-version'],
                                  capture_output=True, text=True, check=True, timeout=10)

            if ffmpeg_version.returncode != 0:
                self.logger.debug("ffmpeg check failed with non-zero return code")
                return False

            self.logger.debug(f"ffmpeg found: {ffmpeg_version.stdout.splitlines()[0]}")

            # Check for specific codecs
            codec_result = subprocess.run(['ffmpeg', '-codecs'],
                                        capture_output=True, text=True, timeout=10)

            if codec_result.returncode == 0:
                codec_output = codec_result.stdout
                has_h264 = 'h264' in codec_output and 'libx264' in codec_output
                has_mjpeg = 'mjpeg' in codec_output

                if not (has_h264 and has_mjpeg):
                    self.logger.warning(f"ffmpeg available but missing required codecs. h264: {has_h264}, mjpeg: {has_mjpeg}")
                    # Allow operation with warnings but don't disable completely
                    return True

                self.logger.debug("ffmpeg available with all required codecs")
                return True
            else:
                self.logger.warning("Could not check ffmpeg codecs, assuming basic support")
                return True

        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            self.logger.debug(f"ffmpeg not available: {e}")
            return False

    def can_merge_files(self, mpg_path: Path, thm_path: Path) -> bool:
        """
        Check if MPG and THM files can be merged.

        Args:
            mpg_path (Path): Path to MPG file
            thm_path (Path): Path to THM file

        Returns:
            bool: True if files can be merged
        """
        if not self.enable_merging:
            return False

        if not self.ffmpeg_available:
            self.logger.debug("Cannot merge: ffmpeg not available")
            return False

        if not mpg_path.exists():
            self.logger.debug(f"Cannot merge: MPG file does not exist: {mpg_path}")
            return False

        if not thm_path.exists():
            self.logger.debug(f"Cannot merge: THM file does not exist: {thm_path}")
            return False

        # Check file extensions
        if mpg_path.suffix.lower() not in ['.mpg', '.mpeg']:
            self.logger.debug(f"Cannot merge: Not an MPG file: {mpg_path}")
            return False

        if thm_path.suffix.lower() != '.thm':
            self.logger.debug(f"Cannot merge: Not a THM file: {thm_path}")
            return False

        # Check if files have matching base names
        if mpg_path.stem.lower() != thm_path.stem.lower():
            self.logger.debug(f"Cannot merge: File names don't match: {mpg_path.stem} vs {thm_path.stem}")
            return False

        return True

    def merge_mpg_with_thm(self, mpg_path: Path, thm_path: Path, output_dir: Path = None) -> Tuple[bool, Optional[Path]]:
        """
        Merge MPG video with THM thumbnail.

        Args:
            mpg_path (Path): Path to MPG file
            thm_path (Path): Path to THM file
            output_dir (Path): Output directory (default: same as input)

        Returns:
            Tuple[bool, Optional[Path]]: (success, output_file_path)
        """
        if not self.can_merge_files(mpg_path, thm_path):
            return False, None

        if output_dir is None:
            output_dir = mpg_path.parent

        # Check if this is a dry run
        if self.config.get('safety', {}).get('dry_run', False):
            self.logger.info(f"[DRY RUN] Would merge {mpg_path} with {thm_path}")
            return True, mpg_path  # Return original path for dry run

        self.logger.info(f"Merging {mpg_path} with {thm_path}")

        try:
            # Create backup if requested
            backup_path = None
            if self.backup_original_mpg:
                backup_path = self._create_backup(mpg_path)
                if backup_path:
                    self.stats['backups_created'] += 1

            # Create temporary output file
            temp_output = output_dir / f"{mpg_path.stem}_merged.mpg"

            # Perform the merge
            success = self._perform_merge(mpg_path, thm_path, temp_output)

            if success:
                # Replace original MPG with merged version
                final_output = output_dir / mpg_path.name
                if temp_output != final_output:
                    shutil.move(str(temp_output), str(final_output))

                # Preserve original file timestamps
                try:
                    original_stat = mpg_path.stat()
                    os.utime(str(final_output), (original_stat.st_atime, original_stat.st_mtime))
                    self.logger.debug(f"Preserved original timestamps for {final_output}")
                except Exception as e:
                    self.logger.warning(f"Could not preserve timestamps for {final_output}: {e}")

                # Delete original MPG file if we created the merged file in a different directory
                # and we're in move mode (not copy mode)
                move_files = self.config.get('processing', {}).get('move_files', True)
                if move_files and output_dir != mpg_path.parent:
                    try:
                        mpg_path.unlink()
                        self.stats['mpg_deleted'] = self.stats.get('mpg_deleted', 0) + 1
                        self.logger.debug(f"Deleted original MPG file: {mpg_path}")
                    except Exception as e:
                        self.logger.warning(f"Could not delete original MPG file {mpg_path}: {e}")

                # Delete THM file if requested
                if self.delete_thm_after_merge:
                    try:
                        thm_path.unlink()
                        self.stats['thm_deleted'] += 1
                        self.logger.debug(f"Deleted THM file: {thm_path}")
                    except Exception as e:
                        self.logger.warning(f"Could not delete THM file {thm_path}: {e}")

                self.stats['merged_successfully'] += 1
                self.logger.info(f"Successfully merged to: {final_output}")
                return True, final_output

            else:
                # Restore backup if merge failed
                if backup_path and backup_path.exists():
                    shutil.move(str(backup_path), str(mpg_path))
                    self.logger.info(f"Restored backup after failed merge: {mpg_path}")

                # Clean up temp file
                if temp_output.exists():
                    temp_output.unlink()

                self.stats['merge_errors'] += 1
                return False, None

        except Exception as e:
            self.logger.error(f"Error merging {mpg_path} with {thm_path}: {e}")
            self.stats['merge_errors'] += 1
            return False, None

    def _create_backup(self, mpg_path: Path) -> Optional[Path]:
        """
        Create a backup of the original MPG file.

        Args:
            mpg_path (Path): Path to MPG file

        Returns:
            Optional[Path]: Path to backup file or None if failed
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = mpg_path.parent / "backup"
            backup_dir.mkdir(exist_ok=True)

            backup_path = backup_dir / f"{mpg_path.stem}_backup_{timestamp}{mpg_path.suffix}"
            shutil.copy2(str(mpg_path), str(backup_path))

            self.logger.debug(f"Created backup: {backup_path}")
            return backup_path

        except Exception as e:
            self.logger.warning(f"Could not create backup for {mpg_path}: {e}")
            return None

    def _perform_merge(self, mpg_path: Path, thm_path: Path, output_path: Path) -> bool:
        """
        Perform the actual merge using ffmpeg.

        Args:
            mpg_path (Path): Path to MPG file
            thm_path (Path): Path to THM file
            output_path (Path): Path for output file

        Returns:
            bool: True if merge successful
        """
        try:
            if self.thumbnail_method == "embedded":
                return self._merge_with_embedded_thumbnail(mpg_path, thm_path, output_path)
            elif self.thumbnail_method == "first_frame":
                return self._merge_with_first_frame(mpg_path, thm_path, output_path)
            elif self.thumbnail_method == "both":
                # Try embedded first, then first frame if that fails
                if self._merge_with_embedded_thumbnail(mpg_path, thm_path, output_path):
                    return True
                return self._merge_with_first_frame(mpg_path, thm_path, output_path)
            else:
                self.logger.error(f"Unknown thumbnail method: {self.thumbnail_method}")
                return False

        except Exception as e:
            self.logger.error(f"Error performing merge: {e}")
            return False

    def _merge_with_embedded_thumbnail(self, mpg_path: Path, thm_path: Path, output_path: Path) -> bool:
        """
        Merge by embedding THM as video thumbnail metadata.

        Args:
            mpg_path (Path): Path to MPG file
            thm_path (Path): Path to THM file
            output_path (Path): Path for output file

        Returns:
            bool: True if successful
        """
        try:
            # Build ffmpeg command for embedded thumbnail
            cmd = [
                'ffmpeg',
                '-y',  # Overwrite output file
                '-i', str(mpg_path),     # Input video
                '-i', str(thm_path),     # Input thumbnail
                '-map', '0',             # Map all streams from first input (video)
                '-map', '1',             # Map thumbnail as additional stream
                '-c:v', 'copy',          # Copy video stream (no re-encoding)
                '-c:a', 'copy',          # Copy audio stream (no re-encoding)
                '-c:v:1', 'mjpeg',       # Encode thumbnail as MJPEG
                '-disposition:v:1', 'attached_pic',  # Mark as attached picture
                '-metadata:s:v:1', 'title=Thumbnail',
                '-metadata:s:v:1', 'comment=Generated by PhotosSorter',
                str(output_path)
            ]

            # Add quality settings if not "same"
            if self.merge_quality != "same":
                quality_settings = self._get_quality_settings()
                # Insert quality settings before output path
                cmd = cmd[:-1] + quality_settings + [str(output_path)]

            self.logger.debug(f"Running ffmpeg command: {' '.join(cmd)}")

            # Run ffmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0:
                self.logger.debug(f"ffmpeg completed successfully for {mpg_path}")
                return True
            else:
                self.logger.error(f"ffmpeg failed for {mpg_path}: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error(f"ffmpeg timeout for {mpg_path}")
            return False
        except Exception as e:
            self.logger.error(f"Error in embedded thumbnail merge: {e}")
            return False

    def _merge_with_first_frame(self, mpg_path: Path, thm_path: Path, output_path: Path) -> bool:
        """
        Merge by replacing first frame with thumbnail.

        Args:
            mpg_path (Path): Path to MPG file
            thm_path (Path): Path to THM file
            output_path (Path): Path for output file

        Returns:
            bool: True if successful
        """
        try:
            # This is more complex - we need to replace the first frame
            # For now, we'll use a simpler approach: overlay the thumbnail
            cmd = [
                'ffmpeg',
                '-y',  # Overwrite output file
                '-i', str(mpg_path),     # Input video
                '-i', str(thm_path),     # Input thumbnail
                '-filter_complex',
                '[1:v]scale=iw*0.2:ih*0.2[thumb];[0:v][thumb]overlay=W-w-10:10:enable=\'between(t,0,3)\'',
                '-c:a', 'copy',          # Copy audio
                str(output_path)
            ]

            # Add quality settings
            if self.merge_quality != "same":
                quality_settings = self._get_quality_settings()
                cmd = cmd[:-1] + quality_settings + [str(output_path)]

            self.logger.debug(f"Running ffmpeg overlay command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                self.logger.debug(f"ffmpeg overlay completed successfully for {mpg_path}")
                return True
            else:
                self.logger.error(f"ffmpeg overlay failed for {mpg_path}: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"Error in first frame merge: {e}")
            return False

    def _get_quality_settings(self) -> List[str]:
        """
        Get ffmpeg quality settings based on configuration.

        Returns:
            List[str]: List of ffmpeg arguments for quality
        """
        if self.merge_quality == "high":
            return ['-crf', '18', '-preset', 'slow']
        elif self.merge_quality == "medium":
            return ['-crf', '23', '-preset', 'medium']
        elif self.merge_quality == "low":
            return ['-crf', '28', '-preset', 'fast']
        else:  # "same"
            return ['-c:v', 'copy']

    def process_mpg_thm_pair(self, mpg_path: Path, thm_path: Path, target_dir: Path) -> Tuple[bool, Optional[Path]]:
        """
        Process an MPG/THM pair: merge if enabled, otherwise just organize.

        Args:
            mpg_path (Path): Path to MPG file
            thm_path (Path): Path to THM file
            target_dir (Path): Target directory for organized files

        Returns:
            Tuple[bool, Optional[Path]]: (success, final_mpg_path)
        """
        self.stats['mpg_processed'] += 1
        self.stats['thm_processed'] += 1

        if self.enable_merging and self.can_merge_files(mpg_path, thm_path):
            # Merge the files
            success, merged_path = self.merge_mpg_with_thm(mpg_path, thm_path, target_dir)
            if success:
                return True, merged_path
            else:
                # Fall back to separate file handling
                self.logger.warning(f"Merge failed for {mpg_path}, processing separately")

        # Process files separately (no merging)
        try:
            # Copy/move MPG file
            target_mpg = target_dir / mpg_path.name
            if self.config.get('processing', {}).get('move_files', False):
                shutil.move(str(mpg_path), str(target_mpg))
            else:
                shutil.copy2(str(mpg_path), str(target_mpg))

            # Copy/move THM file (keep it separate)
            target_thm = target_dir / thm_path.name
            if self.config.get('processing', {}).get('move_files', False):
                shutil.move(str(thm_path), str(target_thm))
            else:
                shutil.copy2(str(thm_path), str(target_thm))

            return True, target_mpg

        except Exception as e:
            self.logger.error(f"Error processing MPG/THM pair: {e}")
            return False, None

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
            'mpg_processed': 0,
            'thm_processed': 0,
            'merged_successfully': 0,
            'merge_errors': 0,
            'thm_deleted': 0,
            'backups_created': 0
        }


def main():
    """Test function for the MPG/THM merger."""
    import sys

    import yaml

    if len(sys.argv) < 3:
        print("Usage: python mpg_thm_merger.py <mpg_file> <thm_file>")
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
        config = {
            'video': {
                'mpg_processing': {
                    'enable_merging': True,
                    'delete_thm_after_merge': False,  # Safe for testing
                    'backup_original_mpg': True
                }
            },
            'safety': {'dry_run': False}
        }

    merger = MpgThmMerger(config)
    mpg_path = Path(sys.argv[1])
    thm_path = Path(sys.argv[2])

    print("Testing MPG/THM merger:")
    print(f"MPG file: {mpg_path}")
    print(f"THM file: {thm_path}")
    print(f"ffmpeg available: {merger.ffmpeg_available}")
    print(f"Can merge: {merger.can_merge_files(mpg_path, thm_path)}")
    print("-" * 50)

    if merger.can_merge_files(mpg_path, thm_path):
        success, output_path = merger.merge_mpg_with_thm(mpg_path, thm_path)
        print(f"Merge result: {'Success' if success else 'Failed'}")
        if output_path:
            print(f"Output file: {output_path}")

        stats = merger.get_statistics()
        print("\nStatistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    else:
        print("Cannot merge these files")


if __name__ == "__main__":
    main()
