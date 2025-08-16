"""
Unit tests for core data models.
Tests Pydantic models, enums, and data structures.
"""
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4
from typing import Dict, Any

from core.models import (
    AudioFormat, ProcessingStatus, Provider, FileType, SummaryTemplate,
    Word, Segment, AudioMetadata, TranscriptionJob, SummarizationJob,
    ProcessingPipeline, ProcessingResults, JobManager, TranscriptData, SummaryData
)


class TestEnums:
    """Test enum definitions and values."""
    
    def test_audio_format_enum(self):
        """Test AudioFormat enum values."""
        assert AudioFormat.M4A == "m4a"
        assert AudioFormat.FLAC == "flac"
        assert AudioFormat.WAV == "wav"
        assert AudioFormat.MP3 == "mp3"
        assert AudioFormat.OGG == "ogg"
        assert AudioFormat.WEBM == "webm"
        assert AudioFormat.MKA == "mka"
        
        # Test enum membership
        assert "m4a" in AudioFormat
        assert "invalid" not in AudioFormat
    
    def test_processing_status_enum(self):
        """Test ProcessingStatus enum values."""
        assert ProcessingStatus.PENDING == "pending"
        assert ProcessingStatus.IN_PROGRESS == "in_progress"
        assert ProcessingStatus.COMPLETED == "completed"
        assert ProcessingStatus.FAILED == "failed"
        assert ProcessingStatus.CANCELLED == "cancelled"
    
    def test_provider_enum(self):
        """Test Provider enum values."""
        assert Provider.OPENAI == "openai"
        assert Provider.ANTHROPIC == "anthropic"
    
    def test_file_type_enum(self):
        """Test FileType enum values."""
        assert FileType.JSON == "json"
        assert FileType.TXT == "txt"
        assert FileType.SRT == "srt"
        assert FileType.MD == "md"
        assert FileType.CSV == "csv"
    
    def test_summary_template_enum(self):
        """Test SummaryTemplate enum values."""
        assert SummaryTemplate.DEFAULT == "default"
        assert SummaryTemplate.SOP == "sop"
        assert SummaryTemplate.DECISION == "decision"
        assert SummaryTemplate.BRAINSTORM == "brainstorm"


class TestDataClasses:
    """Test dataclass models."""
    
    def test_word_creation(self):
        """Test Word dataclass creation and validation."""
        word = Word(start=0.0, end=1.5, text="hello", confidence=0.95)
        
        assert word.start == 0.0
        assert word.end == 1.5
        assert word.text == "hello"
        assert word.confidence == 0.95
    
    def test_word_without_confidence(self):
        """Test Word creation without confidence score."""
        word = Word(start=0.0, end=1.5, text="hello")
        
        assert word.confidence is None
    
    def test_segment_creation(self):
        """Test Segment dataclass creation."""
        words = [
            Word(start=0.0, end=0.5, text="hello"),
            Word(start=0.5, end=1.0, text="world")
        ]
        
        segment = Segment(
            start=0.0,
            end=1.0,
            text="hello world",
            speaker="SPEAKER_00",
            words=words,
            confidence=0.92
        )
        
        assert segment.start == 0.0
        assert segment.end == 1.0
        assert segment.text == "hello world"
        assert segment.speaker == "SPEAKER_00"
        assert len(segment.words) == 2
        assert segment.confidence == 0.92
    
    def test_segment_minimal(self):
        """Test Segment with minimal required fields."""
        segment = Segment(start=0.0, end=1.0, text="hello")
        
        assert segment.speaker is None
        assert segment.words is None
        assert segment.confidence is None


