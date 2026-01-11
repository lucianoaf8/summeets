"""Data models for summeets transcription and summarization."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict


class AudioFormat(str, Enum):
    """Supported audio formats."""
    M4A = "m4a"
    FLAC = "flac"
    WAV = "wav"
    MKA = "mka"
    OGG = "ogg"
    MP3 = "mp3"
    WEBM = "webm"


class ProcessingStatus(str, Enum):
    """Processing status for files and jobs."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Provider(str, Enum):
    """LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class FileType(str, Enum):
    """Output file types."""
    JSON = "json"
    TXT = "txt"
    SRT = "srt"
    MD = "md"
    CSV = "csv"


class InputFileType(str, Enum):
    """Input file types for workflow processing."""
    VIDEO = "video"
    AUDIO = "audio"
    TRANSCRIPT = "transcript"
    UNKNOWN = "unknown"


class SummaryTemplate(str, Enum):
    """Summary template types."""
    DEFAULT = "default"
    SOP = "sop"
    DECISION = "decision"
    BRAINSTORM = "brainstorm"
    REQUIREMENTS = "requirements"


@dataclass
class Word:
    """Individual word with timing information."""
    start: float
    end: float
    text: str
    confidence: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "start": self.start,
            "end": self.end,
            "text": self.text
        }
        if self.confidence is not None:
            result["confidence"] = self.confidence
        return result


@dataclass
class Segment:
    """Text segment with speaker attribution and word-level timing."""
    start: float
    end: float
    text: str
    speaker: Optional[str] = None
    words: Optional[List[Word]] = None
    confidence: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "start": self.start,
            "end": self.end,
            "text": self.text,
            "speaker": self.speaker,
            "words": [w.to_dict() for w in (self.words or [])]
        }
        if self.confidence is not None:
            result["confidence"] = self.confidence
        return result


class AudioMetadata(BaseModel):
    """Audio file metadata."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    file_path: Path
    file_size_bytes: int
    duration_seconds: Optional[float] = None
    sample_rate: Optional[int] = None
    bit_rate: Optional[int] = None
    channels: Optional[int] = None
    format: Optional[AudioFormat] = None
    codec: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)


class TranscriptionJob(BaseModel):
    """Transcription job tracking."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    job_id: UUID = Field(default_factory=uuid4)
    audio_file: Path
    output_dir: Path
    status: ProcessingStatus = ProcessingStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    # Processing settings
    model: str = "thomasmol/whisper-diarization"
    model_version: Optional[str] = None
    
    # Results
    segments: Optional[List[Dict]] = None
    metadata: Optional[AudioMetadata] = None
    output_files: Dict[FileType, Path] = Field(default_factory=dict)


class SummarizationJob(BaseModel):
    """Summarization job tracking."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    job_id: UUID = Field(default_factory=uuid4)
    transcript_file: Path
    output_dir: Path
    status: ProcessingStatus = ProcessingStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    # Processing settings
    provider: Provider = Provider.OPENAI
    model: str = "gpt-4o-mini"
    chunk_seconds: int = 1800
    cod_passes: int = 2
    max_tokens: int = 3000
    template: SummaryTemplate = SummaryTemplate.DEFAULT
    auto_detect_template: bool = True
    
    # Results
    summary: Optional[str] = None
    chunk_summaries: Optional[List[str]] = None
    detected_template: Optional[SummaryTemplate] = None
    output_files: Dict[FileType, Path] = Field(default_factory=dict)


class ProcessingPipeline(BaseModel):
    """Complete processing pipeline job."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    pipeline_id: UUID = Field(default_factory=uuid4)
    audio_file: Path
    output_dir: Path
    status: ProcessingStatus = ProcessingStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    # Sub-jobs
    transcription_job: Optional[TranscriptionJob] = None
    summarization_job: Optional[SummarizationJob] = None
    
    # Final outputs
    outputs: Dict[str, Path] = Field(default_factory=dict)


class ProcessingResults(BaseModel):
    """Results from processing operations."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    job_id: UUID
    input_file: Path
    output_dir: Path
    processing_time_seconds: float
    created_at: datetime = Field(default_factory=datetime.now)
    
    # File outputs
    transcript_json: Optional[Path] = None
    transcript_txt: Optional[Path] = None
    transcript_srt: Optional[Path] = None
    summary_json: Optional[Path] = None
    summary_md: Optional[Path] = None
    audio_metadata: Optional[AudioMetadata] = None
    
    # Statistics
    segments_count: Optional[int] = None
    speakers_count: Optional[int] = None
    total_duration: Optional[float] = None
    word_count: Optional[int] = None


class JobManager(BaseModel):
    """Manages job state and history."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    jobs: Dict[UUID, Union[TranscriptionJob, SummarizationJob, ProcessingPipeline]] = Field(default_factory=dict)
    completed_jobs: List[UUID] = Field(default_factory=list)
    failed_jobs: List[UUID] = Field(default_factory=list)
    
    def add_job(self, job: Union[TranscriptionJob, SummarizationJob, ProcessingPipeline]) -> UUID:
        """Add a new job to the manager."""
        self.jobs[job.job_id] = job
        return job.job_id
    
    def get_job(self, job_id: UUID) -> Optional[Union[TranscriptionJob, SummarizationJob, ProcessingPipeline]]:
        """Get a job by ID."""
        return self.jobs.get(job_id)
    
    def update_job_status(self, job_id: UUID, status: ProcessingStatus, error_message: Optional[str] = None):
        """Update job status."""
        if job_id in self.jobs:
            self.jobs[job_id].status = status
            if error_message:
                self.jobs[job_id].error_message = error_message
            if status == ProcessingStatus.COMPLETED:
                self.jobs[job_id].completed_at = datetime.now()
                self.completed_jobs.append(job_id)
            elif status == ProcessingStatus.FAILED:
                self.failed_jobs.append(job_id)
    
    def get_active_jobs(self) -> List[Union[TranscriptionJob, SummarizationJob, ProcessingPipeline]]:
        """Get all active (non-completed, non-failed) jobs."""
        return [
            job for job in self.jobs.values()
            if job.status in [ProcessingStatus.PENDING, ProcessingStatus.IN_PROGRESS]
        ]
    
    def cleanup_old_jobs(self, days: int = 7):
        """Clean up jobs older than specified days."""
        cutoff = datetime.now() - timedelta(days=days)
        to_remove = [
            job_id for job_id, job in self.jobs.items()
            if job.created_at < cutoff and job.status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED]
        ]
        for job_id in to_remove:
            del self.jobs[job_id]
            if job_id in self.completed_jobs:
                self.completed_jobs.remove(job_id)
            if job_id in self.failed_jobs:
                self.failed_jobs.remove(job_id)


@dataclass
class TranscriptData:
    """Complete transcript data with segments and metadata."""
    segments: List[Segment]
    duration: float
    output_file: Optional[Path] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass 
class SummaryData:
    """Summary data with content and metadata."""
    content: str
    output_file: Optional[Path] = None
    metadata: Optional[Dict[str, Any]] = None
    chunk_summaries: Optional[List[str]] = None


