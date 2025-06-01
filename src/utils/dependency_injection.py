#!/usr/bin/env python3
"""
Dependency Injection Container Module

This module provides a dependency injection container to improve testability
and modularity by removing hard-coded dependencies between components.
"""

import logging
from typing import Dict, Any, Type, TypeVar, Callable, Optional, Union
from abc import ABC, abstractmethod
from functools import wraps

T = TypeVar('T')


class DIContainer:
    """
    Dependency Injection Container for managing component dependencies.
    
    Supports singleton and transient lifetimes, factory methods,
    and circular dependency detection.
    """
    
    def __init__(self):
        """Initialize the DI container."""
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}
        self._scoped: Dict[str, Any] = {}
        self._lifetimes: Dict[str, str] = {}  # 'singleton', 'transient', 'scoped'
        self._resolving: set = set()  # For circular dependency detection
        self.logger = logging.getLogger(__name__)
    
    def register_singleton(self, interface: Union[str, Type], implementation: Union[Type, Any]) -> 'DIContainer':
        """
        Register a service as singleton (single instance for entire application).
        
        Args:
            interface: Interface name or type
            implementation: Implementation class or instance
            
        Returns:
            DIContainer: Self for method chaining
        """
        key = self._get_key(interface)
        
        if isinstance(implementation, type):
            self._factories[key] = implementation
        else:
            self._singletons[key] = implementation
            
        self._lifetimes[key] = 'singleton'
        self.logger.debug(f"Registered singleton: {key}")
        return self
    
    def register_transient(self, interface: Union[str, Type], implementation: Type) -> 'DIContainer':
        """
        Register a service as transient (new instance each time).
        
        Args:
            interface: Interface name or type
            implementation: Implementation class
            
        Returns:
            DIContainer: Self for method chaining
        """
        key = self._get_key(interface)
        self._factories[key] = implementation
        self._lifetimes[key] = 'transient'
        self.logger.debug(f"Registered transient: {key}")
        return self
    
    def register_scoped(self, interface: Union[str, Type], implementation: Type) -> 'DIContainer':
        """
        Register a service as scoped (single instance per scope).
        
        Args:
            interface: Interface name or type
            implementation: Implementation class
            
        Returns:
            DIContainer: Self for method chaining
        """
        key = self._get_key(interface)
        self._factories[key] = implementation
        self._lifetimes[key] = 'scoped'
        self.logger.debug(f"Registered scoped: {key}")
        return self
    
    def register_factory(self, interface: Union[str, Type], factory: Callable) -> 'DIContainer':
        """
        Register a factory method for creating instances.
        
        Args:
            interface: Interface name or type
            factory: Factory function that returns instance
            
        Returns:
            DIContainer: Self for method chaining
        """
        key = self._get_key(interface)
        self._factories[key] = factory
        self._lifetimes[key] = 'factory'
        self.logger.debug(f"Registered factory: {key}")
        return self
    
    def register_instance(self, interface: Union[str, Type], instance: Any) -> 'DIContainer':
        """
        Register a specific instance.
        
        Args:
            interface: Interface name or type
            instance: The instance to register
            
        Returns:
            DIContainer: Self for method chaining
        """
        key = self._get_key(interface)
        self._singletons[key] = instance
        self._lifetimes[key] = 'singleton'
        self.logger.debug(f"Registered instance: {key}")
        return self
    
    def clear_cache(self) -> 'DIContainer':
        """
        Clear all cached singleton and scoped instances.
        
        Returns:
            DIContainer: Self for method chaining
        """
        self._singletons.clear()
        self._scoped.clear()
        return self
    
    def resolve(self, interface: Union[str, Type], **kwargs) -> Any:
        """
        Resolve an instance of the specified interface.
        
        Args:
            interface: Interface name or type to resolve
            **kwargs: Additional arguments to pass to factory
            
        Returns:
            Any: Instance of the requested interface
        """
        key = self._get_key(interface)
        
        # Check for circular dependencies
        if key in self._resolving:
            raise ValueError(f"Circular dependency detected for {key}")
        
        if key not in self._lifetimes:
            raise ValueError(f"Service not registered: {key}")
        
        lifetime = self._lifetimes[key]
        
        # Handle singleton
        if lifetime == 'singleton':
            if key in self._singletons:
                return self._singletons[key]
            
            instance = self._create_instance(key, **kwargs)
            self._singletons[key] = instance
            return instance
        
        # Handle scoped
        elif lifetime == 'scoped':
            scope_key = f"{key}_{id(self)}"
            if scope_key in self._scoped:
                return self._scoped[scope_key]
            
            instance = self._create_instance(key, **kwargs)
            self._scoped[scope_key] = instance
            return instance
        
        # Handle transient
        else:
            return self._create_instance(key, **kwargs)
    
    def _create_instance(self, key: str, **kwargs) -> Any:
        """
        Create an instance using the registered factory.
        
        Args:
            key: Service key
            **kwargs: Additional arguments
            
        Returns:
            Any: Created instance
        """
        self._resolving.add(key)
        
        try:
            factory = self._factories[key]
            
            # If factory is a class, try to resolve constructor dependencies
            if isinstance(factory, type):
                instance = self._create_with_injection(factory, **kwargs)
            else:
                # Factory function
                instance = factory(self, **kwargs)
            
            return instance
            
        finally:
            self._resolving.discard(key)
    
    def _create_with_injection(self, cls: Type, **kwargs) -> Any:
        """
        Create instance with automatic dependency injection.
        
        Args:
            cls: Class to instantiate
            **kwargs: Additional arguments
            
        Returns:
            Any: Instance with dependencies injected
        """
        import inspect
        
        # Get constructor signature
        sig = inspect.signature(cls.__init__)
        constructor_args = {}
        
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
                
            # Check if parameter is provided in kwargs
            if param_name in kwargs:
                constructor_args[param_name] = kwargs[param_name]
                continue
            
            # Try to resolve from type annotation
            if param.annotation != inspect.Parameter.empty:
                try:
                    resolved = self.resolve(param.annotation)
                    constructor_args[param_name] = resolved
                    continue
                except ValueError:
                    pass
            
            # Check if parameter has default value
            if param.default != inspect.Parameter.empty:
                continue
            
            # Try to resolve by parameter name
            try:
                resolved = self.resolve(param_name)
                constructor_args[param_name] = resolved
            except ValueError:
                if param.default == inspect.Parameter.empty:
                    self.logger.warning(f"Could not resolve parameter '{param_name}' for {cls.__name__}")
        
        return cls(**constructor_args)
    
    def _get_key(self, interface: Union[str, Type]) -> str:
        """
        Get string key for interface.
        
        Args:
            interface: Interface name or type
            
        Returns:
            str: String key
        """
        if isinstance(interface, str):
            return interface
        elif hasattr(interface, '__name__'):
            return f"{interface.__module__}.{interface.__name__}"
        else:
            return str(interface)
    
    def clear_scope(self):
        """Clear all scoped instances."""
        self._scoped.clear()
        self.logger.debug("Cleared scoped instances")
    
    def is_registered(self, interface: Union[str, Type]) -> bool:
        """
        Check if service is registered.
        
        Args:
            interface: Interface name or type
            
        Returns:
            bool: True if registered
        """
        key = self._get_key(interface)
        return key in self._lifetimes
    
    def get_registered_services(self) -> Dict[str, str]:
        """
        Get all registered services and their lifetimes.
        
        Returns:
            Dict[str, str]: Service names and lifetimes
        """
        return self._lifetimes.copy()


