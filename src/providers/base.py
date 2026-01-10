"""
Abstract base class for LLM providers.

Provides a unified interface for all LLM provider implementations,
enabling provider-agnostic code in the pipeline.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import logging

log = logging.getLogger(__name__)


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All provider implementations (OpenAI, Anthropic, etc.) should inherit
    from this class and implement the required methods.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name (e.g., 'openai', 'anthropic')."""
        pass

    @property
    @abstractmethod
    def model(self) -> str:
        """Return the current model being used."""
        pass

    @abstractmethod
    def summarize_text(
        self,
        text: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Summarize or process text using the LLM.

        Args:
            text: The input text to process
            system_prompt: Optional system prompt to guide the model
            max_tokens: Maximum tokens in the response
            **kwargs: Provider-specific options (e.g., enable_thinking for Anthropic)

        Returns:
            The model's response text

        Raises:
            LLMProviderError: If the API call fails
        """
        pass

    @abstractmethod
    def chain_of_density_summarize(self, text: str, passes: int = 2) -> str:
        """
        Apply Chain-of-Density summarization.

        Args:
            text: Text to summarize
            passes: Number of density improvement passes

        Returns:
            Condensed summary

        Raises:
            LLMProviderError: If the API call fails
        """
        pass

    @abstractmethod
    def validate_api_key(self) -> bool:
        """
        Validate that the API key is properly configured.

        Returns:
            True if API key is valid, False otherwise
        """
        pass

    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the provider.

        Returns:
            Dictionary with health status information
        """
        try:
            is_valid = self.validate_api_key()
            return {
                "provider": self.name,
                "model": self.model,
                "api_key_valid": is_valid,
                "status": "healthy" if is_valid else "unhealthy"
            }
        except Exception as e:
            log.error(f"Health check failed for {self.name}: {e}")
            return {
                "provider": self.name,
                "model": self.model,
                "api_key_valid": False,
                "status": "error",
                "error": str(e)
            }


class ProviderRegistry:
    """
    Registry for LLM provider instances.

    Provides factory methods for getting provider instances by name.
    """

    _providers: Dict[str, type] = {}
    _instances: Dict[str, LLMProvider] = {}

    @classmethod
    def register(cls, name: str, provider_class: type) -> None:
        """
        Register a provider class.

        Args:
            name: Provider name (e.g., 'openai', 'anthropic')
            provider_class: The provider class to register
        """
        cls._providers[name.lower()] = provider_class
        log.debug(f"Registered provider: {name}")

    @classmethod
    def get(cls, name: str) -> LLMProvider:
        """
        Get a provider instance by name.

        Args:
            name: Provider name

        Returns:
            Provider instance

        Raises:
            ValueError: If provider is not registered
        """
        name = name.lower()
        if name not in cls._providers:
            available = ', '.join(cls._providers.keys())
            raise ValueError(
                f"Unknown provider: {name}. Available providers: {available}"
            )

        # Use singleton pattern for provider instances
        if name not in cls._instances:
            cls._instances[name] = cls._providers[name]()

        return cls._instances[name]

    @classmethod
    def reset(cls, name: Optional[str] = None) -> None:
        """
        Reset provider instance(s).

        Args:
            name: Optional provider name to reset. If None, resets all.
        """
        if name:
            name = name.lower()
            if name in cls._instances:
                del cls._instances[name]
        else:
            cls._instances.clear()

    @classmethod
    def available_providers(cls) -> list:
        """Return list of registered provider names."""
        return list(cls._providers.keys())
