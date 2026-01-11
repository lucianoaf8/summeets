"""Workflow engine components following Single Responsibility Principle.

Provides focused classes for workflow validation, step creation, and execution.
"""
import logging
from pathlib import Path
from typing import Callable, Dict, Any, List, Optional

from .utils.validation import validate_workflow_input, validate_file_size, MAX_FILE_SIZE_MB
from .utils.exceptions import SummeetsError

log = logging.getLogger(__name__)


class WorkflowValidator:
    """Validates workflow configuration before execution.

    Responsible for:
    - Input file validation
    - File type detection
    - File size validation
    - Output directory creation
    """

    def __init__(self, max_file_size_mb: float = MAX_FILE_SIZE_MB):
        """Initialize validator with configurable file size limit.

        Args:
            max_file_size_mb: Maximum allowed file size in MB (default: 500MB)
        """
        self.max_file_size_mb = max_file_size_mb

    def validate(self, config) -> tuple:
        """Validate configuration and return validated path and file type.

        Args:
            config: WorkflowConfig instance

        Returns:
            Tuple of (validated_path, file_type)

        Raises:
            SummeetsError: If validation fails
        """
        validated_path, file_type = validate_workflow_input(config.input_file)
        log.info(f"Detected file type: {file_type} for {validated_path}")

        # Validate file size (skip for transcript files which are typically small)
        if file_type in ("video", "audio"):
            validate_file_size(validated_path, self.max_file_size_mb, file_type)
            log.info(f"File size validation passed for {file_type} file")

        # Ensure output directory exists
        config.output_dir.mkdir(parents=True, exist_ok=True)

        return validated_path, file_type


class WorkflowStepFactory:
    """Creates workflow steps based on configuration and file type.

    Responsible for:
    - Step instantiation
    - Step configuration
    - Conditional step enablement
    """

    def __init__(self, engine):
        """Initialize with reference to engine for step functions.

        Args:
            engine: WorkflowEngine instance with step implementation methods
        """
        self._engine = engine

    def create_steps(self, config, file_type: str) -> List:
        """Create workflow steps for the given configuration.

        Args:
            config: WorkflowConfig instance
            file_type: Detected input file type

        Returns:
            List of WorkflowStep instances
        """
        from .models import WorkflowStep

        steps = []

        # Step 1: Extract Audio (video only)
        steps.append(WorkflowStep(
            name="extract_audio",
            enabled=config.extract_audio,
            function=self._engine._extract_audio_step,
            settings={
                "format": config.audio_format,
                "quality": config.audio_quality
            },
            required_input_type="video"
        ))

        # Step 2: Process Audio (video/audio only)
        steps.append(WorkflowStep(
            name="process_audio",
            enabled=config.process_audio,
            function=self._engine._process_audio_step,
            settings={
                "increase_volume": config.increase_volume,
                "volume_gain_db": config.volume_gain_db,
                "normalize_audio": config.normalize_audio,
                "output_formats": config.output_formats
            },
            required_input_type=None
        ))

        # Step 3: Transcribe (video/audio only)
        steps.append(WorkflowStep(
            name="transcribe",
            enabled=config.transcribe,
            function=self._engine._transcribe_step,
            settings={
                "model": config.transcribe_model,
                "language": config.language
            },
            required_input_type=None
        ))

        # Step 4: Summarize (all file types)
        steps.append(WorkflowStep(
            name="summarize",
            enabled=config.summarize,
            function=self._engine._summarize_step,
            settings={
                "template": config.summary_template,
                "provider": config.provider,
                "model": config.model,
                "auto_detect_template": config.auto_detect_template
            },
            required_input_type=None
        ))

        return steps

    def filter_executable_steps(
        self,
        steps: List,
        file_type: str
    ) -> List:
        """Filter steps that can execute for the given file type.

        Args:
            steps: List of WorkflowStep instances
            file_type: Input file type

        Returns:
            Filtered list of executable steps
        """
        return [step for step in steps if step.can_execute(file_type)]


class WorkflowExecutor:
    """Executes workflow steps with progress tracking.

    Responsible for:
    - Step execution
    - Progress callback management
    - Error handling during execution
    """

    def execute_steps(
        self,
        steps: List,
        progress_callback: Optional[Callable[[int, int, str, str], None]] = None
    ) -> Dict[str, Any]:
        """Execute workflow steps in order.

        Args:
            steps: List of WorkflowStep instances to execute
            progress_callback: Optional callback for progress updates

        Returns:
            Dictionary mapping step names to their results

        Raises:
            SummeetsError: If any step fails
        """
        results = {}
        total_steps = len(steps)

        for i, step in enumerate(steps):
            try:
                log.info(f"Executing step {i + 1}/{total_steps}: {step.name}")

                if progress_callback:
                    progress_callback(
                        step=i + 1,
                        total=total_steps,
                        step_name=step.name,
                        status=f"Executing {step.name}..."
                    )

                # Execute step
                step_result = step.function(step.settings)
                results[step.name] = step_result

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

        return results