class ServiceProvider(ABC):
    """
    Abstract base class for service providers that configure DI container.
    """
    
    @abstractmethod
    def configure_services(self, container: DIContainer):
        """
        Configure services in the DI container.
        
        Args:
            container: DI container to configure
        """
        pass


def inject(interface: Union[str, Type]):
    """
    Decorator for automatic dependency injection into methods.
    
    Args:
        interface: Interface to inject
        
    Returns:
        Callable: Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get container from first argument (usually self)
            if hasattr(args[0], 'container'):
                container = args[0].container
                service = container.resolve(interface)
                return func(*args, service, **kwargs)
            else:
                return func(*args, **kwargs)
        return wrapper
    return decorator


class DefaultServiceProvider(ServiceProvider):
    """
    Default service provider for PhotosSorter application.
    """
    
    def configure_services(self, container: DIContainer):
        """Configure default PhotosSorter services."""
        # Register core interfaces
        from .interfaces import (
            DateExtractor, FileProcessor, StatisticsProvider,
            ConfigValidator, FileGrouper, BatchProcessor
        )
        
        # Register implementations (will be imported when needed)
        self._register_core_services(container)
        self._register_processors(container)
        self._register_utilities(container)
    
    def _register_core_services(self, container: DIContainer):
        """Register core application services."""
        # Configuration validator
        container.register_singleton(
            'config_validator',
            lambda c: self._create_config_validator()
        )
        
        # Statistics collector
        def statistics_factory(c):
            import logging
            logger = logging.getLogger('dependency_injection')
            logger.debug("Statistics factory called - creating StatisticsCollector")
            result = self._create_statistics_collector()
            logger.debug(f"Statistics factory result: {type(result)}")
            return result
        
        container.register_singleton(
            'statistics',
            statistics_factory
        )
        
        # Logger
        container.register_singleton(
            'logger',
            lambda c: logging.getLogger('PhotosSorter')
        )
    
    def _register_processors(self, container: DIContainer):
        """Register file processors."""
        # EXIF extractor
        container.register_singleton(
            'exif_extractor',
            lambda c: self._create_exif_extractor()
        )
        
        # Video processor
        container.register_transient(
            'video_processor',
            lambda c, **kwargs: self._create_video_processor(kwargs.get('config'))
        )
        
        # File organizer
        container.register_transient(
            'file_organizer',
            lambda c, **kwargs: self._create_file_organizer(kwargs.get('config'), c)
        )
    
    def _register_utilities(self, container: DIContainer):
        """Register utility services."""
        # Progress reporter
        container.register_transient(
            'progress_reporter',
            lambda c: self._create_progress_reporter()
        )
        
        # Error handler
        container.register_transient(
            'error_handler',
            lambda c: self._create_error_handler()
        )
    
    def _create_config_validator(self):
        """Create configuration validator."""
        from .config_validator import ConfigValidator
        return ConfigValidator()
    
    def _create_statistics_collector(self):
        """Create statistics collector."""
        from .statistics import StatisticsCollector
        return StatisticsCollector()
    
    def _create_exif_extractor(self):
        """Create EXIF extractor."""
        try:
            from ..exif_extractor import ExifExtractor
        except ImportError:
            from exif_extractor import ExifExtractor
        return ExifExtractor()
    
    def _create_video_processor(self, config):
        """Create video processor."""
        try:
            from ..video_processor import VideoProcessor
        except ImportError:
            from video_processor import VideoProcessor
        return VideoProcessor(config)
    
    def _create_file_organizer(self, config, container):
        """Create file organizer with injected dependencies."""
        try:
            from ..file_organizer import FileOrganizer
        except ImportError:
            from file_organizer import FileOrganizer
        
        # Create dependencies directly to avoid DI caching issues
        try:
            from ..exif_extractor import ExifExtractor
        except ImportError:
            from exif_extractor import ExifExtractor
        exif_extractor = ExifExtractor()
        
        from .statistics import StatisticsCollector
        stats_collector = StatisticsCollector()
        
        organizer = FileOrganizer(
            config=config,
            exif_extractor=exif_extractor,
            stats_collector=stats_collector
        )
        
        return organizer
    
    def _create_progress_reporter(self):
        """Create progress reporter."""
        try:
            from tqdm import tqdm
            
            class TqdmProgressReporter:
                def __init__(self):
                    self.pbar = None
                
                def start(self, total: int, description: str = "Processing"):
                    self.pbar = tqdm(total=total, desc=description)
                
                def update(self, amount: int = 1):
                    if self.pbar:
                        self.pbar.update(amount)
                
                def finish(self):
                    if self.pbar:
                        self.pbar.close()
                
                def set_description(self, description: str):
                    if self.pbar:
                        self.pbar.set_description(description)
            
            return TqdmProgressReporter()
            
        except ImportError:
            # Fallback to simple console reporter
            class SimpleProgressReporter:
                def __init__(self):
                    self.current = 0
                    self.total = 0
                    self.description = ""
                
                def start(self, total: int, description: str = "Processing"):
                    self.total = total
                    self.current = 0
                    self.description = description
                    print(f"{description}: 0/{total}")
                
                def update(self, amount: int = 1):
                    self.current += amount
                    if self.current % 10 == 0 or self.current == self.total:
                        print(f"{self.description}: {self.current}/{self.total}")
                
                def finish(self):
                    print(f"{self.description}: Complete!")
                
                def set_description(self, description: str):
                    self.description = description
            
            return SimpleProgressReporter()
    
    def _create_error_handler(self):
        """Create error handler."""
        class DefaultErrorHandler:
            def __init__(self):
                self.logger = logging.getLogger('PhotosSorter.ErrorHandler')
            
            def handle_error(self, error: Exception, context: Dict[str, Any]) -> bool:
                """Handle error and decide if processing should continue."""
                self.logger.error(f"Error: {error}, Context: {context}")
                
                # Continue for recoverable errors
                from .exceptions import RECOVERABLE_ERRORS
                return isinstance(error, RECOVERABLE_ERRORS)
            
            def should_retry(self, error: Exception, attempt: int) -> bool:
                """Check if operation should be retried."""
                max_retries = self.get_max_retries()
                if attempt >= max_retries:
                    return False
                
                # Retry for specific error types
                from .exceptions import FILE_SYSTEM_ERRORS
                return isinstance(error, FILE_SYSTEM_ERRORS)
            
            def get_max_retries(self) -> int:
                """Get maximum number of retries."""
                return 3
        
        return DefaultErrorHandler()


# Global container instance
_container: Optional[DIContainer] = None


def get_container() -> DIContainer:
    """
    Get the global DI container instance.
    
    Returns:
        DIContainer: The global container instance
    """
    global _container
    if _container is None:
        _container = DIContainer()
        # Clear any potential cached state
        _container.clear_cache()
        # Configure with default services
        provider = DefaultServiceProvider()
        provider.configure_services(_container)
    return _container


def configure_container(provider: ServiceProvider) -> DIContainer:
    """
    Configure the global container with a custom provider.
    
    Args:
        provider: Service provider to configure the container
        
    Returns:
        DIContainer: The configured container
    """
    global _container
    _container = DIContainer()
    _container.clear_cache()
    provider.configure_services(_container)
    return _container


def reset_container():
    """Reset the global container."""
    global _container
    _container = None