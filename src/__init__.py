"""summeets_core - Shared processing core for audio transcription and summarization."""

__version__ = "0.1.0"

# Export main workflow functionality
from .workflow import WorkflowConfig, WorkflowEngine, execute_workflow

__all__ = [
    "WorkflowConfig",
    "WorkflowEngine", 
    "execute_workflow"
]