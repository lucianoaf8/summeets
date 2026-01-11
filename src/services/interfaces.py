"""Service interfaces for dependency injection.

Abstract base classes defining contracts for core services.
Enables testability through mock implementations and loose coupling.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable


class AudioProcessorInterface(ABC):
    """Interface for audio/video processing operations."""

    @abstractmethod
    def probe(self, input_path: Path) -> str:
        """Probe media file for metadata.

        Args:
            input_path: Path to media file

        Returns:
            Probe output string
        """
        pass

    @abstractmethod
    def normalize_loudness(self, input_path: Path, output_path: Path) -> None:
        """Normalize audio loudness using EBU R128.

        Args:
            input_path: Source file path
            output_path: Destination file path
        """
        pass

    @abstractmethod
    def extract_audio(
        self,
        input_path: Path,
        output_path: Path,
        codec: Optional[str] = None
    ) -> None:
        """Extract audio from video file.

        Args:
            input_path: Source video path
            output_path: Destination audio path
            codec: Optional audio codec (aac, mp3, etc.)
        """
        pass

    @abstractmethod
    def get_duration(self, input_path: Path) -> float:
        """Get media duration in seconds.

        Args:
            input_path: Path to media file

        Returns:
            Duration in seconds
        """
        pass


class TranscriberInterface(ABC):
    """Interface for audio transcription services."""

    @abstractmethod
    def transcribe(
        self,
        audio_path: Path,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """Transcribe audio file.

        Args:
            audio_path: Path to audio file
            progress_callback: Optional progress update function

        Returns:
            Raw transcription output
        """
        pass

    @abstractmethod
    def get_segments(
        self,
        audio_path: Path,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> List[Dict[str, Any]]:
        """Transcribe and return parsed segments.

        Args:
            audio_path: Path to audio file
            progress_callback: Optional progress update function

        Returns:
            List of transcript segments with speaker, text, timing
        """
        pass


class SummarizerInterface(ABC):
    """Interface for text summarization services.

    Note: This extends the pattern from providers.base.LLMProvider
    for pipeline-level summarization operations.
    """

    @abstractmethod
    def summarize_transcript(
        self,
        segments: List[Dict[str, Any]],
        template: Optional[str] = None
    ) -> str:
        """Summarize transcript segments.

        Args:
            segments: List of transcript segments
            template: Optional template name (DEFAULT, SOP, etc.)

        Returns:
            Formatted summary text
        """
        pass

    @abstractmethod
    def summarize_with_cod(
        self,
        text: str,
        passes: int = 2
    ) -> str:
        """Apply Chain-of-Density summarization.

        Args:
            text: Text to summarize
            passes: Number of density improvement passes

        Returns:
            Condensed summary
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the underlying LLM provider name."""
        pass
