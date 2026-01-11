"""Service container for dependency injection.

Provides centralized service registration and resolution.
Supports both singleton and transient lifetimes.
"""
import logging
from typing import Dict, Type, Optional, Any, Callable

from .interfaces import (
    AudioProcessorInterface,
    TranscriberInterface,
    SummarizerInterface,
)

log = logging.getLogger(__name__)


class ServiceContainer:
    """
    Dependency injection container for managing service instances.

    Supports:
    - Singleton services (one instance shared)
    - Transient services (new instance per request)
    - Factory functions for deferred initialization
    """

    _services: Dict[Type, Any] = {}
    _factories: Dict[Type, Callable[[], Any]] = {}
    _singletons: Dict[Type, Any] = {}

    @classmethod
    def register(
        cls,
        interface: Type,
        implementation: Type,
        singleton: bool = True
    ) -> None:
        """
        Register a service implementation.

        Args:
            interface: The abstract interface type
            implementation: The concrete implementation class
            singleton: If True, reuse same instance (default)
        """
        if singleton:
            cls._services[interface] = implementation
        else:
            cls._factories[interface] = implementation
        log.debug(f"Registered {implementation.__name__} for {interface.__name__}")

    @classmethod
    def register_instance(cls, interface: Type, instance: Any) -> None:
        """
        Register a pre-created service instance.

        Args:
            interface: The abstract interface type
            instance: The instance to use
        """
        cls._singletons[interface] = instance
        log.debug(f"Registered instance for {interface.__name__}")

    @classmethod
    def register_factory(
        cls,
        interface: Type,
        factory: Callable[[], Any]
    ) -> None:
        """
        Register a factory function for creating services.

        Args:
            interface: The abstract interface type
            factory: Callable that creates the service
        """
        cls._factories[interface] = factory
        log.debug(f"Registered factory for {interface.__name__}")

    @classmethod
    def resolve(cls, interface: Type) -> Any:
        """
        Resolve a service by its interface.

        Args:
            interface: The interface type to resolve

        Returns:
            Service instance

        Raises:
            KeyError: If service not registered
        """
        # Check for pre-created singleton
        if interface in cls._singletons:
            return cls._singletons[interface]

        # Check for registered implementation (singleton)
        if interface in cls._services:
            impl = cls._services[interface]
            if interface not in cls._singletons:
                cls._singletons[interface] = impl()
            return cls._singletons[interface]

        # Check for factory (transient)
        if interface in cls._factories:
            factory = cls._factories[interface]
            if callable(factory) and isinstance(factory, type):
                return factory()
            return factory()

        raise KeyError(f"No service registered for {interface.__name__}")

    @classmethod
    def get_audio_processor(cls) -> AudioProcessorInterface:
        """Get the registered audio processor service."""
        return cls.resolve(AudioProcessorInterface)

    @classmethod
    def get_transcriber(cls) -> TranscriberInterface:
        """Get the registered transcriber service."""
        return cls.resolve(TranscriberInterface)

    @classmethod
    def get_summarizer(cls) -> SummarizerInterface:
        """Get the registered summarizer service."""
        return cls.resolve(SummarizerInterface)

    @classmethod
    def reset(cls) -> None:
        """Clear all registrations (useful for testing)."""
        cls._services.clear()
        cls._factories.clear()
        cls._singletons.clear()

    @classmethod
    def is_registered(cls, interface: Type) -> bool:
        """Check if a service is registered."""
        return (
            interface in cls._services or
            interface in cls._factories or
            interface in cls._singletons
        )
