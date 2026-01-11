"""
Workflow engine for flexible processing pipeline.
Supports conditional execution based on input file type and user configuration.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable

from pydantic import BaseModel, Field, ConfigDict

from .models import TranscriptData, SummaryData, InputFileType, WorkflowStep
from .utils.validation import validate_workflow_input, detect_file_type
from .utils.exceptions import SummeetsError
from .utils.config import SETTINGS
from .utils.fsio import get_data_manager
from .audio.ffmpeg_ops import (
    extract_audio_from_video,
    increase_audio_volume,
    convert_audio_format,
    normalize_loudness,
    ensure_wav16k_mono
)
from .transcribe.pipeline import run as transcribe_run
from .summarize.pipeline import run as summarize_run
from .workflow_components import WorkflowValidator, WorkflowStepFactory, WorkflowExecutor

log = logging.getLogger(__name__)


class WorkflowConfig(BaseModel):
    """Configuration for workflow execution."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # File paths
    input_file: Path
    output_dir: Path

    # Step enablement
    extract_audio: bool = True
    process_audio: bool = True
    transcribe: bool = True
    summarize: bool = True

    # Extract audio settings
    audio_format: str = "m4a"
    audio_quality: str = "high"

    # Process audio settings
    increase_volume: bool = False
    volume_gain_db: float = 10.0
    normalize_audio: bool = True
    output_formats: List[str] = Field(default_factory=lambda: ["m4a"])

    # Transcribe settings
    transcribe_model: str = "thomasmol/whisper-diarization"
    language: str = "auto"

    # Summarize settings
    summary_template: str = "Default"
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    auto_detect_template: bool = True


