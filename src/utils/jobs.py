"""Job management and processing coordination."""
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
import json

from .models import (
    TranscriptionJob, SummarizationJob, ProcessingPipeline,
    ProcessingStatus, JobManager, ProcessingResults
)
from .fsio import get_data_manager, DataManager
from .config import SETTINGS

log = logging.getLogger(__name__)


class JobProcessor:
    """Handles job processing and coordination."""
    
    def __init__(self, data_manager: DataManager = None):
        self.data_manager = data_manager or get_data_manager()
        self.job_manager = JobManager()
        self.active_jobs: Dict[UUID, asyncio.Task] = {}
        self._load_jobs()
    
    def _load_jobs(self):
        """Load existing jobs from disk."""
        if not self.data_manager.jobs_dir.exists():
            return
        
        for job_file in self.data_manager.jobs_dir.glob("*.json"):
            try:
                job_data = self.data_manager.load_job_state(UUID(job_file.stem))
                if job_data:
                    # Reconstruct job objects based on type
                    if job_data.get("transcription_job"):
                        job = ProcessingPipeline(**job_data)
                    elif "transcript_file" in job_data:
                        job = SummarizationJob(**job_data)
                    else:
                        job = TranscriptionJob(**job_data)
                    
                    self.job_manager.add_job(job)
                    log.debug(f"Loaded job {job.job_id}")
            except Exception as e:
                log.warning(f"Failed to load job from {job_file}: {e}")
    
    def create_transcription_job(self, audio_file: Path, output_dir: Path = None) -> TranscriptionJob:
        """Create a new transcription job."""
        output_dir = output_dir or self.data_manager.create_job_output_dir(
            uuid4(), "transcription"
        )
        
        job = TranscriptionJob(
            audio_file=audio_file,
            output_dir=output_dir,
            model=SETTINGS.replicate_model if hasattr(SETTINGS, 'replicate_model') else "thomasmol/whisper-diarization"
        )
        
        self.job_manager.add_job(job)
        self.data_manager.save_job_state(job)
        log.info(f"Created transcription job {job.job_id}")
        return job
    
    def create_summarization_job(self, transcript_file: Path, output_dir: Path = None) -> SummarizationJob:
        """Create a new summarization job."""
        output_dir = output_dir or self.data_manager.create_job_output_dir(
            uuid4(), "summarization"
        )
        
        job = SummarizationJob(
            transcript_file=transcript_file,
            output_dir=output_dir,
            provider=SETTINGS.provider,
            model=SETTINGS.model,
            chunk_seconds=SETTINGS.summary_chunk_seconds,
            cod_passes=SETTINGS.summary_cod_passes,
            max_tokens=SETTINGS.summary_max_tokens
        )
        
        self.job_manager.add_job(job)
        self.data_manager.save_job_state(job)
        log.info(f"Created summarization job {job.job_id}")
        return job
    
    def create_pipeline_job(self, audio_file: Path, output_dir: Path = None) -> ProcessingPipeline:
        """Create a complete pipeline job."""
        output_dir = output_dir or self.data_manager.create_job_output_dir(
            uuid4(), "pipeline"
        )
        
        job = ProcessingPipeline(
            audio_file=audio_file,
            output_dir=output_dir
        )
        
        self.job_manager.add_job(job)
        self.data_manager.save_job_state(job)
        log.info(f"Created pipeline job {job.pipeline_id}")
        return job
    
    async def process_job(self, job_id: UUID) -> ProcessingResults:
        """Process a job asynchronously."""
        job = self.job_manager.get_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        if job.status != ProcessingStatus.PENDING:
            raise ValueError(f"Job {job_id} is not in pending status")
        
        try:
            # Update job status
            self.job_manager.update_job_status(job_id, ProcessingStatus.IN_PROGRESS)
            job.started_at = datetime.now()
            self.data_manager.save_job_state(job)
            
            # Process based on job type
            if isinstance(job, TranscriptionJob):
                results = await self._process_transcription_job(job)
            elif isinstance(job, SummarizationJob):
                results = await self._process_summarization_job(job)
            elif isinstance(job, ProcessingPipeline):
                results = await self._process_pipeline_job(job)
            else:
                raise ValueError(f"Unknown job type: {type(job)}")
            
            # Mark as completed
            self.job_manager.update_job_status(job_id, ProcessingStatus.COMPLETED)
            self.data_manager.save_job_state(job)
            
            return results
            
        except Exception as e:
            log.error(f"Job {job_id} failed: {e}")
            self.job_manager.update_job_status(job_id, ProcessingStatus.FAILED, str(e))
            self.data_manager.save_job_state(job)
            raise
    
    async def _process_transcription_job(self, job: TranscriptionJob) -> ProcessingResults:
        """Process a transcription job."""
        from .transcribe.pipeline import run as transcribe_run
        
        log.info(f"Processing transcription job {job.job_id}")
        start_time = datetime.now()
        
        # Run transcription
        result_file = await asyncio.to_thread(
            transcribe_run, 
            audio_path=job.audio_file,
            output_dir=job.output_dir
        )
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Create results object
        results = ProcessingResults(
            job_id=job.job_id,
            input_file=job.audio_file,
            output_dir=job.output_dir,
            processing_time_seconds=processing_time,
            transcript_json=result_file
        )
        
        # Create manifest
        self.data_manager.create_processing_manifest(results)
        
        return results
    
    async def _process_summarization_job(self, job: SummarizationJob) -> ProcessingResults:
        """Process a summarization job."""
        from .summarize.pipeline import run as summarize_run
        
        log.info(f"Processing summarization job {job.job_id}")
        start_time = datetime.now()
        
        # Run summarization
        result_file = await asyncio.to_thread(
            summarize_run,
            transcript_path=job.transcript_file,
            provider=job.provider,
            model=job.model,
            chunk_seconds=job.chunk_seconds,
            cod_passes=job.cod_passes,
            output_dir=job.output_dir
        )
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Create results object
        results = ProcessingResults(
            job_id=job.job_id,
            input_file=job.transcript_file,
            output_dir=job.output_dir,
            processing_time_seconds=processing_time,
            summary_json=result_file,
            summary_md=job.output_dir / f"{job.transcript_file.stem}.summary.md"
        )
        
        # Create manifest
        self.data_manager.create_processing_manifest(results)
        
        return results
    
    async def _process_pipeline_job(self, job: ProcessingPipeline) -> ProcessingResults:
        """Process a complete pipeline job."""
        log.info(f"Processing pipeline job {job.pipeline_id}")
        start_time = datetime.now()
        
        # Create and process transcription job
        transcription_job = self.create_transcription_job(
            job.audio_file, 
            job.output_dir / "transcription"
        )
        job.transcription_job = transcription_job
        
        transcription_results = await self.process_job(transcription_job.job_id)
        
        # Create and process summarization job
        summarization_job = self.create_summarization_job(
            transcription_results.transcript_json,
            job.output_dir / "summarization"
        )
        job.summarization_job = summarization_job
        
        summarization_results = await self.process_job(summarization_job.job_id)
        
        # Calculate total processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Create combined results
        results = ProcessingResults(
            job_id=job.pipeline_id,
            input_file=job.audio_file,
            output_dir=job.output_dir,
            processing_time_seconds=processing_time,
            transcript_json=transcription_results.transcript_json,
            summary_json=summarization_results.summary_json,
            summary_md=summarization_results.summary_md
        )
        
        # Create manifest
        self.data_manager.create_processing_manifest(results)
        
        return results
    
    def get_job_status(self, job_id: UUID) -> Optional[Dict[str, Any]]:
        """Get job status information."""
        job = self.job_manager.get_job(job_id)
        if not job:
            return None
        
        return {
            "job_id": str(job.job_id),
            "status": job.status,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "error_message": job.error_message,
            "type": type(job).__name__
        }
    
    def list_jobs(self, status: ProcessingStatus = None) -> List[Dict[str, Any]]:
        """List all jobs, optionally filtered by status."""
        jobs = []
        for job in self.job_manager.jobs.values():
            if status is None or job.status == status:
                jobs.append(self.get_job_status(job.job_id))
        
        return sorted(jobs, key=lambda x: x["created_at"], reverse=True)
    
    def cleanup(self):
        """Clean up old jobs and temporary files."""
        self.job_manager.cleanup_old_jobs(SETTINGS.job_history_days)
        self.data_manager.cleanup_temp_files(SETTINGS.temp_cleanup_hours)


# Global job processor instance
_job_processor: Optional[JobProcessor] = None

def get_job_processor() -> JobProcessor:
    """Get global job processor instance."""
    global _job_processor
    if _job_processor is None:
        _job_processor = JobProcessor()
    return _job_processor