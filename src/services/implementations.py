"""Concrete implementations of service interfaces.

These wrap the existing module-level functions for DI compatibility.
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

from .interfaces import (
    AudioProcessorInterface,
    TranscriberInterface,
    SummarizerInterface,
)
from ..utils.config import SETTINGS

log = logging.getLogger(__name__)


class FFmpegAudioProcessor(AudioProcessorInterface):
    """Audio processor implementation using FFmpeg."""

    def probe(self, input_path: Path) -> str:
        from ..audio.ffmpeg_ops import probe
        return probe(str(input_path))

    def normalize_loudness(self, input_path: Path, output_path: Path) -> None:
        from ..audio.ffmpeg_ops import normalize_loudness
        normalize_loudness(str(input_path), str(output_path))

    def extract_audio(
        self,
        input_path: Path,
        output_path: Path,
        codec: Optional[str] = None
    ) -> None:
        from ..audio.ffmpeg_ops import extract_audio_copy, extract_audio_reencode
        if codec:
            extract_audio_reencode(str(input_path), str(output_path), codec)
        else:
            extract_audio_copy(str(input_path), str(output_path))

    def get_duration(self, input_path: Path) -> float:
        from ..audio.ffmpeg_ops import ffprobe_info
        info = ffprobe_info(input_path)
        return info.get("duration", 0.0)


class ReplicateTranscriberService(TranscriberInterface):
    """Transcriber implementation using Replicate API."""

    def __init__(self):
        from ..transcribe.replicate_api import ReplicateTranscriber
        self._transcriber = ReplicateTranscriber()

    def transcribe(
        self,
        audio_path: Path,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        return self._transcriber.transcribe(audio_path, progress_callback)

    def get_segments(
        self,
        audio_path: Path,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> List[Dict[str, Any]]:
        from ..transcribe.formatting import parse_replicate_output
        raw_output = self.transcribe(audio_path, progress_callback)
        return parse_replicate_output(raw_output)


class LLMSummarizer(SummarizerInterface):
    """Summarizer implementation using configured LLM provider."""

    def __init__(self, provider: Optional[str] = None):
        self._provider = provider or SETTINGS.provider

    @property
    def provider_name(self) -> str:
        return self._provider

    def _get_client(self):
        if self._provider == "anthropic":
            from ..providers import anthropic_client
            return anthropic_client
        else:
            from ..providers import openai_client
            return openai_client

    def summarize_transcript(
        self,
        segments: List[Dict[str, Any]],
        template: Optional[str] = None
    ) -> str:
        from ..summarize.pipeline import template_aware_summarize
        return template_aware_summarize(
            segments,
            template=template,
            provider=self._provider
        )

    def summarize_with_cod(self, text: str, passes: int = 2) -> str:
        client = self._get_client()
        return client.chain_of_density_summarize(text, passes)


def register_default_services():
    """Register default service implementations (idempotent)."""
    from .container import get_container

    container = get_container()

    # Skip if already registered
    if container.is_registered(AudioProcessorInterface):
        return

    container.register(AudioProcessorInterface, FFmpegAudioProcessor)
    container.register(TranscriberInterface, ReplicateTranscriberService)
    container.register(SummarizerInterface, LLMSummarizer)

    log.debug("Default services registered")
