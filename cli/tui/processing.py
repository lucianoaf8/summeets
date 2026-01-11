"""
Processing Controller for TUI.

Separates business logic from UI, providing:
- Workflow execution management
- Progress reporting interface
- Cancellation support
- Result handling
"""
import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Dict, Any, Optional, List

from src.utils.threading import CancellationToken, CancelledError
from .constants import PIPELINE_STAGES, STAGE_ID_ALIASES

log = logging.getLogger(__name__)


class ProcessingStage(Enum):
    """Processing pipeline stages."""
    IDLE = auto()
    EXTRACT_AUDIO = auto()
    PROCESS_AUDIO = auto()
    TRANSCRIBE = auto()
    SUMMARIZE = auto()
    COMPLETE = auto()
    ERROR = auto()
    CANCELLED = auto()


@dataclass
class StageProgress:
    """Progress information for a single stage."""
    stage_id: str
    stage_name: str
    status: str  # pending, active, complete, error
    progress_percent: float = 0.0
    message: str = ""
    elapsed_seconds: float = 0.0


@dataclass
class WorkflowProgress:
    """Overall workflow progress information."""
    overall_percent: float = 0.0
    current_stage: str = ""
    stage_message: str = ""
    stages: Dict[str, StageProgress] = field(default_factory=dict)


@dataclass
class WorkflowResult:
    """Result of workflow execution."""
    success: bool
    stage: str = ""
    error: Optional[str] = None
    traceback: Optional[str] = None
    results: Dict[str, Any] = field(default_factory=dict)
    elapsed_seconds: float = 0.0


# Type alias for progress callback
ProgressCallback = Callable[[WorkflowProgress], None]


class ProcessingController:
    """
    Controller for managing workflow execution.

    Provides clean interface between TUI and workflow engine,
    handling progress reporting and cancellation.
    """

    def __init__(self):
        """Initialize the processing controller."""
        self._cancellation_token: Optional[CancellationToken] = None
        self._is_running = False
        self._start_time: float = 0
        self._current_stage = ""
        self._stage_start_times: Dict[str, float] = {}
        self._progress_callback: Optional[ProgressCallback] = None

    @property
    def is_running(self) -> bool:
        """Check if a workflow is currently running."""
        return self._is_running

    @property
    def current_stage(self) -> str:
        """Get the current processing stage."""
        return self._current_stage

    def set_progress_callback(self, callback: ProgressCallback) -> None:
        """Set the progress callback for UI updates."""
        self._progress_callback = callback

    def cancel(self) -> bool:
        """
        Cancel the running workflow.

        Returns:
            True if cancellation was initiated
        """
        if self._cancellation_token:
            self._cancellation_token.cancel()
            return True
        return False

    def execute(
        self,
        input_file: Path,
        output_dir: Path,
        config: Dict[str, Any],
        progress_callback: Optional[ProgressCallback] = None
    ) -> WorkflowResult:
        """
        Execute the processing workflow.

        Args:
            input_file: Path to input file
            output_dir: Path to output directory
            config: Workflow configuration
            progress_callback: Optional progress callback

        Returns:
            WorkflowResult with success/failure info
        """
        if self._is_running:
            return WorkflowResult(
                success=False,
                error="Workflow already running"
            )

        self._is_running = True
        self._start_time = time.time()
        self._cancellation_token = CancellationToken()
        self._stage_start_times.clear()

        if progress_callback:
            self._progress_callback = progress_callback

        try:
            # Import workflow components
            from src.workflow import WorkflowConfig, execute_workflow
            from src.utils.validation import detect_file_type

            file_type = detect_file_type(input_file)

            # Build workflow config
            workflow_config = WorkflowConfig(
                input_file=input_file,
                output_dir=output_dir,
                extract_audio=(file_type == "video"),
                process_audio=(file_type in ["video", "audio"]),
                transcribe=(file_type in ["video", "audio"]),
                summarize=True,
                audio_format=config.get("audio_format", "m4a"),
                audio_quality=config.get("audio_quality", "high"),
                normalize_audio=config.get("normalize", True),
                increase_volume=config.get("increase_volume", False),
                summary_template=config.get("template", "default"),
                provider=config.get("provider", "openai"),
                model=config.get("model", "gpt-4o-mini"),
                auto_detect_template=config.get("auto_detect", True),
            )

            # Execute with progress tracking
            def internal_callback(step: int, total: int, step_name: str, status: str) -> None:
                if self._cancellation_token and self._cancellation_token.is_cancelled:
                    raise CancelledError("Workflow cancelled by user")

                self._update_progress(step, total, step_name, status)

            results = execute_workflow(workflow_config, internal_callback)

            elapsed = time.time() - self._start_time
            return WorkflowResult(
                success=True,
                results=results,
                elapsed_seconds=elapsed
            )

        except CancelledError:
            return WorkflowResult(
                success=False,
                stage=self._current_stage,
                error="Workflow cancelled by user",
                elapsed_seconds=time.time() - self._start_time
            )

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            log.error(f"Workflow error: {e}")
            return WorkflowResult(
                success=False,
                stage=self._current_stage,
                error=str(e),
                traceback=tb,
                elapsed_seconds=time.time() - self._start_time
            )

        finally:
            self._is_running = False
            self._cancellation_token = None

    def _update_progress(self, step: int, total: int, step_name: str, status: str) -> None:
        """Update progress and notify callback."""
        # Normalize stage name
        stage_id = STAGE_ID_ALIASES.get(step_name, step_name)
        self._current_stage = stage_id

        # Track stage timing
        if stage_id not in self._stage_start_times:
            self._stage_start_times[stage_id] = time.time()

        elapsed = time.time() - self._stage_start_times.get(stage_id, time.time())

        # Build progress info
        progress = WorkflowProgress(
            overall_percent=(step / total) * 100 if total > 0 else 0,
            current_stage=stage_id,
            stage_message=status
        )

        # Add stage info
        for stage_info in PIPELINE_STAGES:
            sid = stage_info["id"]
            stage_progress = StageProgress(
                stage_id=sid,
                stage_name=stage_info["name"],
                status="pending"
            )

            if sid == stage_id:
                stage_progress.status = "active"
                stage_progress.elapsed_seconds = elapsed
                stage_progress.message = status
            elif sid in self._stage_start_times:
                # Previous stage, completed
                stage_progress.status = "complete"
                stage_progress.elapsed_seconds = (
                    self._stage_start_times.get(stage_id, time.time()) -
                    self._stage_start_times[sid]
                )

            progress.stages[sid] = stage_progress

        # Notify callback
        if self._progress_callback:
            try:
                self._progress_callback(progress)
            except Exception as e:
                log.warning(f"Progress callback error: {e}")

    def get_elapsed_time(self) -> float:
        """Get elapsed time since workflow start."""
        if self._start_time:
            return time.time() - self._start_time
        return 0.0


