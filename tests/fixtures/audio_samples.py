"""
Audio file fixtures and sample data for testing.
Creates realistic audio file samples for various test scenarios.
"""
import pytest
from pathlib import Path
from typing import Dict, List
import json
import tempfile
import shutil


@pytest.fixture
def audio_file_samples(tmp_path):
    """Create comprehensive audio file samples for testing."""
    samples = {}
    
    # High quality formats
    formats = {
        '.m4a': {'priority': 1, 'codec': 'aac', 'quality': 'high'},
        '.flac': {'priority': 2, 'codec': 'flac', 'quality': 'lossless'},
        '.wav': {'priority': 3, 'codec': 'pcm', 'quality': 'uncompressed'},
        '.mka': {'priority': 4, 'codec': 'various', 'quality': 'high'},
        '.ogg': {'priority': 5, 'codec': 'vorbis', 'quality': 'medium'},
        '.mp3': {'priority': 6, 'codec': 'mp3', 'quality': 'medium'},
        '.webm': {'priority': 7, 'codec': 'opus', 'quality': 'medium'}
    }
    
    for ext, metadata in formats.items():
        file_path = tmp_path / f"meeting_audio{ext}"
        # Create fake audio data with varying sizes
        size = 1024 * (10 - metadata['priority'])  # Larger for higher priority
        file_path.write_bytes(b"fake audio data " * size)
        samples[ext] = {
            'path': file_path,
            'metadata': metadata,
            'size': file_path.stat().st_size
        }
    
    # Create corrupted file
    corrupted_file = tmp_path / "corrupted.mp3"
    corrupted_file.write_bytes(b"not audio data")
    samples['corrupted'] = {
        'path': corrupted_file,
        'metadata': {'quality': 'corrupted'},
        'size': corrupted_file.stat().st_size
    }
    
    # Create normalized versions
    for ext in ['.mp3', '.m4a']:
        norm_file = tmp_path / f"meeting_audio_norm{ext}"
        norm_file.write_bytes(b"normalized audio data " * 512)
        samples[f'normalized{ext}'] = {
            'path': norm_file,
            'metadata': {'quality': 'normalized'},
            'size': norm_file.stat().st_size
        }
    
    return samples


@pytest.fixture
def video_file_samples(tmp_path):
    """Create video file samples for audio extraction testing."""
    samples = {}
    
    video_formats = {
        '.mp4': {'codec': 'h264', 'container': 'mp4'},
        '.mkv': {'codec': 'h264', 'container': 'mkv'},
        '.avi': {'codec': 'xvid', 'container': 'avi'},
        '.mov': {'codec': 'h264', 'container': 'mov'},
        '.wmv': {'codec': 'wmv', 'container': 'wmv'},
        '.flv': {'codec': 'h264', 'container': 'flv'},
        '.webm': {'codec': 'vp8', 'container': 'webm'},
        '.m4v': {'codec': 'h264', 'container': 'm4v'}
    }
    
    for ext, metadata in video_formats.items():
        file_path = tmp_path / f"meeting_video{ext}"
        # Create fake video data
        file_path.write_bytes(b"fake video data with audio track " * 1024)
        samples[ext] = {
            'path': file_path,
            'metadata': metadata,
            'size': file_path.stat().st_size
        }
    
    return samples


@pytest.fixture
def directory_with_mixed_files(tmp_path):
    """Create directory with mixed audio files for selection testing."""
    audio_dir = tmp_path / "mixed_audio"
    audio_dir.mkdir()
    
    # Create various quality audio files
    files = {
        'meeting_high.flac': b"high quality audio " * 2048,
        'meeting_medium.mp3': b"medium quality audio " * 1024,
        'meeting_low.ogg': b"low quality audio " * 512,
        'other_audio.wav': b"other audio " * 1024,
        'readme.txt': b"This is not an audio file",
        'image.jpg': b"fake image data",
        '.hidden_audio.mp3': b"hidden audio file " * 256,
    }
    
    created_files = []
    for filename, content in files.items():
        file_path = audio_dir / filename
        file_path.write_bytes(content)
        created_files.append(file_path)
    
    return {
        'directory': audio_dir,
        'files': created_files,
        'audio_files': [f for f in created_files if any(f.suffix == ext for ext in ['.flac', '.mp3', '.ogg', '.wav'])],
        'non_audio_files': [f for f in created_files if not any(f.suffix == ext for ext in ['.flac', '.mp3', '.ogg', '.wav'])]
    }


