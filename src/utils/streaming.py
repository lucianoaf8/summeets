"""Streaming utilities for large file handling.

Provides memory-efficient processing for large audio files and transcripts
to prevent memory exhaustion when processing long meetings.

Classes:
    StreamingReader: Line-by-line file reader
    ChunkedProcessor: Process data in memory-efficient chunks

Functions:
    load_json_array: Load and iterate over JSON arrays
    estimate_memory_usage: Estimate memory for processing
"""
import json
import logging
from pathlib import Path
from typing import Iterator, Dict, Any, List, Callable, Optional
import mmap
import gc

log = logging.getLogger(__name__)

# Memory thresholds
DEFAULT_CHUNK_SIZE = 1000  # segments per chunk
MAX_MEMORY_MB = 512  # trigger warning above this


def estimate_memory_usage(file_path: Path) -> float:
    """Estimate memory needed to process file.

    Args:
        file_path: Path to file

    Returns:
        Estimated memory in MB (rough approximation)
    """
    file_size_mb = file_path.stat().st_size / (1024 * 1024)

    # JSON files typically expand 2-3x in memory
    if file_path.suffix.lower() == '.json':
        return file_size_mb * 2.5

    # Text files are roughly 1:1
    return file_size_mb


def load_json_array(file_path: Path) -> Iterator[Dict[str, Any]]:
    """Load a JSON file and yield its array elements.

    Despite the iterator return type, the entire file is read into memory.
    Use ChunkedProcessor for true streaming on very large files.

    Args:
        file_path: Path to JSON file containing array

    Yields:
        Individual array elements

    Note:
        Only works with JSON files containing a root array.
        For nested structures, use standard json.load().
    """
    log.debug(f"Loading JSON array from {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    try:
        data = json.loads(content)
        if isinstance(data, list):
            for item in data:
                yield item
        elif isinstance(data, dict) and 'segments' in data:
            for item in data['segments']:
                yield item
        else:
            yield data
    except json.JSONDecodeError as e:
        log.error(f"Failed to parse JSON: {e}")
        raise


# Backward-compatible alias
stream_json_array = load_json_array


class ChunkedProcessor:
    """Process data in memory-efficient chunks.

    Example:
        processor = ChunkedProcessor(chunk_size=500)
        for chunk in processor.process(segments, summarize_chunk):
            results.append(chunk)
    """

    def __init__(self, chunk_size: int = DEFAULT_CHUNK_SIZE):
        """Initialize processor.

        Args:
            chunk_size: Number of items per chunk
        """
        self.chunk_size = chunk_size
        self.processed_count = 0

    def chunk_iterator(self, items: List[Any]) -> Iterator[List[Any]]:
        """Yield chunks of items.

        Args:
            items: List to chunk

        Yields:
            Chunks of specified size
        """
        for i in range(0, len(items), self.chunk_size):
            chunk = items[i:i + self.chunk_size]
            yield chunk
            self.processed_count += len(chunk)
            log.debug(f"Processed {self.processed_count} items")

    def process(
        self,
        items: List[Any],
        processor_fn: Callable[[List[Any]], Any],
        cleanup_between: bool = True
    ) -> Iterator[Any]:
        """Process items in chunks with optional memory cleanup.

        Args:
            items: Items to process
            processor_fn: Function to apply to each chunk
            cleanup_between: Whether to force GC between chunks

        Yields:
            Results from each chunk
        """
        for chunk in self.chunk_iterator(items):
            result = processor_fn(chunk)
            yield result

            if cleanup_between:
                gc.collect()


class StreamingReader:
    """Memory-mapped file reader for large files.

    Provides efficient reading without loading entire file into memory.
    """

    def __init__(self, file_path: Path):
        """Initialize reader.

        Args:
            file_path: Path to file
        """
        self.file_path = file_path
        self._file = None
        self._mmap = None

    def __enter__(self):
        """Open file for memory-mapped reading."""
        self._file = open(self.file_path, 'rb')
        self._mmap = mmap.mmap(
            self._file.fileno(),
            0,
            access=mmap.ACCESS_READ
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close file and mapping."""
        if self._mmap:
            self._mmap.close()
        if self._file:
            self._file.close()

    def read_lines(self) -> Iterator[str]:
        """Yield lines from file.

        Yields:
            Decoded lines
        """
        if not self._mmap:
            raise RuntimeError("Reader not opened. Use 'with' statement.")

        for line in iter(self._mmap.readline, b''):
            yield line.decode('utf-8').rstrip('\n\r')

    def search(self, pattern: bytes) -> Optional[int]:
        """Find pattern in file.

        Args:
            pattern: Bytes to search for

        Returns:
            Position or None if not found
        """
        if not self._mmap:
            raise RuntimeError("Reader not opened. Use 'with' statement.")

        return self._mmap.find(pattern)


def check_memory_pressure() -> bool:
    """Check if system is under memory pressure.

    Returns:
        True if memory usage is concerning
    """
    try:
        import psutil
        memory = psutil.virtual_memory()
        percent_used = memory.percent
        return percent_used > 85
    except ImportError:
        # psutil not available, assume OK
        return False


def process_large_transcript(
    file_path: Path,
    processor: Callable[[List[Dict]], Any],
    chunk_size: int = DEFAULT_CHUNK_SIZE
) -> List[Any]:
    """Process large transcript file in chunks.

    Convenience function for common pattern of chunked transcript processing.

    Args:
        file_path: Path to transcript file
        processor: Function to process each chunk
        chunk_size: Segments per chunk

    Returns:
        List of results from each chunk
    """
    estimated_mb = estimate_memory_usage(file_path)

    if estimated_mb > MAX_MEMORY_MB:
        log.warning(
            f"Large file detected ({estimated_mb:.1f}MB). "
            f"Using chunked processing with {chunk_size} segments per chunk."
        )

    results = []
    segments = list(stream_json_array(file_path))

    chunked = ChunkedProcessor(chunk_size=chunk_size)
    for result in chunked.process(segments, processor):
        results.append(result)

    return results