# Data adapter for converting between core and TUI formats
class WorkflowAdapter:
    """
    Adapter for converting between core workflow data and TUI formats.

    Provides bidirectional mapping with validation.
    """

    @staticmethod
    def config_to_workflow(tui_config: Dict[str, Any]) -> Dict[str, Any]:
        """Convert TUI config to workflow config format."""
        return {
            "provider": tui_config.get("provider", "openai"),
            "model": tui_config.get("model", "gpt-4o-mini"),
            "template": tui_config.get("templates", ["default"])[0] if tui_config.get("templates") else "default",
            "auto_detect": tui_config.get("auto_detect", True),
            "chunk_seconds": tui_config.get("chunk_seconds", 1800),
            "cod_passes": tui_config.get("cod_passes", 2),
            "max_tokens": tui_config.get("max_tokens", 3000),
            "normalize": tui_config.get("normalize", True),
            "increase_volume": tui_config.get("increase_volume", False),
            "audio_format": tui_config.get("audio_format", "m4a"),
            "audio_quality": tui_config.get("audio_quality", "high"),
        }

    @staticmethod
    def result_to_tui(result: WorkflowResult) -> Dict[str, Any]:
        """Convert workflow result to TUI display format."""
        return {
            "success": result.success,
            "stage": result.stage,
            "error": result.error,
            "elapsed": f"{result.elapsed_seconds:.1f}s",
            "summary_file": result.results.get("summarize", {}).get("summary_file"),
            "transcript_file": result.results.get("transcribe", {}).get("transcript_file"),
        }

    @staticmethod
    def progress_to_tui(progress: WorkflowProgress) -> Dict[str, Any]:
        """Convert workflow progress to TUI display format."""
        stages = {}
        for stage_id, stage in progress.stages.items():
            stages[stage_id] = {
                "status": stage.status,
                "elapsed": f"{stage.elapsed_seconds:.1f}s" if stage.elapsed_seconds > 0 else "",
                "message": stage.message,
            }

        return {
            "overall_percent": progress.overall_percent,
            "current_stage": progress.current_stage,
            "message": progress.stage_message,
            "stages": stages,
        }