class WorkflowEngine:
    """Main workflow execution engine.

    Uses composition with specialized components:
    - WorkflowValidator: Configuration validation
    - WorkflowStepFactory: Step creation
    - WorkflowExecutor: Step execution
    """

    def __init__(
        self,
        config: WorkflowConfig,
        validator: Optional[WorkflowValidator] = None,
        step_factory: Optional[WorkflowStepFactory] = None,
        executor: Optional[WorkflowExecutor] = None
    ):
        """Initialize workflow engine with configuration and optional components.

        Args:
            config: WorkflowConfig instance
            validator: Optional custom validator (for testing)
            step_factory: Optional custom step factory (for testing)
            executor: Optional custom executor (for testing)
        """
        self.config = config
        self.file_type = None
        self.current_audio_file = None
        self.current_transcript = None
        self.results = {}

        # Initialize components (allow injection for testing)
        self._validator = validator or WorkflowValidator()
        self._executor = executor or WorkflowExecutor()

        # Validate input using component
        self._validate_config()

        # Step factory needs engine reference for step functions
        self._step_factory = step_factory or WorkflowStepFactory(self)

    def _validate_config(self):
        """Validate workflow configuration using validator component."""
        validated_path, file_type = self._validator.validate(self.config)
        self.config.input_file = validated_path
        self.file_type = file_type

    def execute(self, progress_callback: Optional[Callable[[int, int, str, str], None]] = None) -> Dict[str, Any]:
        """Execute the workflow pipeline.

        Args:
            progress_callback: Optional callback for progress updates

        Returns:
            Dictionary mapping step names to their results
        """
        log.info(f"Starting workflow execution for {self.file_type} file: {self.config.input_file}")

        # Create workflow steps using factory
        steps = self._step_factory.create_steps(self.config, self.file_type)

        # Filter steps that can execute for this file type
        executable_steps = self._step_factory.filter_executable_steps(steps, self.file_type)

        # Pre-execution setup based on file type
        if self.file_type == "audio":
            self.current_audio_file = self.config.input_file
        elif self.file_type == "transcript":
            self._load_existing_transcript()

        log.info(f"Executing {len(executable_steps)} workflow steps: {[s.name for s in executable_steps]}")

        # Execute steps using executor
        self.results = self._executor.execute_steps(executable_steps, progress_callback)

        log.info("Workflow execution completed successfully")
        return self.results
    
    def _extract_audio_step(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Extract audio from video file."""
        if self.file_type != "video":
            log.warning("Skipping audio extraction - not a video file")
            return {"skipped": True, "reason": "Not a video file"}
        
        # Use data manager for new structure
        data_manager = get_data_manager()
        
        # Generate output path using new structure
        base_name = self.config.input_file.stem
        output_path = data_manager.get_audio_path(base_name, settings['format'])
        
        # Extract audio
        extracted_path = extract_audio_from_video(
            video_path=self.config.input_file,
            output_path=output_path,
            format=settings["format"],
            quality=settings["quality"],
            normalize=True
        )
        
        # Update current audio file for next steps
        self.current_audio_file = extracted_path
        
        log.info(f"Audio extracted to new structure: {extracted_path}")
        
        return {
            "input_file": str(self.config.input_file),
            "output_file": str(extracted_path),
            "format": settings["format"],
            "quality": settings["quality"]
        }
    
    def _process_audio_step(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Process audio file with volume and format adjustments."""
        if self.file_type == "transcript":
            log.warning("Skipping audio processing - transcript file")
            return {"skipped": True, "reason": "Transcript file"}
        
        if not self.current_audio_file:
            raise SummeetsError("No audio file available for processing")
        
        results = {
            "input_file": str(self.current_audio_file),
            "processed_files": []
        }
        
        current_file = self.current_audio_file
        
        # Use data manager for new structure
        data_manager = get_data_manager()
        base_name = current_file.stem.replace("_extracted", "")  # Remove extracted suffix if present
        
        # Volume adjustment
        if settings.get("increase_volume", False):
            volume_output = data_manager.get_audio_path(f"{base_name}_volume", current_file.suffix[1:])
            volume_file = increase_audio_volume(
                input_path=current_file,
                output_path=volume_output,
                gain_db=settings.get("volume_gain_db", 10.0)
            )
            current_file = volume_file
            results["processed_files"].append({
                "type": "volume_adjustment",
                "file": str(volume_file),
                "gain_db": settings.get("volume_gain_db", 10.0)
            })
        
        # Normalization
        if settings.get("normalize_audio", True):
            norm_output = data_manager.get_audio_path(f"{base_name}_normalized", current_file.suffix[1:])
            normalize_loudness(str(current_file), str(norm_output))
            current_file = norm_output
            results["processed_files"].append({
                "type": "normalization", 
                "file": str(norm_output)
            })
        
        # Format conversions
        output_formats = settings.get("output_formats", ["m4a"])
        for fmt in output_formats:
            if fmt != current_file.suffix[1:]:  # Skip if already in this format
                format_output = self.config.output_dir / f"{current_file.stem}.{fmt}"
                converted_file = convert_audio_format(
                    input_path=current_file,
                    output_path=format_output,
                    format=fmt,
                    quality="medium"
                )
                results["processed_files"].append({
                    "type": "format_conversion",
                    "file": str(converted_file),
                    "format": fmt
                })
        
        # Update current audio file for transcription
        self.current_audio_file = current_file
        
        return results
    
    def _transcribe_step(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Transcribe audio file."""
        if self.file_type == "transcript":
            log.warning("Skipping transcription - already have transcript")
            return {"skipped": True, "reason": "Already have transcript"}
        
        if not self.current_audio_file:
            raise SummeetsError("No audio file available for transcription")
        
        # Ensure audio is in optimal format for transcription
        transcription_audio = ensure_wav16k_mono(self.current_audio_file)
        
        # Transcribe using the pipeline
        transcript_file = transcribe_run(
            audio_path=transcription_audio,
            output_dir=self.config.output_dir
        )
        
        # Create a simple transcript data structure for summarization
        from .models import TranscriptData
        self.current_transcript = TranscriptData(
            segments=[],  # Will be loaded from file when needed
            duration=0.0,  # Will be calculated when needed
            output_file=transcript_file
        )
        
        return {
            "audio_file": str(transcription_audio),
            "model": settings["model"],
            "language": settings.get("language", "auto"),
            "transcript_file": str(transcript_file),
            "segments_count": "generated",
            "duration": "calculated"
        }
    
    def _summarize_step(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize transcript."""
        if not self.current_transcript:
            if self.file_type == "transcript":
                # Load transcript from file
                self._load_existing_transcript()
            else:
                raise SummeetsError("No transcript available for summarization")
        
        # Get transcript file path
        transcript_file = self.current_transcript.output_file if self.current_transcript else self.config.input_file
        
        # Summarize using the pipeline (will use transcript subdirectory if using new structure)
        summary_file, _ = summarize_run(
            transcript_path=transcript_file,
            provider=settings["provider"],
            model=settings["model"],
            output_dir=self.config.output_dir,
            auto_detect_template=settings.get("auto_detect_template", True)
        )
        
        return {
            "transcript_file": str(transcript_file),
            "provider": settings["provider"],
            "model": settings["model"],
            "template": settings.get("template", "Default"),
            "summary_file": str(summary_file),
            "summary_length": "generated"
        }
    
    def _load_existing_transcript(self):
        """Load existing transcript from file."""
        import json
        
        try:
            with open(self.config.input_file, 'r', encoding='utf-8') as f:
                if self.config.input_file.suffix.lower() == '.json':
                    data = json.load(f)
                    # Create TranscriptData from loaded JSON
                    # This is a simplified version - real implementation would need proper parsing
                    from .models import TranscriptData
                    self.current_transcript = TranscriptData(
                        segments=data.get('segments', []) if isinstance(data, dict) else data,
                        duration=data.get('duration', 0.0) if isinstance(data, dict) else 0.0,
                        output_file=self.config.input_file
                    )
                else:
                    # Handle text files
                    content = f.read()
                    from .models import TranscriptData, Segment
                    self.current_transcript = TranscriptData(
                        segments=[Segment(
                            text=content,
                            start=0.0,
                            end=0.0,
                            speaker="UNKNOWN"
                        )],
                        duration=0.0,
                        output_file=self.config.input_file
                    )
                    
            log.info(f"Loaded existing transcript from: {self.config.input_file}")
            
        except Exception as e:
            raise SummeetsError(f"Failed to load transcript file: {e}")


def execute_workflow(config: WorkflowConfig, progress_callback: Optional[Callable[[int, int, str, str], None]] = None) -> Dict[str, Any]:
    """
    Execute a workflow with the given configuration.
    
    Args:
        config: Workflow configuration
        progress_callback: Optional callback for progress updates
        
    Returns:
        Dictionary with workflow results
        
    Raises:
        SummeetsError: If workflow execution fails
    """
    engine = WorkflowEngine(config)
    return engine.execute(progress_callback)