class TestPydanticModels:
    """Test Pydantic model validation and functionality."""
    
    def test_audio_metadata_creation(self, tmp_path):
        """Test AudioMetadata model creation and validation."""
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio")
        
        metadata = AudioMetadata(
            file_path=audio_file,
            file_size_bytes=audio_file.stat().st_size,
            duration_seconds=300.5,
            sample_rate=44100,
            bit_rate=128000,
            channels=2,
            format=AudioFormat.MP3,
            codec="mp3"
        )
        
        assert metadata.file_path == audio_file
        assert metadata.file_size_bytes > 0
        assert metadata.duration_seconds == 300.5
        assert metadata.sample_rate == 44100
        assert metadata.bit_rate == 128000
        assert metadata.channels == 2
        assert metadata.format == AudioFormat.MP3
        assert metadata.codec == "mp3"
        assert isinstance(metadata.created_at, datetime)
    
    def test_audio_metadata_minimal(self, tmp_path):
        """Test AudioMetadata with minimal required fields."""
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio")
        
        metadata = AudioMetadata(
            file_path=audio_file,
            file_size_bytes=1000
        )
        
        assert metadata.file_path == audio_file
        assert metadata.file_size_bytes == 1000
        assert metadata.duration_seconds is None
        assert metadata.format is None
    
    def test_transcription_job_creation(self, tmp_path):
        """Test TranscriptionJob model creation."""
        audio_file = tmp_path / "input.mp3"
        output_dir = tmp_path / "output"
        
        job = TranscriptionJob(
            audio_file=audio_file,
            output_dir=output_dir,
            model="thomasmol/whisper-diarization"
        )
        
        assert isinstance(job.job_id, UUID)
        assert job.audio_file == audio_file
        assert job.output_dir == output_dir
        assert job.status == ProcessingStatus.PENDING
        assert job.model == "thomasmol/whisper-diarization"
        assert isinstance(job.created_at, datetime)
        assert job.started_at is None
        assert job.completed_at is None
    
    def test_transcription_job_with_custom_id(self, tmp_path):
        """Test TranscriptionJob with custom job ID."""
        custom_id = uuid4()
        
        job = TranscriptionJob(
            job_id=custom_id,
            audio_file=tmp_path / "input.mp3",
            output_dir=tmp_path / "output"
        )
        
        assert job.job_id == custom_id
    
    def test_summarization_job_creation(self, tmp_path):
        """Test SummarizationJob model creation."""
        transcript_file = tmp_path / "transcript.json"
        output_dir = tmp_path / "output"
        
        job = SummarizationJob(
            transcript_file=transcript_file,
            output_dir=output_dir,
            provider=Provider.OPENAI,
            model="gpt-4o-mini",
            template=SummaryTemplate.DECISION
        )
        
        assert isinstance(job.job_id, UUID)
        assert job.transcript_file == transcript_file
        assert job.output_dir == output_dir
        assert job.provider == Provider.OPENAI
        assert job.model == "gpt-4o-mini"
        assert job.template == SummaryTemplate.DECISION
        assert job.chunk_seconds == 1800  # default
        assert job.cod_passes == 2  # default
        assert job.max_tokens == 3000  # default
    
    def test_summarization_job_custom_settings(self, tmp_path):
        """Test SummarizationJob with custom settings."""
        job = SummarizationJob(
            transcript_file=tmp_path / "transcript.json",
            output_dir=tmp_path / "output",
            provider=Provider.ANTHROPIC,
            model="claude-3-haiku",
            chunk_seconds=900,
            cod_passes=3,
            max_tokens=4000,
            template=SummaryTemplate.SOP,
            auto_detect_template=False
        )
        
        assert job.provider == Provider.ANTHROPIC
        assert job.model == "claude-3-haiku"
        assert job.chunk_seconds == 900
        assert job.cod_passes == 3
        assert job.max_tokens == 4000
        assert job.template == SummaryTemplate.SOP
        assert job.auto_detect_template is False
    
    def test_processing_pipeline_creation(self, tmp_path):
        """Test ProcessingPipeline model creation."""
        audio_file = tmp_path / "input.mp3"
        output_dir = tmp_path / "output"
        
        pipeline = ProcessingPipeline(
            audio_file=audio_file,
            output_dir=output_dir
        )
        
        assert isinstance(pipeline.pipeline_id, UUID)
        assert pipeline.audio_file == audio_file
        assert pipeline.output_dir == output_dir
        assert pipeline.status == ProcessingStatus.PENDING
        assert isinstance(pipeline.created_at, datetime)
        assert pipeline.transcription_job is None
        assert pipeline.summarization_job is None
    
    def test_processing_results_creation(self, tmp_path):
        """Test ProcessingResults model creation."""
        job_id = uuid4()
        input_file = tmp_path / "input.mp3"
        output_dir = tmp_path / "output"
        
        results = ProcessingResults(
            job_id=job_id,
            input_file=input_file,
            output_dir=output_dir,
            processing_time_seconds=45.2,
            segments_count=25,
            speakers_count=3,
            total_duration=300.5,
            word_count=1250
        )
        
        assert results.job_id == job_id
        assert results.input_file == input_file
        assert results.output_dir == output_dir
        assert results.processing_time_seconds == 45.2
        assert results.segments_count == 25
        assert results.speakers_count == 3
        assert results.total_duration == 300.5
        assert results.word_count == 1250


