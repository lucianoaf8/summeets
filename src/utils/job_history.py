"""Job history persistence.

Provides persistent storage for processing job history with
cleanup and querying capabilities.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from uuid import UUID

log = logging.getLogger(__name__)


class JobHistoryStore:
    """Persistent storage for job history.

    Stores job data as individual JSON files for durability and
    easy inspection. Supports listing, querying, and cleanup.
    """

    def __init__(self, storage_path: Path = None):
        """Initialize job history store.

        Args:
            storage_path: Directory to store job files (default: data/jobs)
        """
        self._path = storage_path or Path("data/jobs")
        self._path.mkdir(parents=True, exist_ok=True)

    @property
    def storage_path(self) -> Path:
        """Get the storage directory path."""
        return self._path

    def _job_file(self, job_id: str) -> Path:
        """Get file path for a job ID."""
        return self._path / f"{job_id}.json"

    def save_job(self, job_data: Dict[str, Any]) -> None:
        """Save job data to disk.

        Args:
            job_data: Job data dictionary (must contain 'job_id')

        Raises:
            ValueError: If job_id not in job_data
        """
        job_id = job_data.get('job_id')
        if not job_id:
            raise ValueError("job_data must contain 'job_id'")

        file_path = self._job_file(str(job_id))

        # Add timestamp if not present
        if 'saved_at' not in job_data:
            job_data['saved_at'] = datetime.now().isoformat()

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(job_data, f, indent=2, default=str)
            log.debug(f"Saved job {job_id} to {file_path}")
        except Exception as e:
            log.error(f"Failed to save job {job_id}: {e}")
            raise

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job data by ID.

        Args:
            job_id: Job ID (string or UUID)

        Returns:
            Job data dictionary or None if not found
        """
        file_path = self._job_file(str(job_id))

        if not file_path.exists():
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log.error(f"Failed to load job {job_id}: {e}")
            return None

    def update_job(self, job_id: str, updates: Dict[str, Any]) -> bool:
        """Update existing job data.

        Args:
            job_id: Job ID to update
            updates: Dictionary of fields to update

        Returns:
            True if updated, False if job not found
        """
        existing = self.get_job(job_id)
        if not existing:
            return False

        existing.update(updates)
        existing['updated_at'] = datetime.now().isoformat()
        self.save_job(existing)
        return True

    def list_jobs(
        self,
        limit: int = 100,
        status: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """List recent jobs with optional filtering.

        Args:
            limit: Maximum number of jobs to return
            status: Filter by status (e.g., 'completed', 'failed')
            since: Only return jobs created after this time

        Returns:
            List of job data dictionaries, sorted by modification time (newest first)
        """
        jobs = []

        # Get all job files sorted by modification time
        job_files = sorted(
            self._path.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        for file in job_files[:limit * 2]:  # Get extra for filtering
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    job = json.load(f)

                # Apply filters
                if status and job.get('status') != status:
                    continue

                if since:
                    created_at = job.get('created_at') or job.get('started_at')
                    if created_at:
                        try:
                            job_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            if job_time < since:
                                continue
                        except ValueError:
                            pass

                jobs.append(job)

                if len(jobs) >= limit:
                    break

            except Exception as e:
                log.warning(f"Failed to read job file {file}: {e}")

        return jobs

    def delete_job(self, job_id: str) -> bool:
        """Delete a job from history.

        Args:
            job_id: Job ID to delete

        Returns:
            True if deleted, False if not found
        """
        file_path = self._job_file(str(job_id))

        if not file_path.exists():
            return False

        try:
            file_path.unlink()
            log.debug(f"Deleted job {job_id}")
            return True
        except Exception as e:
            log.error(f"Failed to delete job {job_id}: {e}")
            return False

    def cleanup_old_jobs(self, days: int = 30) -> int:
        """Remove jobs older than specified days.

        Args:
            days: Age threshold in days

        Returns:
            Number of jobs removed
        """
        cutoff = datetime.now().timestamp() - (days * 86400)
        removed = 0

        for file in self._path.glob("*.json"):
            try:
                if file.stat().st_mtime < cutoff:
                    file.unlink()
                    removed += 1
                    log.debug(f"Cleaned up old job file: {file}")
            except Exception as e:
                log.warning(f"Failed to cleanup job file {file}: {e}")

        if removed > 0:
            log.info(f"Cleaned up {removed} old job files")

        return removed

    def get_stats(self) -> Dict[str, Any]:
        """Get job history statistics.

        Returns:
            Dictionary with counts by status and other stats
        """
        stats = {
            "total": 0,
            "by_status": {},
            "oldest": None,
            "newest": None
        }

        for file in self._path.glob("*.json"):
            stats["total"] += 1

            try:
                with open(file, 'r', encoding='utf-8') as f:
                    job = json.load(f)

                status = job.get('status', 'unknown')
                stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

                created = job.get('created_at')
                if created:
                    if stats["oldest"] is None or created < stats["oldest"]:
                        stats["oldest"] = created
                    if stats["newest"] is None or created > stats["newest"]:
                        stats["newest"] = created

            except Exception:
                pass

        return stats


# Module-level convenience functions
_default_store: Optional[JobHistoryStore] = None


def get_job_store(storage_path: Path = None) -> JobHistoryStore:
    """Get the default job history store.

    Args:
        storage_path: Optional custom storage path

    Returns:
        JobHistoryStore instance
    """
    global _default_store
    if _default_store is None or storage_path:
        _default_store = JobHistoryStore(storage_path)
    return _default_store


def record_job_start(
    job_id: str,
    input_file: Path,
    job_type: str = "workflow",
    **extra_data
) -> None:
    """Record the start of a job.

    Args:
        job_id: Unique job identifier
        input_file: Input file being processed
        job_type: Type of job (workflow, transcribe, summarize)
        **extra_data: Additional job metadata
    """
    store = get_job_store()
    store.save_job({
        "job_id": job_id,
        "job_type": job_type,
        "status": "started",
        "input_file": str(input_file),
        "started_at": datetime.now().isoformat(),
        **extra_data
    })


def record_job_complete(
    job_id: str,
    outputs: Dict[str, str] = None,
    **extra_data
) -> None:
    """Record successful job completion.

    Args:
        job_id: Job identifier
        outputs: Output file paths
        **extra_data: Additional completion data
    """
    store = get_job_store()
    store.update_job(job_id, {
        "status": "completed",
        "completed_at": datetime.now().isoformat(),
        "outputs": outputs or {},
        **extra_data
    })


def record_job_failure(
    job_id: str,
    error_message: str,
    **extra_data
) -> None:
    """Record job failure.

    Args:
        job_id: Job identifier
        error_message: Error description
        **extra_data: Additional failure data
    """
    store = get_job_store()
    store.update_job(job_id, {
        "status": "failed",
        "failed_at": datetime.now().isoformat(),
        "error_message": error_message,
        **extra_data
    })
