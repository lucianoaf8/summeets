"""
Clean transcription pipeline using modular architecture.
Replaces the monolithic transcribe.py with focused, testable components.
"""
import logging
from pathlib import Path
from typing import Callable, Optional, Tuple, List

from ..utils.config import SETTINGS
from ..audio import pick_best_audio, ensure_wav16k_mono, compress_audio_for_upload, cleanup_temp_file
from .replicate_api import ReplicateTranscriber
from .formatting import format_transcript_output, parse_replicate_output, Segment

log = logging.getLogger(__name__)


class TranscriptionPipeline:
    """
    Main transcription pipeline that orchestrates the full process.
    """
    
    def __init__(self):
        """Initialize the pipeline with default settings."""
        self.transcriber = ReplicateTranscriber()
    
    def process_audio_input(
        self,
        audio_path: Optional[Path] = None,
        path_callback: Optional[callable] = None
    ) -> Path:
        """
        Process and validate audio input.

        Args:
            audio_path: Optional path to audio file or directory
            path_callback: Optional callback to request path from user.
                           Should return Path or None to cancel.

        Returns:
            Path to the selected audio file

        Raises:
            ValueError: If no valid audio found or cancelled
            FileNotFoundError: If audio path doesn't exist
        """
        if not audio_path:
            if path_callback:
                audio_path = path_callback()
                if audio_path is None:
                    raise ValueError("Audio path selection cancelled")
            else:
                raise ValueError("No audio path provided and no callback available")

        if not audio_path.exists():
            raise FileNotFoundError(f"Audio path not found: {audio_path}")

        # Select best audio file if directory provided
        if audio_path.is_dir():
            audio_path = pick_best_audio(audio_path)

        log.info(f"Using audio file: {audio_path}")
        return audio_path
    
    def prepare_audio(self, audio_path: Path) -> Path:
        """
        Prepare audio for transcription (format conversion and compression).
        
        Args:
            audio_path: Path to source audio file
            
        Returns:
            Path to prepared audio file (may be same as input)
        """
        log.info("Preparing audio for transcription...")
        
        # Convert to optimal format
        prepared_path = ensure_wav16k_mono(audio_path)
        
        # Compress if needed for upload
        final_path = compress_audio_for_upload(prepared_path)
        
        return final_path
    
    def transcribe_audio_file(self, audio_path: Path) -> List[Segment]:
        """
        Transcribe audio file using Replicate API.
        
        Args:
            audio_path: Path to prepared audio file
            
        Returns:
            List of transcript segments
        """
        log.info("Starting transcription...")
        
        # Define progress callback
        def progress_callback(message: str = "") -> None:
            if message:
                log.info(message)
        
        # Transcribe using Replicate
        raw_output = self.transcriber.transcribe(audio_path, progress_callback)
        
        # Parse output into structured segments
        segments = parse_replicate_output(raw_output)
        
        log.info(f"Transcription completed: {len(segments)} segments")
        return segments
    
    def save_outputs(self, segments: List[Segment], audio_path: Path, output_dir: Path) -> Path:
        """
        Save transcription outputs in multiple formats.
        
        Args:
            segments: Transcription segments
            audio_path: Original audio file path (for naming)
            output_dir: Output directory (fallback, preferably use new structure)
            
        Returns:
            Path to main JSON output file
        """
        # Use new data manager structure if available
        try:
            from ..utils.fsio import get_data_manager
            data_manager = get_data_manager()
            
            # Extract clean base name (remove processing suffixes)
            base_name = audio_path.stem.replace("_extracted", "").replace("_volume", "").replace("_normalized", "")
            
            # Create transcript subdirectory for this file
            transcript_subdir = data_manager.transcript_dir / base_name
            transcript_subdir.mkdir(parents=True, exist_ok=True)
            
            base_path = transcript_subdir / base_name
            log.info(f"Using new transcript structure: {transcript_subdir}")
            
        except ImportError:
            # Fallback to legacy structure
            output_dir.mkdir(parents=True, exist_ok=True)
            base_name = audio_path.stem
            base_path = output_dir / base_name
            log.info(f"Using legacy structure: {output_dir}")
        
        # Save in multiple formats
        output_paths = format_transcript_output(segments, base_path)
        
        log.info(f"Saved transcription outputs:")
        for format_name, path in output_paths.items():
            log.info(f"  {format_name.upper()}: {path}")
        
        return output_paths.get("json", base_path.with_suffix(".json"))
    
    def run(
        self,
        audio_path: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        path_callback: Optional[callable] = None
    ) -> Path:
        """
        Run the complete transcription pipeline.

        Args:
            audio_path: Optional path to audio file or directory
            output_dir: Optional output directory (defaults to configured)
            path_callback: Optional callback for user path input

        Returns:
            Path to main JSON transcript file
        """
        try:
            # Process input
            audio_path = self.process_audio_input(audio_path, path_callback)
            
            # Prepare audio
            prepared_path = self.prepare_audio(audio_path)
            
            try:
                # Transcribe
                segments = self.transcribe_audio_file(prepared_path)
                
                # Save outputs
                output_dir = output_dir or SETTINGS.out_dir
                json_path = self.save_outputs(segments, audio_path, output_dir)
                
                log.info(f"Transcription pipeline completed successfully: {json_path}")
                return json_path
                
            finally:
                # Clean up temporary files
                cleanup_temp_file(prepared_path, audio_path)
                
        except Exception as e:
            log.error(f"Transcription pipeline failed: {e}")
            raise


def run(
    audio_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    path_callback: Optional[callable] = None
) -> Path:
    """
    Convenience function to run transcription pipeline.

    Args:
        audio_path: Optional path to audio file or directory
        output_dir: Optional output directory
        path_callback: Optional callback for user path input

    Returns:
        Path to JSON transcript file
    """
    pipeline = TranscriptionPipeline()
    return pipeline.run(audio_path, output_dir, path_callback)


# Legacy compatibility - remove progress bars from core logic
def transcribe_audio(audio_path: Path) -> List[Segment]:
    """
    Legacy compatibility function.
    Note: This is for backward compatibility only.
    """
    pipeline = TranscriptionPipeline()
    prepared_path = pipeline.prepare_audio(audio_path)
    
    try:
        return pipeline.transcribe_audio_file(prepared_path)
    finally:
        cleanup_temp_file(prepared_path, audio_path)