class TestJobManager:
    """Test JobManager functionality."""
    
    def test_job_manager_creation(self):
        """Test JobManager creation."""
        manager = JobManager()
        
        assert len(manager.jobs) == 0
        assert len(manager.completed_jobs) == 0
        assert len(manager.failed_jobs) == 0
    
    def test_add_transcription_job(self, tmp_path):
        """Test adding transcription job to manager."""
        manager = JobManager()
        
        job = TranscriptionJob(
            audio_file=tmp_path / "input.mp3",
            output_dir=tmp_path / "output"
        )
        
        job_id = manager.add_job(job)
        
        assert job_id == job.job_id
        assert job_id in manager.jobs
        assert manager.jobs[job_id] == job
    
    def test_add_summarization_job(self, tmp_path):
        """Test adding summarization job to manager."""
        manager = JobManager()
        
        job = SummarizationJob(
            transcript_file=tmp_path / "transcript.json",
            output_dir=tmp_path / "output"
        )
        
        job_id = manager.add_job(job)
        
        assert job_id == job.job_id
        assert job_id in manager.jobs
    
    def test_get_job(self, tmp_path):
        """Test retrieving job from manager."""
        manager = JobManager()
        
        job = TranscriptionJob(
            audio_file=tmp_path / "input.mp3",
            output_dir=tmp_path / "output"
        )
        
        job_id = manager.add_job(job)
        retrieved_job = manager.get_job(job_id)
        
        assert retrieved_job == job
    
    def test_get_nonexistent_job(self):
        """Test retrieving nonexistent job."""
        manager = JobManager()
        
        nonexistent_id = uuid4()
        retrieved_job = manager.get_job(nonexistent_id)
        
        assert retrieved_job is None
    
    def test_update_job_status_completed(self, tmp_path):
        """Test updating job status to completed."""
        manager = JobManager()
        
        job = TranscriptionJob(
            audio_file=tmp_path / "input.mp3",
            output_dir=tmp_path / "output"
        )
        
        job_id = manager.add_job(job)
        
        # Update to completed
        manager.update_job_status(job_id, ProcessingStatus.COMPLETED)
        
        updated_job = manager.get_job(job_id)
        assert updated_job.status == ProcessingStatus.COMPLETED
        assert updated_job.completed_at is not None
        assert job_id in manager.completed_jobs
    
    def test_update_job_status_failed(self, tmp_path):
        """Test updating job status to failed."""
        manager = JobManager()
        
        job = TranscriptionJob(
            audio_file=tmp_path / "input.mp3",
            output_dir=tmp_path / "output"
        )
        
        job_id = manager.add_job(job)
        error_message = "Transcription failed due to invalid audio format"
        
        # Update to failed
        manager.update_job_status(job_id, ProcessingStatus.FAILED, error_message)
        
        updated_job = manager.get_job(job_id)
        assert updated_job.status == ProcessingStatus.FAILED
        assert updated_job.error_message == error_message
        assert job_id in manager.failed_jobs
    
    def test_get_active_jobs(self, tmp_path):
        """Test retrieving active jobs."""
        manager = JobManager()
        
        # Add jobs with different statuses
        pending_job = TranscriptionJob(
            audio_file=tmp_path / "input1.mp3",
            output_dir=tmp_path / "output"
        )
        
        in_progress_job = SummarizationJob(
            transcript_file=tmp_path / "transcript.json",
            output_dir=tmp_path / "output"
        )
        in_progress_job.status = ProcessingStatus.IN_PROGRESS
        
        completed_job = TranscriptionJob(
            audio_file=tmp_path / "input2.mp3",
            output_dir=tmp_path / "output"
        )
        completed_job.status = ProcessingStatus.COMPLETED
        
        manager.add_job(pending_job)
        manager.add_job(in_progress_job)
        manager.add_job(completed_job)
        
        active_jobs = manager.get_active_jobs()
        
        assert len(active_jobs) == 2
        assert pending_job in active_jobs
        assert in_progress_job in active_jobs
        assert completed_job not in active_jobs
    
    def test_cleanup_old_jobs(self, tmp_path):
        """Test cleaning up old completed jobs."""
        manager = JobManager()
        
        # Create old completed job
        old_job = TranscriptionJob(
            audio_file=tmp_path / "old_input.mp3",
            output_dir=tmp_path / "output"
        )
        old_job.status = ProcessingStatus.COMPLETED
        old_job.created_at = datetime.now() - timedelta(days=10)
        
        # Create recent job
        recent_job = TranscriptionJob(
            audio_file=tmp_path / "recent_input.mp3",
            output_dir=tmp_path / "output"
        )
        
        old_job_id = manager.add_job(old_job)
        recent_job_id = manager.add_job(recent_job)
        
        # Add to completed list
        manager.completed_jobs.append(old_job_id)
        
        # Cleanup jobs older than 7 days
        manager.cleanup_old_jobs(days=7)
        
        # Old job should be removed
        assert old_job_id not in manager.jobs
        assert old_job_id not in manager.completed_jobs
        
        # Recent job should remain
        assert recent_job_id in manager.jobs


