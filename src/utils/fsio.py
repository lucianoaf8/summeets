"""File system I/O operations with safe writes and data organization."""
import json
import shutil
import tempfile
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from ..models import (
    ProcessingResults, TranscriptionJob, SummarizationJob, 
    ProcessingPipeline, AudioMetadata, FileType
)

log = logging.getLogger(__name__)


class DataManager:
    """Manages data organization and file operations."""
    
    def __init__(self, base_dir: Path = None):
        self.base_dir = base_dir or Path("data")
        self.video_dir = self.base_dir / "video"
        self.audio_dir = self.base_dir / "audio"
        self.transcript_dir = self.base_dir / "transcript"
        self.temp_dir = self.base_dir / "temp"
        self.jobs_dir = self.base_dir / "jobs"
        
        # Legacy directories (kept as properties but not created)
        self.input_dir = self.base_dir / "input"
        self.output_dir = self.base_dir / "output"
        
        # Create only the directories that are actively used
        for dir_path in [self.video_dir, self.audio_dir, self.transcript_dir, 
                        self.temp_dir, self.jobs_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def organize_input_file(self, file_path: Path) -> Path:
        """Move input file to organized input directory."""
        if not file_path.exists():
            raise FileNotFoundError(f"Input file not found: {file_path}")
        
        # Create input directory on-demand if this method is called
        self.input_dir.mkdir(parents=True, exist_ok=True)
        
        # Create dated subdirectory
        date_dir = self.input_dir / datetime.now().strftime("%Y-%m-%d")
        date_dir.mkdir(exist_ok=True)
        
        # Generate unique filename if needed
        target = date_dir / file_path.name
        if target.exists():
            stem = file_path.stem
            suffix = file_path.suffix
            counter = 1
            while target.exists():
                target = date_dir / f"{stem}_{counter}{suffix}"
                counter += 1
        
        shutil.copy2(file_path, target)
        log.info(f"Organized input file: {target}")
        return target
    
    def create_job_output_dir(self, job_id: UUID, job_type: str) -> Path:
        """Create organized output directory for a job."""
        # Create output directory on-demand if this method is called
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        date_dir = self.output_dir / datetime.now().strftime("%Y-%m-%d")
        job_dir = date_dir / job_type / str(job_id)[:8]  # Use short ID for readability
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir
    
    def create_file_processing_dirs(self, base_name: str) -> Dict[str, Path]:
        """Create subdirectories for a processed file in the new structure."""
        safe_name = safe_filename(base_name)
        
        # Create subdirectory for this file in each category
        audio_subdir = self.audio_dir / safe_name
        transcript_subdir = self.transcript_dir / safe_name
        
        audio_subdir.mkdir(parents=True, exist_ok=True)
        transcript_subdir.mkdir(parents=True, exist_ok=True)
        
        return {
            "audio": audio_subdir,
            "transcript": transcript_subdir
        }
    
    def get_video_path(self, filename: str) -> Path:
        """Get video file path in the video directory."""
        return self.video_dir / filename
    
    def get_audio_path(self, base_name: str, audio_format: str = "m4a") -> Path:
        """Get audio file path with subfolder structure."""
        safe_name = safe_filename(base_name)
        audio_subdir = self.audio_dir / safe_name
        audio_subdir.mkdir(parents=True, exist_ok=True)
        return audio_subdir / f"{safe_name}.{audio_format}"
    
    def get_transcript_path(self, base_name: str, transcript_format: str = "json") -> Path:
        """Get transcript file path with subfolder structure."""
        safe_name = safe_filename(base_name)
        transcript_subdir = self.transcript_dir / safe_name
        transcript_subdir.mkdir(parents=True, exist_ok=True)
        return transcript_subdir / f"{safe_name}.{transcript_format}"
    
    def create_temp_file(self, suffix: str = "", prefix: str = "summeets_") -> Path:
        """Create a temporary file that will be cleaned up."""
        fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=self.temp_dir)
        import os
        os.close(fd)  # Close the file descriptor
        os.chmod(temp_path, 0o600)  # Restrict permissions
        return Path(temp_path)
    
    def atomic_write(self, file_path: Path, content: Union[str, Dict, List], encoding: str = "utf-8"):
        """Atomically write content to file using temporary file and move."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to temporary file first
        temp_path = self.create_temp_file(suffix=file_path.suffix)
        
        try:
            if isinstance(content, (dict, list)):
                with open(temp_path, 'w', encoding=encoding) as f:
                    json.dump(content, f, indent=2, ensure_ascii=False, default=str)
            else:
                with open(temp_path, 'w', encoding=encoding) as f:
                    f.write(content)
            
            # Atomic move
            shutil.move(temp_path, file_path)
            log.debug(f"Atomically wrote file: {file_path}")
            
        except Exception as e:
            # Cleanup temp file on error
            if temp_path.exists():
                temp_path.unlink()
            raise e
    
    def save_job_state(self, job: Union[TranscriptionJob, SummarizationJob, ProcessingPipeline]):
        """Save job state to disk."""
        job_file = self.jobs_dir / f"{job.job_id}.json"
        self.atomic_write(job_file, job.model_dump(mode='json'))
    
    def load_job_state(self, job_id: UUID) -> Optional[Dict]:
        """Load job state from disk."""
        job_file = self.jobs_dir / f"{job_id}.json"
        if not job_file.exists():
            return None
        
        try:
            with open(job_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log.error(f"Failed to load job state {job_id}: {e}")
            return None
    
    def cleanup_temp_files(self, max_age_hours: int = 24):
        """Clean up old temporary files."""
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        
        for temp_file in self.temp_dir.glob("*"):
            if temp_file.is_file() and temp_file.stat().st_mtime < cutoff_time:
                try:
                    temp_file.unlink()
                    log.debug(f"Cleaned up temp file: {temp_file}")
                except Exception as e:
                    log.warning(f"Failed to clean temp file {temp_file}: {e}")
    
    def create_processing_manifest(self, results: ProcessingResults) -> Path:
        """Create a processing manifest file with all outputs."""
        manifest = {
            "job_id": str(results.job_id),
            "input_file": str(results.input_file),
            "processing_time": results.processing_time_seconds,
            "created_at": results.created_at.isoformat(),
            "outputs": {},
            "statistics": {
                "segments_count": results.segments_count,
                "speakers_count": results.speakers_count, 
                "total_duration": results.total_duration,
                "word_count": results.word_count
            }
        }
        
        # Add output files
        for attr in ["transcript_json", "transcript_txt", "transcript_srt", "summary_json", "summary_md"]:
            path = getattr(results, attr)
            if path:
                manifest["outputs"][attr] = str(path)
        
        manifest_path = results.output_dir / "manifest.json"
        self.atomic_write(manifest_path, manifest)
        return manifest_path


def safe_filename(name: str, max_length: int = 200) -> str:
    """Create a safe filename from arbitrary text."""
    import re
    # Remove or replace problematic characters
    safe = re.sub(r'[<>:"/\\|?*]', '_', name)
    # Remove control characters
    safe = ''.join(c for c in safe if ord(c) >= 32)
    # Trim whitespace and dots (Windows doesn't like trailing dots)
    safe = safe.strip('. ')
    # Truncate if too long
    if len(safe) > max_length:
        safe = safe[:max_length].rstrip('. ')
    # Ensure not empty
    if not safe:
        safe = "unnamed"
    return safe


def ensure_directory(path: Path) -> Path:
    """Ensure directory exists, creating it if necessary."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_file_size_mb(path: Path) -> float:
    """Get file size in megabytes."""
    return path.stat().st_size / (1024 * 1024)


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def create_output_filename(base_name: str, job_type: str, file_type: FileType, timestamp: bool = True) -> str:
    """Create standardized output filename."""
    safe_base = safe_filename(base_name)
    
    if timestamp:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{safe_base}_{job_type}_{ts}.{file_type.value}"
    else:
        return f"{safe_base}_{job_type}.{file_type.value}"


# Global data manager instance
_data_manager: Optional[DataManager] = None


def get_data_manager(base_dir: Path = None) -> DataManager:
    """Get or create the global data manager instance.

    Raises ValueError if called with a different base_dir than the
    existing instance to prevent silent misconfiguration.
    """
    global _data_manager
    if _data_manager is None:
        _data_manager = DataManager(base_dir)
    elif base_dir is not None and _data_manager.base_dir != base_dir:
        raise ValueError(
            f"DataManager already initialised with base_dir={_data_manager.base_dir}; "
            f"requested base_dir={base_dir}. Call reset_data_manager() first."
        )
    return _data_manager


def reset_data_manager() -> None:
    """Reset the global data manager (useful for testing)."""
    global _data_manager
    _data_manager = None