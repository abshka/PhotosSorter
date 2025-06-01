#!/usr/bin/env python3
"""
Test Suite for Dependency Injection Container and Refactored Components

This module contains comprehensive tests for the PhotosSorter application
after refactoring to use dependency injection and SOLID principles.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.dependency_injection import DIContainer, DefaultServiceProvider, get_container, reset_container
from utils.interfaces import DateExtractor, FileProcessor, StatisticsProvider
from utils.exceptions import ConfigurationError, PhotoSorterError
from utils.statistics import StatisticsCollector
from photos_sorter import PhotosSorter


class TestDIContainer(unittest.TestCase):
    """Test cases for the Dependency Injection Container."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.container = DIContainer()
    
    def test_register_singleton(self):
        """Test singleton registration and resolution."""
        class TestService:
            def __init__(self):
                self.value = "test"
        
        self.container.register_singleton('test_service', TestService)
        
        # Should return same instance
        instance1 = self.container.resolve('test_service')
        instance2 = self.container.resolve('test_service')
        
        self.assertIs(instance1, instance2)
        self.assertEqual(instance1.value, "test")
    
    def test_register_transient(self):
        """Test transient registration and resolution."""
        class TestService:
            def __init__(self):
                self.value = "test"
        
        self.container.register_transient('test_service', TestService)
        
        # Should return different instances
        instance1 = self.container.resolve('test_service')
        instance2 = self.container.resolve('test_service')
        
        self.assertIsNot(instance1, instance2)
        self.assertEqual(instance1.value, "test")
        self.assertEqual(instance2.value, "test")
    
    def test_register_factory(self):
        """Test factory registration and resolution."""
        def test_factory(container):
            return {"created_by": "factory"}
        
        self.container.register_factory('test_service', test_factory)
        
        instance = self.container.resolve('test_service')
        self.assertEqual(instance["created_by"], "factory")
    
    def test_register_instance(self):
        """Test instance registration and resolution."""
        test_instance = {"value": "test_instance"}
        
        self.container.register_instance('test_service', test_instance)
        
        resolved = self.container.resolve('test_service')
        self.assertIs(resolved, test_instance)
    
    def test_dependency_injection(self):
        """Test automatic dependency injection."""
        class Dependency:
            def __init__(self):
                self.name = "dependency"
        
        class Service:
            def __init__(self, dependency: Dependency):
                self.dependency = dependency
        
        self.container.register_singleton(Dependency, Dependency)
        self.container.register_transient(Service, Service)
        
        service = self.container.resolve(Service)
        self.assertIsInstance(service.dependency, Dependency)
        self.assertEqual(service.dependency.name, "dependency")
    
    def test_circular_dependency_detection(self):
        """Test circular dependency detection."""
        class ServiceA:
            def __init__(self, service_b):
                self.service_b = service_b
        
        class ServiceB:
            def __init__(self, service_a):
                self.service_a = service_a
        
        # Register with string keys to avoid type resolution
        self.container.register_transient('service_a', 
            lambda c: ServiceA(c.resolve('service_b')))
        self.container.register_transient('service_b', 
            lambda c: ServiceB(c.resolve('service_a')))
        
        with self.assertRaises(ValueError) as context:
            self.container.resolve('service_a')
        
        self.assertIn("Circular dependency", str(context.exception))
    
    def test_service_not_registered(self):
        """Test error when resolving unregistered service."""
        with self.assertRaises(ValueError) as context:
            self.container.resolve('nonexistent_service')
        
        self.assertIn("Service not registered", str(context.exception))
    
    def test_scoped_lifetime(self):
        """Test scoped service lifetime."""
        class TestService:
            def __init__(self):
                self.value = "scoped"
        
        self.container.register_scoped('test_service', TestService)
        
        # Should return same instance within scope
        instance1 = self.container.resolve('test_service')
        instance2 = self.container.resolve('test_service')
        self.assertIs(instance1, instance2)
        
        # Should return new instance after clearing scope
        self.container.clear_scope()
        instance3 = self.container.resolve('test_service')
        self.assertIsNot(instance1, instance3)
    
    def test_is_registered(self):
        """Test service registration checking."""
        self.assertFalse(self.container.is_registered('test_service'))
        
        self.container.register_singleton('test_service', lambda c: "test")
        self.assertTrue(self.container.is_registered('test_service'))
    
    def test_get_registered_services(self):
        """Test getting all registered services."""
        self.container.register_singleton('service1', lambda c: "test1")
        self.container.register_transient('service2', lambda c: "test2")
        
        services = self.container.get_registered_services()
        
        self.assertEqual(services['service1'], 'singleton')
        self.assertEqual(services['service2'], 'transient')


