"""
Replicate API client for audio transcription.
Handles communication with Replicate's Whisper + diarization model.
"""
import os
import time
import logging
from pathlib import Path
from typing import Dict, Optional, Protocol
from dataclasses import dataclass

from tenacity import retry, stop_after_attempt, wait_fixed
from ..utils.config import SETTINGS

log = logging.getLogger(__name__)


class ProgressCallback(Protocol):
    """Protocol for progress update callbacks."""
    
    def __call__(self, message: str = "") -> None:
        """Update progress with optional message."""
        ...


@dataclass
class TranscriptionConfig:
    """Configuration for transcription requests."""
    
    model: str = "thomasmol/whisper-diarization"
    version: str = ""  # Empty means use latest
    max_retries: int = 3
    retry_delay: float = 2.0


class TranscriptionError(Exception):
    """Raised when transcription fails."""
    pass


class ReplicateTranscriber:
    """
    Replicate API client for audio transcription.
    """
    
    def __init__(self, config: Optional[TranscriptionConfig] = None):
        """
        Initialize transcriber.
        
        Args:
            config: Transcription configuration
        """
        self.config = config or TranscriptionConfig()
        self._client = None
    
    @property
    def client(self):
        """Lazy-load Replicate client."""
        if self._client is None:
            try:
                import replicate
                # Create authenticated client with API token
                api_token = SETTINGS.replicate_api_token
                if not api_token:
                    raise TranscriptionError("REPLICATE_API_TOKEN environment variable not set")
                self._client = replicate.Client(api_token=api_token)
            except ImportError:
                raise ImportError("Please install replicate: pip install replicate")
        return self._client
    
    def get_model_version(self) -> str:
        """
        Get the model version to use.
        
        Returns:
            Model version ID (just the version ID, not model:version)
        """
        if self.config.version:
            return self.config.version
        
        # Get latest version (use same method as legacy)
        model = self.client.models.get(self.config.model)
        versions = list(model.versions.list())
        if not versions:
            raise TranscriptionError(f"No versions available for {self.config.model}")
        
        version_id = versions[0].id
        log.info(f"Using latest model version: {version_id}")
        return version_id
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        reraise=True
    )
    def transcribe(
        self,
        audio_path: Path,
        progress_callback: Optional[ProgressCallback] = None
    ) -> Dict:
        """
        Transcribe audio file using Replicate API.
        
        Args:
            audio_path: Path to audio file
            progress_callback: Optional progress callback
            
        Returns:
            Transcription result dictionary
            
        Raises:
            TranscriptionError: If transcription fails
            FileNotFoundError: If audio file doesn't exist
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        log.info(f"Starting transcription of: {audio_path.name}")
        
        try:
            # Get model version
            model_ref = self.get_model_version()
            
            # Create prediction
            with open(audio_path, "rb") as audio_file:
                prediction = self.client.predictions.create(
                    version=model_ref,
                    input={"file": audio_file}
                )
            
            log.info(f"Prediction created: {prediction.id}")
            
            # Poll for completion
            return self._poll_prediction(prediction, progress_callback)
            
        except Exception as e:
            log.error(f"Transcription failed: {e}")
            raise TranscriptionError(f"Failed to transcribe audio: {e}") from e
    
    def _poll_prediction(
        self,
        prediction,
        progress_callback: Optional[ProgressCallback] = None
    ) -> Dict:
        """
        Poll prediction until completion.
        
        Args:
            prediction: Replicate prediction object
            progress_callback: Optional progress callback
            
        Returns:
            Prediction output
            
        Raises:
            TranscriptionError: If prediction fails
        """
        if progress_callback:
            progress_callback("Transcribing audio (this may take a while)...")
        
        while prediction.status not in ["succeeded", "failed", "canceled"]:
            time.sleep(2)
            # Use legacy approach: get fresh prediction object
            prediction = self.client.predictions.get(prediction.id)
            
            if progress_callback:
                progress_callback()  # Update progress indicator
        
        if prediction.status == "succeeded":
            log.info("Transcription completed successfully")
            return prediction.output
        else:
            error_msg = f"Prediction {prediction.status}"
            if hasattr(prediction, 'error') and prediction.error:
                error_msg += f": {prediction.error}"
            raise TranscriptionError(error_msg)