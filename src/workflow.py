"""
Workflow engine for flexible processing pipeline.
Supports conditional execution based on input file type and user configuration.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from .models import TranscriptData, SummaryData
from .utils.validation import validate_workflow_input, detect_file_type
from .utils.exceptions import SummeetsError, ValidationError
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

log = logging.getLogger(__name__)


@dataclass
class WorkflowStep:
    """Represents a single workflow step."""
    name: str
    enabled: bool
    function: callable
    settings: Dict[str, Any]
    required_input_type: Optional[str] = None
    
    def can_execute(self, file_type: str) -> bool:
        """Check if this step can execute for the given file type."""
        if not self.enabled:
            return False
        if self.required_input_type and self.required_input_type != file_type:
            return False
        return True


@dataclass
class WorkflowConfig:
    """Configuration for workflow execution."""
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
    output_formats: List[str] = None
    
    # Transcribe settings
    transcribe_model: str = "thomasmol/whisper-diarization"
    language: str = "auto"
    
    # Summarize settings
    summary_template: str = "Default"
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    auto_detect_template: bool = True
    
    def __post_init__(self):
        if self.output_formats is None:
            self.output_formats = ["m4a"]


class WorkflowEngine:
    """Main workflow execution engine."""
    
    def __init__(self, config: WorkflowConfig):
        """Initialize workflow engine with configuration."""
        self.config = config
        self.file_type = None
        self.current_audio_file = None
        self.current_transcript = None
        self.results = {}
        
        # Validate input
        self._validate_config()
        
    def _validate_config(self):
        """Validate workflow configuration."""
        # Validate input file and determine type
        validated_path, file_type = validate_workflow_input(self.config.input_file)
        self.config.input_file = validated_path
        self.file_type = file_type
        
        log.info(f"Detected file type: {file_type} for {self.config.input_file}")
        
        # Ensure output directory exists
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        
    def _create_workflow_steps(self) -> List[WorkflowStep]:
        """Create workflow steps based on configuration."""
        steps = []
        
        # Step 1: Extract Audio (video only)
        steps.append(WorkflowStep(
            name="extract_audio",
            enabled=self.config.extract_audio,
            function=self._extract_audio_step,
            settings={
                "format": self.config.audio_format,
                "quality": self.config.audio_quality
            },
            required_input_type="video"
        ))
        
        # Step 2: Process Audio (video/audio only)
        steps.append(WorkflowStep(
            name="process_audio", 
            enabled=self.config.process_audio,
            function=self._process_audio_step,
            settings={
                "increase_volume": self.config.increase_volume,
                "volume_gain_db": self.config.volume_gain_db,
                "normalize_audio": self.config.normalize_audio,
                "output_formats": self.config.output_formats
            },
            required_input_type=None  # Can run on video or audio
        ))
        
        # Step 3: Transcribe (video/audio only)
        steps.append(WorkflowStep(
            name="transcribe",
            enabled=self.config.transcribe,
            function=self._transcribe_step,
            settings={
                "model": self.config.transcribe_model,
                "language": self.config.language
            },
            required_input_type=None  # Can run on video or audio
        ))
        
        # Step 4: Summarize (all file types)
        steps.append(WorkflowStep(
            name="summarize",
            enabled=self.config.summarize,
            function=self._summarize_step,
            settings={
                "template": self.config.summary_template,
                "provider": self.config.provider,
                "model": self.config.model,
                "auto_detect_template": self.config.auto_detect_template
            },
            required_input_type=None  # Can run on any type
        ))
        
        return steps
    
    def execute(self, progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        """Execute the workflow pipeline."""
        log.info(f"Starting workflow execution for {self.file_type} file: {self.config.input_file}")
        
        # Create workflow steps
        steps = self._create_workflow_steps()
        
        # Filter steps that can execute for this file type
        executable_steps = [
            step for step in steps 
            if step.can_execute(self.file_type)
        ]
        
        # Skip extract audio for audio files, skip both extract and transcribe for transcript files
        if self.file_type == "audio":
            # Audio files don't need extraction
            self.current_audio_file = self.config.input_file
        elif self.file_type == "transcript":
            # Transcript files don't need extraction or transcription
            # Load existing transcript
            self._load_existing_transcript()
        
        log.info(f"Executing {len(executable_steps)} workflow steps: {[s.name for s in executable_steps]}")
        
        # Execute steps
        total_steps = len(executable_steps)
        for i, step in enumerate(executable_steps):
            try:
                log.info(f"Executing step {i+1}/{total_steps}: {step.name}")
                
                if progress_callback:
                    progress_callback(
                        step=i+1,
                        total=total_steps,
                        step_name=step.name,
                        status=f"Executing {step.name}..."
                    )
                
                # Execute step
                step_result = step.function(step.settings)
                self.results[step.name] = step_result
                
                log.info(f"Completed step: {step.name}")
                
            except Exception as e:
                error_msg = f"Error in step '{step.name}': {str(e)}"
                log.error(error_msg)
                raise SummeetsError(error_msg) from e
        
        if progress_callback:
            progress_callback(
                step=total_steps,
                total=total_steps,
                step_name="complete",
                status="Workflow completed successfully"
            )
        
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
                    from .models import TranscriptData, TranscriptSegment
                    self.current_transcript = TranscriptData(
                        segments=[TranscriptSegment(
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


def execute_workflow(config: WorkflowConfig, progress_callback: Optional[callable] = None) -> Dict[str, Any]:
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