class TestDefaultServiceProvider(unittest.TestCase):
    """Test cases for the default service provider."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.container = DIContainer()
        self.provider = DefaultServiceProvider()
    
    def test_configure_services(self):
        """Test default service configuration."""
        self.provider.configure_services(self.container)
        
        # Check that core services are registered
        services = self.container.get_registered_services()
        
        expected_services = [
            'config_validator',
            'statistics',
            'logger',
            'exif_extractor',
            'video_processor',
            'file_organizer',
            'progress_reporter',
            'error_handler'
        ]
        
        for service in expected_services:
            self.assertIn(service, services)
    
    def test_resolve_core_services(self):
        """Test resolving core services."""
        self.provider.configure_services(self.container)
        
        # Test resolving key services
        config_validator = self.container.resolve('config_validator')
        self.assertIsNotNone(config_validator)
        
        statistics = self.container.resolve('statistics')
        self.assertIsInstance(statistics, StatisticsCollector)
        
        logger = self.container.resolve('logger')
        self.assertIsNotNone(logger)


class TestStatisticsCollector(unittest.TestCase):
    """Test cases for the statistics collector."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.stats = StatisticsCollector()
    
    def test_increment_counter(self):
        """Test counter increment functionality."""
        self.assertEqual(self.stats.stats.processed, 0)
        
        self.stats.increment('processed')
        self.assertEqual(self.stats.stats.processed, 1)
        
        self.stats.increment('processed', 5)
        self.assertEqual(self.stats.stats.processed, 6)
    
    def test_set_counter(self):
        """Test counter setting functionality."""
        self.stats.set_counter('processed', 10)
        self.assertEqual(self.stats.stats.processed, 10)
    
    def test_session_timing(self):
        """Test session timing functionality."""
        self.assertIsNone(self.stats.get_duration())
        
        self.stats.start_session()
        self.assertIsNotNone(self.stats.stats.start_time)
        
        self.stats.end_session()
        self.assertIsNotNone(self.stats.stats.end_time)
        
        duration = self.stats.get_duration()
        self.assertIsNotNone(duration)
        self.assertGreaterEqual(duration, 0)
    
    def test_operation_logging(self):
        """Test operation logging functionality."""
        source = Path("test_source.jpg")
        target = Path("test_target.jpg")
        
        self.stats.log_operation('move', source, target, True)
        self.assertEqual(self.stats.stats.processed, 1)
        self.assertEqual(self.stats.stats.moved, 1)
        
        self.stats.log_operation('copy', source, target, False, "Test error")
        self.assertEqual(self.stats.stats.errors, 1)
        
        failed_ops = self.stats.get_failed_operations()
        self.assertEqual(len(failed_ops), 1)
        self.assertEqual(failed_ops[0]['error'], "Test error")
    
    def test_get_summary(self):
        """Test summary generation."""
        self.stats.start_session()
        self.stats.increment('processed', 5)
        self.stats.increment('moved', 3)
        self.stats.end_session()
        
        summary = self.stats.get_summary()
        
        self.assertEqual(summary['counters']['processed'], 5)
        self.assertEqual(summary['counters']['moved'], 3)
        self.assertIsNotNone(summary['timing']['duration_seconds'])
        self.assertGreaterEqual(summary['performance']['files_per_second'], 0)
    
    def test_reset(self):
        """Test statistics reset functionality."""
        self.stats.increment('processed', 5)
        self.stats.increment('errors', 2)
        
        self.stats.reset()
        
        self.assertEqual(self.stats.stats.processed, 0)
        self.assertEqual(self.stats.stats.errors, 0)
        self.assertEqual(len(self.stats._operation_log), 0)


class TestPhotosSorterIntegration(unittest.TestCase):
    """Integration tests for the refactored PhotosSorter class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_config.yaml"
        
        # Create a minimal test configuration
        test_config = """
source_directory: "{}"
target_directory: null
date_format: "YYYY/MM/DD"
supported_extensions:
  - ".jpg"
  - ".jpeg"
  - ".png"
processing:
  move_files: false
  duplicate_handling: "rename"
video:
  enabled: false
safety:
  dry_run: true
  confirm_before_start: false
logging:
  level: "WARNING"