class TestLegacyModels:
    """Test legacy dataclass models."""
    
    def test_transcript_data_creation(self, tmp_path):
        """Test TranscriptData creation."""
        segments = [
            Segment(start=0.0, end=5.0, text="Hello world", speaker="SPEAKER_00")
        ]
        
        output_file = tmp_path / "transcript.json"
        metadata = {"model": "whisper", "language": "en"}
        
        transcript_data = TranscriptData(
            segments=segments,
            duration=300.0,
            output_file=output_file,
            metadata=metadata
        )
        
        assert len(transcript_data.segments) == 1
        assert transcript_data.duration == 300.0
        assert transcript_data.output_file == output_file
        assert transcript_data.metadata == metadata
    
    def test_summary_data_creation(self, tmp_path):
        """Test SummaryData creation."""
        content = "This is a meeting summary."
        output_file = tmp_path / "summary.md"
        metadata = {"provider": "openai", "model": "gpt-4o-mini"}
        chunk_summaries = ["Chunk 1 summary", "Chunk 2 summary"]
        
        summary_data = SummaryData(
            content=content,
            output_file=output_file,
            metadata=metadata,
            chunk_summaries=chunk_summaries
        )
        
        assert summary_data.content == content
        assert summary_data.output_file == output_file
        assert summary_data.metadata == metadata
        assert len(summary_data.chunk_summaries) == 2


class TestModelValidation:
    """Test model validation and error handling."""
    
    def test_invalid_enum_values(self, tmp_path):
        """Test validation with invalid enum values."""
        with pytest.raises(ValueError):
            TranscriptionJob(
                audio_file=tmp_path / "input.mp3",
                output_dir=tmp_path / "output",
                status="invalid_status"  # Should fail validation
            )
    
    def test_required_fields_validation(self):
        """Test validation of required fields."""
        with pytest.raises(ValueError):
            AudioMetadata()  # Missing required fields
    
    def test_path_validation(self, tmp_path):
        """Test Path field validation."""
        # Valid path
        metadata = AudioMetadata(
            file_path=tmp_path / "test.mp3",
            file_size_bytes=1000
        )
        assert isinstance(metadata.file_path, Path)
        
        # String path should be converted to Path
        metadata_str = AudioMetadata(
            file_path=str(tmp_path / "test.mp3"),
            file_size_bytes=1000
        )
        assert isinstance(metadata_str.file_path, Path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])