@pytest.fixture
def ffprobe_mock_responses():
    """Mock responses for ffprobe operations."""
    return {
        'meeting_audio.mp3': {
            'duration': 1800.5,  # 30 minutes
            'bit_rate': 128000,
            'sample_rate': 44100,
            'channels': 2,
            'codec': 'mp3',
            'size': 14000000
        },
        'meeting_audio.flac': {
            'duration': 1800.5,
            'bit_rate': 800000,
            'sample_rate': 48000,
            'channels': 2,
            'codec': 'flac',
            'size': 85000000
        },
        'meeting_audio.m4a': {
            'duration': 1800.5,
            'bit_rate': 256000,
            'sample_rate': 48000,
            'channels': 2,
            'codec': 'aac',
            'size': 28000000
        },
        'corrupted.mp3': {
            'error': 'Invalid data found when processing input'
        },
        'meeting_video.mp4': {
            'duration': 1800.5,
            'video_codec': 'h264',
            'audio_codec': 'aac',
            'audio_bit_rate': 192000,
            'video_bit_rate': 2000000,
            'audio_sample_rate': 48000,
            'audio_channels': 2,
            'size': 250000000
        }
    }


@pytest.fixture
def large_audio_file_mock(tmp_path):
    """Mock large audio file for performance testing."""
    large_file = tmp_path / "large_meeting.wav"
    # Simulate 2-hour meeting file (would be ~1GB)
    metadata = {
        'path': large_file,
        'duration': 7200,  # 2 hours
        'size': 1073741824,  # 1GB
        'sample_rate': 48000,
        'channels': 2,
        'bit_rate': 1536000
    }
    
    # Don't actually create the large file, just the metadata
    return metadata


@pytest.fixture
def compressed_audio_samples(tmp_path):
    """Create audio samples for compression testing."""
    samples = {}
    
    # Original file
    original = tmp_path / "original.wav"
    original.write_bytes(b"uncompressed audio data " * 4096)  # Larger file
    
    # Compressed versions
    compressed_opus = tmp_path / "compressed.opus"
    compressed_opus.write_bytes(b"compressed audio data " * 512)  # Much smaller
    
    compressed_mp3 = tmp_path / "compressed.mp3"
    compressed_mp3.write_bytes(b"compressed audio data " * 1024)
    
    samples.update({
        'original': {'path': original, 'size': original.stat().st_size, 'format': 'wav'},
        'opus': {'path': compressed_opus, 'size': compressed_opus.stat().st_size, 'format': 'opus'},
        'mp3': {'path': compressed_mp3, 'size': compressed_mp3.stat().st_size, 'format': 'mp3'}
    })
    
    return samples


@pytest.fixture
def audio_conversion_matrix():
    """Define conversion matrix for format testing."""
    return {
        'input_formats': ['.wav', '.mp3', '.flac', '.m4a', '.ogg'],
        'output_formats': ['.wav', '.mp3', '.flac', '.m4a', '.ogg', '.opus'],
        'quality_settings': ['low', 'medium', 'high', 'lossless'],
        'sample_rates': [16000, 22050, 44100, 48000],
        'channels': [1, 2],  # mono, stereo
        'bit_rates': [96, 128, 192, 256, 320]  # kbps
    }


def create_test_audio_file(path: Path, duration: float = 10.0, 
                          sample_rate: int = 44100, channels: int = 2) -> Path:
    """
    Utility function to create test audio files with specified parameters.
    Creates fake binary data that simulates audio files.
    """
    # Calculate approximate file size based on parameters
    bytes_per_sample = 2  # 16-bit
    total_samples = int(duration * sample_rate * channels)
    file_size = total_samples * bytes_per_sample
    
    # Create fake audio data
    fake_data = b"audio" * (file_size // 5)
    if len(fake_data) < file_size:
        fake_data += b"0" * (file_size - len(fake_data))
    
    path.write_bytes(fake_data[:file_size])
    return path


def create_audio_directory_structure(base_path: Path) -> Dict[str, Path]:
    """
    Create a realistic directory structure with audio files.
    Useful for testing audio file discovery and selection.
    """
    structure = {}
    
    # Main meeting directory
    meeting_dir = base_path / "meeting_2024_08_16"
    meeting_dir.mkdir(parents=True)
    
    # Audio subdirectory
    audio_dir = meeting_dir / "audio"
    audio_dir.mkdir()
    
    # Create various audio files
    audio_files = [
        "presentation_part1.m4a",
        "presentation_part2.m4a", 
        "discussion.wav",
        "qa_session.mp3",
        "background_noise.wav"
    ]
    
    for filename in audio_files:
        audio_path = audio_dir / filename
        create_test_audio_file(audio_path)
        structure[filename] = audio_path
    
    # Create some non-audio files
    (meeting_dir / "notes.txt").write_text("Meeting notes")
    (meeting_dir / "slides.pdf").write_bytes(b"fake pdf")
    
    structure['meeting_dir'] = meeting_dir
    structure['audio_dir'] = audio_dir
    
    return structure