""".format(self.temp_dir)
        
        with open(self.config_path, 'w') as f:
            f.write(test_config)
        
        # Reset global container for clean test
        reset_container()
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
        reset_container()
    
    def test_initialization_with_valid_config(self):
        """Test PhotosSorter initialization with valid configuration."""
        sorter = PhotosSorter(str(self.config_path))
        
        self.assertIsNotNone(sorter.config)
        self.assertIsNotNone(sorter.container)
        self.assertEqual(sorter.config['source_directory'], self.temp_dir)
    
    def test_initialization_with_invalid_config(self):
        """Test PhotosSorter initialization with invalid configuration."""
        invalid_config = Path(self.temp_dir) / "invalid_config.yaml"
        with open(invalid_config, 'w') as f:
            f.write("invalid: yaml: content:")
        
        with self.assertRaises(ConfigurationError):
            PhotosSorter(str(invalid_config))
    
    def test_initialization_with_missing_config(self):
        """Test PhotosSorter initialization with missing configuration."""
        missing_config = Path(self.temp_dir) / "missing_config.yaml"
        
        with self.assertRaises(ConfigurationError):
            PhotosSorter(str(missing_config))
    
    @patch('src.photos_sorter.Path.exists')
    def test_run_with_missing_source_directory(self, mock_exists):
        """Test run method with missing source directory."""
        mock_exists.return_value = False
        
        sorter = PhotosSorter(str(self.config_path))
        
        with self.assertRaises(ConfigurationError):
            sorter.run(interactive=False)
    
    def test_dependency_injection(self):
        """Test that dependencies are properly injected."""
        sorter = PhotosSorter(str(self.config_path))
        
        # Test that container can resolve dependencies
        exif_extractor = sorter.container.resolve('exif_extractor')
        self.assertIsNotNone(exif_extractor)
        
        statistics = sorter.container.resolve('statistics')
        self.assertIsInstance(statistics, StatisticsCollector)
        
        config_validator = sorter.container.resolve('config_validator')
        self.assertIsNotNone(config_validator)
    
    def test_test_exif_extraction(self):
        """Test EXIF extraction testing functionality."""
        # Create a test image file (empty file for testing)
        test_image = Path(self.temp_dir) / "test.jpg"
        test_image.touch()
        
        sorter = PhotosSorter(str(self.config_path))
        
        # This should not raise an exception
        result = sorter.test_exif_extraction(str(test_image))
        self.assertIsInstance(result, dict)
    
    def test_scan_directory(self):
        """Test directory scanning functionality."""
        # Create some test files
        (Path(self.temp_dir) / "test1.jpg").touch()
        (Path(self.temp_dir) / "test2.png").touch()
        (Path(self.temp_dir) / "test3.txt").touch()  # Unsupported extension
        
        sorter = PhotosSorter(str(self.config_path))
        
        # Mock the file organizer's scan_directory method
        with patch.object(sorter.container.resolve('file_organizer'), 'scan_directory') as mock_scan:
            mock_scan.return_value = {
                'total_images': 2,
                'total_videos': 0,
                'total_files': 2
            }
            
            result = sorter.scan_directory(self.temp_dir)
            
            self.assertEqual(result['total_images'], 2)
            self.assertEqual(result['total_videos'], 0)
            mock_scan.assert_called_once_with(self.temp_dir)


class TestErrorHandling(unittest.TestCase):
    """Test cases for error handling improvements."""
    
    def test_configuration_error_hierarchy(self):
        """Test configuration error inheritance."""
        error = ConfigurationError("Test error")
        self.assertIsInstance(error, PhotoSorterError)
    
    def test_error_with_context(self):
        """Test error creation with context information."""
        error = PhotoSorterError(
            "Test error",
            file_path="/test/path",
            details={'key': 'value'}
        )
        
        self.assertEqual(error.file_path, "/test/path")
        self.assertEqual(error.details['key'], 'value')
        
        error_str = str(error)
        self.assertIn("Test error", error_str)
        self.assertIn("/test/path", error_str)
        self.assertIn("key=value", error_str)


class TestInterfaceCompliance(unittest.TestCase):
    """Test cases to ensure implementations comply with defined interfaces."""
    
    def test_statistics_provider_interface(self):
        """Test that StatisticsCollector implements StatisticsProvider interface."""
        collector = StatisticsCollector()
        
        # Check that required methods exist
        self.assertTrue(hasattr(collector, 'get_statistics'))
        self.assertTrue(hasattr(collector, 'reset_statistics'))
        self.assertTrue(hasattr(collector, 'increment_counter'))
        
        # Test method calls
        stats = collector.get_statistics()
        self.assertIsInstance(stats, dict)
        
        collector.increment_counter('processed', 5)
        collector.reset_statistics()


class TestGlobalContainer(unittest.TestCase):
    """Test cases for global container management."""
    
    def setUp(self):
        """Set up test fixtures."""
        reset_container()
    
    def tearDown(self):
        """Clean up test fixtures."""
        reset_container()
    
    def test_get_container_singleton(self):
        """Test that get_container returns the same instance."""
        container1 = get_container()
        container2 = get_container()
        
        self.assertIs(container1, container2)
    
    def test_container_auto_configuration(self):
        """Test that container is automatically configured."""
        container = get_container()
        
        # Should have default services registered
        services = container.get_registered_services()
        self.assertGreater(len(services), 0)
    
    def test_reset_container(self):
        """Test container reset functionality."""
        container1 = get_container()
        reset_container()
        container2 = get_container()
        
        self.assertIsNot(container1, container2)


if __name__ == '__main__':
    # Setup test logging
    import logging
    logging.basicConfig(level=logging.WARNING)
    
    # Run all tests
    unittest.main(verbosity=2)