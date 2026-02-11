"""Service layer for dependency injection."""
from .interfaces import (
    AudioProcessorInterface,
    TranscriberInterface,
    SummarizerInterface,
)
from .container import ServiceContainer, get_container, reset_container
from .implementations import (
    FFmpegAudioProcessor,
    ReplicateTranscriberService,
    LLMSummarizer,
    register_default_services,
)

__all__ = [
    "AudioProcessorInterface",
    "TranscriberInterface",
    "SummarizerInterface",
    "ServiceContainer",
    "get_container",
    "reset_container",
    "FFmpegAudioProcessor",
    "ReplicateTranscriberService",
    "LLMSummarizer",
    "register_default_services",
]
