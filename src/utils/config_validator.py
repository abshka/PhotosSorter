#!/usr/bin/env python3
"""
Configuration Validator Module

This module provides validation for PhotosSorter configuration files
to ensure all settings are valid and dependencies are available.
"""

import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

try:
    from .exceptions import ConfigurationError, ValidationError, DependencyError
except ImportError:
    from exceptions import ConfigurationError, ValidationError, DependencyError


class ConfigValidator:
    """
    Validates PhotosSorter configuration files and settings.
    """
    
    def __init__(self):
        """Initialize the configuration validator."""
        self.logger = logging.getLogger(__name__)
        self.errors = []
        self.warnings = []
        
        # Valid configuration schema
        self.schema = {
            'source_directory': {'type': str, 'required': True},
            'target_directory': {'type': (str, type(None)), 'required': False},
            'date_format': {'type': str, 'required': True, 'choices': [
                'YYYY/MM/DD', 'YYYY/MM', 'YYYY-MM-DD', 'YYYY-MM'
            ]},
            'supported_extensions': {'type': list, 'required': True},
            'processing': {'type': dict, 'required': False},
            'video': {'type': dict, 'required': False},
            'fallback': {'type': dict, 'required': False},
            'logging': {'type': dict, 'required': False},
            'performance': {'type': dict, 'required': False},
            'safety': {'type': dict, 'required': False}
        }
        
        # Processing section schema
        self.processing_schema = {
            'move_files': {'type': bool, 'default': True},
            'skip_organized': {'type': bool, 'default': True},
            'create_backup': {'type': bool, 'default': False},
            'duplicate_handling': {'type': str, 'choices': ['skip', 'rename', 'overwrite'], 'default': 'rename'}
        }
        
        # Video section schema
        self.video_schema = {
            'enabled': {'type': bool, 'default': True},
            'process_with_thumbnails': {'type': bool, 'default': True},
            'thumbnail_extensions': {'type': list, 'default': ['.thm']},
            'keep_thumbnails_together': {'type': bool, 'default': True},
            'extract_video_metadata': {'type': bool, 'default': False},
            'use_thumbnail_date': {'type': bool, 'default': True},
            'mpg_processing': {'type': dict, 'required': False}
        }
        
        # MPG processing schema
        self.mpg_processing_schema = {
            'enable_merging': {'type': bool, 'default': True},
            'delete_thm_after_merge': {'type': bool, 'default': True},
            'backup_original_mpg': {'type': bool, 'default': False},
            'merge_quality': {'type': str, 'choices': ['same', 'high', 'medium', 'low'], 'default': 'same'},
            'thumbnail_method': {'type': str, 'choices': ['embedded', 'first_frame', 'both'], 'default': 'embedded'},
            'require_ffmpeg': {'type': bool, 'default': True}
        }
        
        # Logging section schema
        self.logging_schema = {
            'level': {'type': str, 'choices': ['DEBUG', 'INFO', 'WARNING', 'ERROR'], 'default': 'INFO'},
            'file': {'type': str, 'default': 'logs/photos_sorter.log'},
            'max_size_mb': {'type': int, 'min': 1, 'max': 1000, 'default': 10},
            'backup_count': {'type': int, 'min': 0, 'max': 20, 'default': 5}
        }
        
        # Performance section schema
        self.performance_schema = {
            'batch_size': {'type': int, 'min': 1, 'max': 10000, 'default': 100},
            'show_progress': {'type': bool, 'default': True},
            'worker_threads': {'type': int, 'min': 1, 'max': 32, 'default': 4}
        }
        
        # Safety section schema
        self.safety_schema = {
            'dry_run': {'type': bool, 'default': False},
            'confirm_before_start': {'type': bool, 'default': True},
            'max_files_per_run': {'type': int, 'min': 0, 'default': 0}
        }
    
    def validate(self, config: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        """
        Validate a configuration dictionary.
        
        Args:
            config (Dict[str, Any]): Configuration to validate
            
        Returns:
            Tuple[bool, List[str], List[str]]: (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []
        
        try:
            # Validate main configuration
            self._validate_main_config(config)
            
            # Validate subsections
            if 'processing' in config:
                self._validate_section(config['processing'], self.processing_schema, 'processing')
            
            if 'video' in config:
                self._validate_video_config(config['video'])
            
            if 'logging' in config:
                self._validate_section(config['logging'], self.logging_schema, 'logging')
            
            if 'performance' in config:
                self._validate_section(config['performance'], self.performance_schema, 'performance')
            
            if 'safety' in config:
                self._validate_section(config['safety'], self.safety_schema, 'safety')
            
            # Validate dependencies
            self._validate_dependencies(config)
            
            # Validate paths and permissions
            self._validate_paths(config)
            
            # Validate file extensions
            self._validate_extensions(config)
            
            # Cross-validation
            self._cross_validate(config)
            
        except Exception as e:
            self.errors.append(f"Validation error: {str(e)}")
        
        is_valid = len(self.errors) == 0
        return is_valid, self.errors.copy(), self.warnings.copy()
    
    def _validate_main_config(self, config: Dict[str, Any]):
        """Validate main configuration structure."""
        for key, schema in self.schema.items():
            if schema.get('required', False) and key not in config:
                self.errors.append(f"Required configuration key '{key}' is missing")
                continue
            
            if key in config:
                value = config[key]
                expected_type = schema['type']
                
                if not isinstance(value, expected_type):
                    type_name = expected_type.__name__ if hasattr(expected_type, '__name__') else str(expected_type)
                    self.errors.append(f"Configuration '{key}' must be of type {type_name}, got {type(value).__name__}")
                
                if 'choices' in schema and value not in schema['choices']:
                    self.errors.append(f"Configuration '{key}' must be one of {schema['choices']}, got '{value}'")
    
    def _validate_section(self, section_config: Dict[str, Any], schema: Dict[str, Any], section_name: str):
        """Validate a configuration section."""
        for key, value in section_config.items():
            if key not in schema:
                self.warnings.append(f"Unknown configuration key '{section_name}.{key}'")
                continue
            
            key_schema = schema[key]
            expected_type = key_schema['type']
            
            if not isinstance(value, expected_type):
                type_name = expected_type.__name__ if hasattr(expected_type, '__name__') else str(expected_type)
                self.errors.append(f"Configuration '{section_name}.{key}' must be of type {type_name}, got {type(value).__name__}")
            
            if 'choices' in key_schema and value not in key_schema['choices']:
                self.errors.append(f"Configuration '{section_name}.{key}' must be one of {key_schema['choices']}, got '{value}'")
            
            if 'min' in key_schema and isinstance(value, (int, float)) and value < key_schema['min']:
                self.errors.append(f"Configuration '{section_name}.{key}' must be >= {key_schema['min']}, got {value}")
            
            if 'max' in key_schema and isinstance(value, (int, float)) and value > key_schema['max']:
                self.errors.append(f"Configuration '{section_name}.{key}' must be <= {key_schema['max']}, got {value}")
    
    def _validate_video_config(self, video_config: Dict[str, Any]):
        """Validate video configuration section."""
        self._validate_section(video_config, self.video_schema, 'video')
        
        if 'mpg_processing' in video_config:
            self._validate_section(video_config['mpg_processing'], self.mpg_processing_schema, 'video.mpg_processing')
    
    def _validate_dependencies(self, config: Dict[str, Any]):
        """Validate that required dependencies are available."""
        import importlib.util
        import subprocess
        
        # Check Python dependencies
        required_deps = {
            'PIL': 'pip install Pillow',
            'yaml': 'pip install PyYAML',
            'exifread': 'pip install exifread'
        }
        
        for dep, install_cmd in required_deps.items():
            if importlib.util.find_spec(dep) is None:
                self.errors.append(f"Required dependency '{dep}' not found. Install with: {install_cmd}")
        
        # Check optional dependencies
        optional_deps = {
            'tqdm': 'pip install tqdm'
        }
        
        for dep, install_cmd in optional_deps.items():
            if importlib.util.find_spec(dep) is None:
                self.warnings.append(f"Optional dependency '{dep}' not found. Install with: {install_cmd}")
        
        # Check system dependencies
        video_config = config.get('video', {})
        mpg_config = video_config.get('mpg_processing', {})
        
        if video_config.get('extract_video_metadata', False):
            if not self._check_system_command('ffprobe'):
                self.errors.append("ffprobe not found. Install ffmpeg to enable video metadata extraction.")
        
        if mpg_config.get('enable_merging', False) and mpg_config.get('require_ffmpeg', True):
            if not self._check_system_command('ffmpeg'):
                self.errors.append("ffmpeg not found. Install ffmpeg to enable MPG/THM merging.")
    
    def _check_system_command(self, command: str) -> bool:
        """Check if a system command is available."""
        import subprocess
        
        # First try to check if command exists using 'which' on Unix systems
        try:
            result = subprocess.run(['which', command], capture_output=True, timeout=5)
            if result.returncode == 0:
                return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # Try different version flags for different commands
        version_flags = ['--version', '-version', '-V']
        
        for flag in version_flags:
            try:
                subprocess.run([command, flag], capture_output=True, timeout=5)
                return True
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                continue
        
        return False
    
    def _validate_paths(self, config: Dict[str, Any]):
        """Validate path configurations."""
        source_dir = config.get('source_directory')
        if source_dir:
            source_path = Path(source_dir)
            if not source_path.exists():
                self.errors.append(f"Source directory does not exist: {source_dir}")
            elif not source_path.is_dir():
                self.errors.append(f"Source path is not a directory: {source_dir}")
            elif not os.access(source_path, os.R_OK):
                self.errors.append(f"Source directory is not readable: {source_dir}")
        
        target_dir = config.get('target_directory')
        if target_dir:
            target_path = Path(target_dir)
            if target_path.exists():
                if not target_path.is_dir():
                    self.errors.append(f"Target path exists but is not a directory: {target_dir}")
                elif not os.access(target_path, os.W_OK):
                    self.errors.append(f"Target directory is not writable: {target_dir}")
            else:
                # Check if parent directory is writable
                parent = target_path.parent
                if not parent.exists():
                    self.warnings.append(f"Target directory parent does not exist: {parent}")
                elif not os.access(parent, os.W_OK):
                    self.errors.append(f"Cannot create target directory, parent not writable: {parent}")
        
        # Validate log file path
        log_config = config.get('logging', {})
        log_file = log_config.get('file', 'logs/photos_sorter.log')
        log_path = Path(log_file)
        log_dir = log_path.parent
        
        if not log_dir.exists():
            try:
                log_dir.mkdir(parents=True, exist_ok=True)
            except OSError:
                self.warnings.append(f"Cannot create log directory: {log_dir}")
        elif not os.access(log_dir, os.W_OK):
            self.warnings.append(f"Log directory is not writable: {log_dir}")
    
    def _validate_extensions(self, config: Dict[str, Any]):
        """Validate file extension configurations."""
        extensions = config.get('supported_extensions', [])
        
        if not extensions:
            self.errors.append("No supported extensions configured")
            return
        
        valid_pattern = re.compile(r'^\.[a-zA-Z0-9]+$')
        
        for ext in extensions:
            if not isinstance(ext, str):
                self.errors.append(f"Extension must be string, got {type(ext).__name__}: {ext}")
                continue
            
            if not ext.startswith('.'):
                self.warnings.append(f"Extension should start with dot: {ext}")
            
            if not valid_pattern.match(ext):
                self.warnings.append(f"Extension has unusual format: {ext}")
        
        # Check for common image/video extensions
        image_exts = {'.jpg', '.jpeg', '.png', '.tiff', '.tif'}
        video_exts = {'.mp4', '.avi', '.mov', '.mpg', '.mpeg'}
        
        has_images = any(ext.lower() in image_exts for ext in extensions)
        has_videos = any(ext.lower() in video_exts for ext in extensions)
        
        if not has_images and not has_videos:
            self.warnings.append("No common image or video extensions found in configuration")
    
    def _cross_validate(self, config: Dict[str, Any]):
        """Perform cross-validation between different configuration sections."""
        # Check video processing dependencies
        video_config = config.get('video', {})
        if video_config.get('enabled', True):
            if video_config.get('extract_video_metadata', False):
                if not self._check_system_command('ffprobe'):
                    self.warnings.append("Video metadata extraction enabled but ffprobe not available")
            
            mpg_config = video_config.get('mpg_processing', {})
            if mpg_config.get('enable_merging', True):
                if not self._check_system_command('ffmpeg'):
                    self.warnings.append("MPG merging enabled but ffmpeg not available")
        
        # Check safety vs performance settings
        safety_config = config.get('safety', {})
        performance_config = config.get('performance', {})
        
        if safety_config.get('dry_run', False):
            self.warnings.append("Dry run mode is enabled - no actual file operations will be performed")
        
        batch_size = performance_config.get('batch_size', 100)
        max_files = safety_config.get('max_files_per_run', 0)
        
        if max_files > 0 and batch_size > max_files:
            self.warnings.append(f"Batch size ({batch_size}) larger than max files per run ({max_files})")
    
    def apply_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply default values to missing configuration options.
        
        Args:
            config (Dict[str, Any]): Configuration to update
            
        Returns:
            Dict[str, Any]: Configuration with defaults applied
        """
        result = config.copy()
        
        # Apply defaults for each section
        self._apply_section_defaults(result, 'processing', self.processing_schema)
        self._apply_section_defaults(result, 'video', self.video_schema)
        self._apply_section_defaults(result, 'logging', self.logging_schema)
        self._apply_section_defaults(result, 'performance', self.performance_schema)
        self._apply_section_defaults(result, 'safety', self.safety_schema)
        
        # Apply MPG processing defaults
        if 'video' in result and 'mpg_processing' in result['video']:
            self._apply_section_defaults(
                result['video'], 'mpg_processing', self.mpg_processing_schema
            )
        
        return result
    
    def _apply_section_defaults(self, config: Dict[str, Any], section_name: str, schema: Dict[str, Any]):
        """Apply default values to a configuration section."""
        if section_name not in config:
            config[section_name] = {}
        
        section = config[section_name]
        
        for key, key_schema in schema.items():
            if 'default' in key_schema and key not in section:
                section[key] = key_schema['default']


def main():
    """Test function for the configuration validator."""
    import yaml
    
    # Setup basic logging
    logging.basicConfig(level=logging.DEBUG)
    
    validator = ConfigValidator()
    
    # Test with sample configuration
    sample_config = {
        'source_directory': '/tmp/test_photos',
        'date_format': 'YYYY/MM/DD',
        'supported_extensions': ['.jpg', '.jpeg', '.png', '.mp4'],
        'processing': {
            'move_files': True,
            'duplicate_handling': 'rename'
        },
        'video': {
            'enabled': True,
            'extract_video_metadata': True
        }
    }
    
    is_valid, errors, warnings = validator.validate(sample_config)
    
    print("Configuration Validation Results:")
    print("=" * 40)
    print(f"Valid: {is_valid}")
    
    if errors:
        print(f"\nErrors ({len(errors)}):")
        for error in errors:
            print(f"  - {error}")
    
    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for warning in warnings:
            print(f"  - {warning}")
    
    # Test defaults application
    config_with_defaults = validator.apply_defaults(sample_config)
    print(f"\nConfiguration with defaults applied:")
    print(yaml.dump(config_with_defaults, indent=2))


if __name__ == "__main__":
    main()