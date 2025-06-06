#!/usr/bin/env python3
"""
Photos Sorter - Main Application Script

This is the main entry point for the Photos Sorter application.
It provides a command-line interface for organizing photos by date
based on EXIF metadata.

Refactored to use dependency injection and SOLID principles.
"""

import argparse
import importlib.util
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Optional, Any

import yaml

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from .utils.dependency_injection import DIContainer, get_container, DefaultServiceProvider
    from .utils.interfaces import ConfigurableMixin, LoggerMixin
    from .utils.exceptions import ConfigurationError, PhotoSorterError
    from .utils.config_validator import ConfigValidator
except ImportError:
    from utils.dependency_injection import DIContainer, get_container, DefaultServiceProvider
    from utils.interfaces import ConfigurableMixin, LoggerMixin
    from utils.exceptions import ConfigurationError, PhotoSorterError
    from utils.config_validator import ConfigValidator

TQDM_AVAILABLE = importlib.util.find_spec("tqdm") is not None


class PhotosSorter(ConfigurableMixin, LoggerMixin):
    """
    Main application class for sorting photos by date.
    
    Refactored to use dependency injection and follow SOLID principles:
    - Single Responsibility: Handles application orchestration only
    - Dependency Inversion: Uses injected dependencies instead of creating them
    - Open/Closed: Extensible through dependency injection
    """

    def __init__(self, config_path: Optional[str] = None, container: Optional[DIContainer] = None):
        """
        Initialize the Photos Sorter application.

        Args:
            config_path (Optional[str]): Path to configuration file
            container (Optional[DIContainer]): Dependency injection container
        """
        if container is None:
            # Force fresh container creation to avoid cached function issues
            try:
                from .utils.dependency_injection import DIContainer, DefaultServiceProvider
            except ImportError:
                from utils.dependency_injection import DIContainer, DefaultServiceProvider
            self.container = DIContainer()
            provider = DefaultServiceProvider()
            provider.configure_services(self.container)
        else:
            self.container = container
            
        self.config = self._load_and_validate_config(config_path)
        self._setup_logging()
        
        # Initialize with dependency injection
        super().__init__(config=self.config)

    def _load_and_validate_config(self, config_path: Optional[str] = None) -> Dict:
        """
        Load and validate configuration from YAML file.

        Args:
            config_path (Optional[str]): Path to config file

        Returns:
            Dict: Validated configuration dictionary
            
        Raises:
            ConfigurationError: If config file not found or invalid
        """
        if config_path is None:
            config_path_obj = Path(__file__).parent.parent / "config.yaml"
        else:
            config_path_obj = Path(config_path)

        if not config_path_obj.exists():
            raise ConfigurationError(f"Configuration file not found: {config_path_obj}")

        try:
            with open(config_path_obj, 'r', encoding='utf-8') as f:
                raw_config = yaml.safe_load(f)
            
            # Validate and apply defaults
            try:
                from .utils.config_validator import ConfigValidator
            except ImportError:
                from utils.config_validator import ConfigValidator
            config_validator = ConfigValidator()
            is_valid, errors, warnings = config_validator.validate(raw_config)
            
            if not is_valid:
                raise ConfigurationError(f"Invalid configuration: {', '.join(errors)}")
            
            if warnings:
                self.logger.warning(f"Configuration warnings: {', '.join(warnings)}")
            
            config = config_validator.apply_defaults(raw_config)
            return config
            
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Error parsing YAML configuration: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error loading configuration: {e}")

    def _setup_logging(self):
        """Setup logging configuration."""
        log_config = self.config.get('logging', {})

        # Create logs directory if it doesn't exist
        log_file = log_config.get('file', 'logs/photos_sorter.log')
        log_path = Path(__file__).parent.parent / log_file
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Configure logging
        log_level = getattr(logging, log_config.get('level', 'INFO').upper())

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # Setup file handler with rotation
        try:
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=log_config.get('max_size_mb', 10) * 1024 * 1024,
                backupCount=log_config.get('backup_count', 5)
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(log_level)
        except Exception:
            # Fallback to regular file handler
            file_handler = logging.FileHandler(log_path)
            file_handler.setFormatter(formatter)
            file_handler.setLevel(log_level)

        # Setup console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

    def run(self, source_dir: Optional[str] = None, target_dir: Optional[str] = None,
            dry_run: Optional[bool] = None, interactive: bool = True) -> Dict:
        """
        Run the photo organization process.

        Args:
            source_dir (Optional[str]): Override source directory
            target_dir (Optional[str]): Override target directory
            dry_run (Optional[bool]): Override dry run setting
            interactive (bool): Whether to ask for confirmation

        Returns:
            Dict: Processing statistics
        """
        try:
            # Use provided parameters or config defaults
            source = source_dir or self.config.get('source_directory')
            target = target_dir or self.config.get('target_directory')

            if dry_run is not None:
                self.config.setdefault('safety', {})['dry_run'] = dry_run

            # Validate source directory
            if not source:
                raise ConfigurationError("Source directory not specified")

            source_path = Path(source)
            if not source_path.exists():
                raise ConfigurationError(f"Source directory does not exist: {source}")

            self.logger.info("Photos Sorter starting...")
            self.logger.info(f"Source: {source}")
            self.logger.info(f"Target: {target or 'Same as source'}")
            self.logger.info(f"Dry run: {self.config.get('safety', {}).get('dry_run', False)}")

            # Ask for confirmation if interactive mode
            if interactive and self.config.get('safety', {}).get('confirm_before_start', True):
                if not self._get_user_confirmation():
                    self.logger.info("Operation cancelled by user")
                    return {'cancelled': True}

            # Get file organizer with injected dependencies
            organizer = self.container.resolve('file_organizer', config=self.config)
            
            # Run the organization
            stats = organizer.organize_photos(source, target)
            self._print_summary(stats)
            return stats
            
        except PhotoSorterError:
            # Re-raise PhotoSorter errors as-is
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during organization: {e}")
            raise PhotoSorterError(f"Organization failed: {e}")

    def _get_user_confirmation(self) -> bool:
        """
        Get user confirmation before starting the process.

        Returns:
            bool: True if user confirms, False otherwise
        """
        print("\n" + "="*60)
        print("PHOTOS SORTER - CONFIRMATION")
        print("="*60)
        print(f"Source directory: {self.config.get('source_directory')}")
        print(f"Target directory: {self.config.get('target_directory') or 'Same as source'}")
        print(f"Date format: {self.config.get('date_format', 'YYYY/MM')}")
        print(f"Operation: {'Move' if self.config.get('processing', {}).get('move_files', False) else 'Copy'}")
        print(f"Dry run: {self.config.get('safety', {}).get('dry_run', False)}")
        print("="*60)

        while True:
            response = input("\nProceed with photo organization? (y/n): ").lower().strip()
            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no']:
                return False
            else:
                print("Please enter 'y' for yes or 'n' for no.")

    def _print_summary(self, stats: Dict):
        """
        Print a summary of the organization process.

        Args:
            stats (Dict): Processing statistics
        """
        print("\n" + "="*60)
        print("PHOTOS SORTER - SUMMARY")
        print("="*60)
        print(f"Files processed: {stats.get('processed', 0)}")
        print(f"Files moved: {stats.get('moved', 0)}")
        print(f"Files copied: {stats.get('copied', 0)}")
        print(f"Files skipped: {stats.get('skipped', 0)}")
        print(f"Videos processed: {stats.get('videos_processed', 0)}")
        print(f"Thumbnails processed: {stats.get('thumbnails_processed', 0)}")
        print(f"MPG files merged: {stats.get('mpg_merged', 0)}")
        print(f"THM files deleted: {stats.get('thm_deleted', 0)}")
        print(f"Files without date: {stats.get('no_date', 0)}")
        print(f"Errors: {stats.get('errors', 0)}")
        print("="*60)

        if stats.get('errors', 0) > 0:
            print(f"\n⚠️  {stats['errors']} errors occurred. Check the log file for details.")

        if self.config.get('safety', {}).get('dry_run', False):
            print("\n✅ Dry run completed successfully!")
            print("   To actually move/copy files, set dry_run: false in config.yaml")
        else:
            print("\n✅ Organization completed successfully!")

    def scan_directory(self, directory: str) -> Dict:
        """
        Scan directory and return information about found images.

        Args:
            directory (str): Directory to scan

        Returns:
            Dict: Scan results
        """
        self.logger.info(f"Scanning directory: {directory}")

        directory_path = Path(directory)
        if not directory_path.exists():
            raise ConfigurationError(f"Directory does not exist: {directory}")

        try:
            # Get supported extensions from config
            extensions = set(ext.lower() for ext in self.config.get('supported_extensions', []))
            video_extensions = {'.mpg', '.mpeg', '.mp4', '.avi', '.mov', '.mkv', '.wmv'}
            image_extensions = extensions - video_extensions - {'.thm'}
            
            # Scan directory recursively
            total_files = 0
            total_images = 0
            total_videos = 0
            total_thumbnails = 0
            total_size = 0
            by_extension = {}
            video_groups = []
            mpg_mergeable = 0
            
            for file_path in directory_path.rglob('*'):
                if file_path.is_file():
                    ext = file_path.suffix.lower()
                    if ext in extensions:
                        total_files += 1
                        size = file_path.stat().st_size
                        total_size += size
                        
                        # Update by extension stats
                        if ext not in by_extension:
                            by_extension[ext] = {'count': 0, 'size': 0}
                        by_extension[ext]['count'] += 1
                        by_extension[ext]['size'] += size
                        
                        # Categorize files
                        if ext in image_extensions:
                            total_images += 1
                        elif ext in video_extensions:
                            total_videos += 1
                            # Check for MPG files that could be merged
                            if ext in {'.mpg', '.mpeg'}:
                                thm_path = file_path.with_suffix('.THM')
                                if thm_path.exists():
                                    mpg_mergeable += 1
                                    video_groups.append({
                                        'video': str(file_path),
                                        'thumbnail_count': 1,
                                        'processing_type': 'mpg_merge'
                                    })
                        elif ext == '.thm':
                            total_thumbnails += 1
            
            return {
                'total_files': total_files,
                'total_images': total_images,
                'total_videos': total_videos,
                'total_thumbnails': total_thumbnails,
                'total_size_mb': total_size / (1024 * 1024),
                'by_extension': by_extension,
                'video_groups': len(video_groups),
                'video_thumbnail_groups': video_groups,
                'mpg_mergeable': mpg_mergeable
            }
            
        except Exception as e:
            self.logger.error(f"Error scanning directory: {e}")
            raise PhotoSorterError(f"Directory scan failed: {e}")

    def test_exif_extraction(self, file_path: str) -> Dict:
        """
        Test EXIF extraction on a single file.

        Args:
            file_path (str): Path to image file

        Returns:
            Dict: EXIF extraction results
        """
        try:
            # Create exif extractor directly for testing
            try:
                from .exif_extractor import ExifExtractor
            except ImportError:
                from exif_extractor import ExifExtractor
            
            exif_extractor = ExifExtractor()
            return exif_extractor.get_exif_summary(file_path)
        except Exception as e:
            self.logger.error(f"Error testing EXIF extraction: {e}")
            raise PhotoSorterError(f"EXIF test failed: {e}")


