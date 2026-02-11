"""Service container for dependency injection.

Provides centralized service registration and resolution.
Supports both singleton and transient lifetimes.
"""
import logging
import threading
from typing import Dict, Type, Any, Callable

from .interfaces import (
    AudioProcessorInterface,
    TranscriberInterface,
    SummarizerInterface,
)

log = logging.getLogger(__name__)


class ServiceContainer:
    """
    Dependency injection container for managing service instances.

    Each instance has its own registrations, avoiding class-level mutable
    state that leaks between tests or subclasses.

    Supports:
    - Singleton services (one instance shared)
    - Transient services (new instance per request)
    - Factory functions for deferred initialization
    """

    def __init__(self):
        self._services: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable[[], Any]] = {}
        self._singletons: Dict[Type, Any] = {}
        self._lock = threading.Lock()

    def register(
        self,
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
            self._services[interface] = implementation
        else:
            self._factories[interface] = implementation
        log.debug(f"Registered {implementation.__name__} for {interface.__name__}")

    def register_instance(self, interface: Type, instance: Any) -> None:
        """
        Register a pre-created service instance.

        Args:
            interface: The abstract interface type
            instance: The instance to use
        """
        self._singletons[interface] = instance
        log.debug(f"Registered instance for {interface.__name__}")

    def register_factory(
        self,
        interface: Type,
        factory: Callable[[], Any]
    ) -> None:
        """
        Register a factory function for creating services.

        Args:
            interface: The abstract interface type
            factory: Callable that creates the service
        """
        self._factories[interface] = factory
        log.debug(f"Registered factory for {interface.__name__}")

    def resolve(self, interface: Type) -> Any:
        """
        Resolve a service by its interface.

        Args:
            interface: The interface type to resolve

        Returns:
            Service instance

        Raises:
            KeyError: If service not registered
        """
        # Fast path: check for pre-created singleton (no lock needed)
        if interface in self._singletons:
            return self._singletons[interface]

        with self._lock:
            # Double-check after acquiring lock
            if interface in self._singletons:
                return self._singletons[interface]

            # Check for registered implementation (singleton)
            if interface in self._services:
                impl = self._services[interface]
                self._singletons[interface] = impl()
                return self._singletons[interface]

        # Check for factory (transient) - no lock needed
        if interface in self._factories:
            factory = self._factories[interface]
            return factory()

        raise KeyError(f"No service registered for {interface.__name__}")

    def get_audio_processor(self) -> AudioProcessorInterface:
        """Get the registered audio processor service."""
        return self.resolve(AudioProcessorInterface)

    def get_transcriber(self) -> TranscriberInterface:
        """Get the registered transcriber service."""
        return self.resolve(TranscriberInterface)

    def get_summarizer(self) -> SummarizerInterface:
        """Get the registered summarizer service."""
        return self.resolve(SummarizerInterface)

    def reset(self) -> None:
        """Clear all registrations (useful for testing)."""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()

    def is_registered(self, interface: Type) -> bool:
        """Check if a service is registered."""
        return (
            interface in self._services or
            interface in self._factories or
            interface in self._singletons
        )


# Global default container instance
_default_container = ServiceContainer()


def get_container() -> ServiceContainer:
    """Get the default service container."""
    return _default_container


def reset_container() -> None:
    """Reset the default container (for testing)."""
    global _default_container
    _default_container = ServiceContainer()