def create_cli_parser() -> argparse.ArgumentParser:
    """
    Create command-line interface parser.

    Returns:
        argparse.ArgumentParser: Configured argument parser
    """
    parser = argparse.ArgumentParser(
        description="Organize photos by date based on EXIF metadata",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Use default config
  %(prog)s --source /path/to/photos           # Override source directory
  %(prog)s --dry-run                          # Preview what would be done
  %(prog)s --scan /path/to/photos             # Just scan directory
  %(prog)s --test-exif photo.jpg              # Test EXIF extraction
  %(prog)s --test-exif video.mpg              # Test video metadata extraction
        """
    )

    parser.add_argument(
        '--config', '-c',
        help='Path to configuration file (default: config.yaml)'
    )

    parser.add_argument(
        '--source', '-s',
        help='Source directory containing photos'
    )

    parser.add_argument(
        '--target', '-t',
        help='Target directory for organized photos'
    )

    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Preview actions without making changes'
    )

    parser.add_argument(
        '--no-confirm',
        action='store_true',
        help='Skip confirmation prompt'
    )

    parser.add_argument(
        '--scan',
        help='Scan directory and show statistics'
    )

    parser.add_argument(
        '--test-exif',
        help='Test EXIF/metadata extraction on a single file'
    )

    parser.add_argument(
        '--version', '-v',
        action='version',
        version='Photos Sorter 1.0.0'
    )

    return parser


def main():
    """Main entry point for the application."""
    parser = create_cli_parser()
    args = parser.parse_args()

    try:
        # Initialize the sorter
        sorter = PhotosSorter(args.config)

        # Handle different modes
        if args.scan:
            # Scan mode
            print(f"Scanning directory: {args.scan}")
            results = sorter.scan_directory(args.scan)

            print(f"\nFound {results['total_files']} total files:")
            print(f"  Images: {results['total_images']}")
            print(f"  Videos: {results['total_videos']}")
            print(f"  Thumbnails: {results['total_thumbnails']}")
            print(f"  Video groups: {results['video_groups']}")
            print(f"  MPG files ready for merging: {results['mpg_mergeable']}")
            print(f"Total size: {results['total_size_mb']:.2f} MB")
            print("\nBy extension:")
            for ext, info in results['by_extension'].items():
                print(f"  {ext}: {info['count']} files ({info['size'] / (1024*1024):.2f} MB)")

            if results['video_groups'] > 0:
                print(f"\nVideo/Thumbnail pairs:")
                for i, group in enumerate(results['video_thumbnail_groups'][:5], 1):  # Show first 5
                    processing_note = ""
                    if group.get('processing_type') == 'mpg_merge':
                        processing_note = " [MPG+THM merge]"
                    elif group.get('processing_type') == 'orphaned':
                        processing_note = " [orphaned]"
                    print(f"  {i}. {Path(group['video']).name} + {group['thumbnail_count']} thumbnail(s){processing_note}")
                if len(results['video_thumbnail_groups']) > 5:
                    print(f"  ... and {len(results['video_thumbnail_groups']) - 5} more groups")

        elif args.test_exif:
            # EXIF test mode
            test_path = Path(args.test_exif)
            print(f"Testing metadata extraction: {test_path}")

            # Create video processor and mpg merger for testing
            try:
                from .video_processor import VideoProcessor
                from .mpg_thm_merger import MpgThmMerger
            except ImportError:
                from video_processor import VideoProcessor
                from mpg_thm_merger import MpgThmMerger
            
            video_processor = VideoProcessor(sorter.config)
            mpg_merger = MpgThmMerger(sorter.config)
            
            if video_processor.is_video_file(test_path) or video_processor.is_thumbnail_file(test_path):
                # Test video processing
                print("File type: Video/Thumbnail")
                video_info = video_processor.get_video_file_info(test_path)
                for key, value in video_info.items():
                    print(f"{key}: {value}")

                # Test MPG merging capability if applicable
                if (test_path.suffix.lower() in ['.mpg', '.mpeg'] and
                    mpg_merger.ffmpeg_available):
                    thm_path = test_path.with_suffix('.THM')
                    if thm_path.exists():
                        can_merge = mpg_merger.can_merge_files(test_path, thm_path)
                        print(f"can_merge_with_thm: {can_merge}")
                        print(f"thm_file_found: {thm_path}")
            else:
                # Test EXIF extraction
                print("File type: Image")
                results = sorter.test_exif_extraction(args.test_exif)
                for key, value in results.items():
                    print(f"{key}: {value}")

        else:
            # Normal organization mode
            # Auto-skip confirmation for dry-run mode
            interactive = not args.no_confirm and not args.dry_run
            stats = sorter.run(
                source_dir=args.source,
                target_dir=args.target,
                dry_run=args.dry_run,
                interactive=interactive
            )

            # Exit with error code if there were errors
            if stats.get('errors', 0) > 0:
                sys.exit(1)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
