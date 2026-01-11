"""
Valid audio file generator for testing.
Creates actual valid audio files that FFmpeg can process.
"""
import wave
import struct
import math
from pathlib import Path
from typing import Optional
import io


def generate_silence_wav(
    file_path: Path,
    duration_seconds: float = 1.0,
    sample_rate: int = 44100,
    channels: int = 2,
    sample_width: int = 2
) -> Path:
    """
    Generate a valid WAV file containing silence.

    Args:
        file_path: Path to save the WAV file
        duration_seconds: Duration in seconds
        sample_rate: Sample rate (default 44100 Hz)
        channels: Number of channels (1=mono, 2=stereo)
        sample_width: Bytes per sample (2 = 16-bit)

    Returns:
        Path to the created file
    """
    n_samples = int(duration_seconds * sample_rate)

    with wave.open(str(file_path), 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)

        # Generate silence (zeros)
        silence = b'\x00' * (n_samples * channels * sample_width)
        wav_file.writeframes(silence)

    return file_path


def generate_tone_wav(
    file_path: Path,
    duration_seconds: float = 1.0,
    frequency: float = 440.0,
    sample_rate: int = 44100,
    channels: int = 2,
    amplitude: float = 0.3
) -> Path:
    """
    Generate a valid WAV file containing a sine wave tone.

    Args:
        file_path: Path to save the WAV file
        duration_seconds: Duration in seconds
        frequency: Tone frequency in Hz (default 440 = A4)
        sample_rate: Sample rate (default 44100 Hz)
        channels: Number of channels (1=mono, 2=stereo)
        amplitude: Volume 0.0 to 1.0

    Returns:
        Path to the created file
    """
    n_samples = int(duration_seconds * sample_rate)
    max_amplitude = 32767 * amplitude

    with wave.open(str(file_path), 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)

        frames = []
        for i in range(n_samples):
            # Generate sine wave sample
            sample = int(max_amplitude * math.sin(2 * math.pi * frequency * i / sample_rate))
            # Pack as signed 16-bit integer
            packed = struct.pack('<h', sample)
            # Duplicate for each channel
            frames.append(packed * channels)

        wav_file.writeframes(b''.join(frames))

    return file_path


def generate_wav_bytes(
    duration_seconds: float = 0.5,
    sample_rate: int = 16000,
    channels: int = 1
) -> bytes:
    """
    Generate valid WAV file bytes in memory.
    Useful for mocking without file I/O.

    Returns:
        bytes: Valid WAV file content
    """
    buffer = io.BytesIO()
    n_samples = int(duration_seconds * sample_rate)

    with wave.open(buffer, 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b'\x00' * (n_samples * channels * 2))

    return buffer.getvalue()


def create_test_audio_files(base_path: Path) -> dict:
    """
    Create a complete set of valid test audio files.

    Args:
        base_path: Directory to create files in

    Returns:
        dict: Mapping of format to file info
    """
    samples = {}

    # Create WAV files (valid format FFmpeg can process)
    wav_file = base_path / "test_audio.wav"
    generate_silence_wav(wav_file, duration_seconds=2.0)
    samples['.wav'] = {
        'path': wav_file,
        'duration': 2.0,
        'sample_rate': 44100,
        'channels': 2
    }

    # Create a short WAV for quick tests
    short_wav = base_path / "short_audio.wav"
    generate_silence_wav(short_wav, duration_seconds=0.5, sample_rate=16000, channels=1)
    samples['short'] = {
        'path': short_wav,
        'duration': 0.5,
        'sample_rate': 16000,
        'channels': 1
    }

    # Create WAV with tone for testing actual audio processing
    tone_wav = base_path / "tone_audio.wav"
    generate_tone_wav(tone_wav, duration_seconds=1.0, frequency=440.0)
    samples['tone'] = {
        'path': tone_wav,
        'duration': 1.0,
        'frequency': 440.0
    }

    # Create normalized version marker
    norm_wav = base_path / "audio_norm.wav"
    generate_silence_wav(norm_wav, duration_seconds=1.0)
    samples['normalized'] = {
        'path': norm_wav,
        'duration': 1.0,
        'normalized': True
    }

    return samples


# Minimal valid MP3 frame (for tests that just need valid headers)
# This is a minimal valid MP3 frame with silence
VALID_MP3_HEADER = bytes([
    0xFF, 0xFB, 0x90, 0x00,  # MP3 frame sync + header
    0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00,
] * 10)  # Repeat to make it longer


def create_minimal_mp3(file_path: Path) -> Path:
    """
    Create a minimal MP3-like file for basic tests.
    Note: This won't be fully valid for FFmpeg processing,
    use WAV files for actual FFmpeg tests.
    """
    file_path.write_bytes(VALID_MP3_HEADER)
    return file_path
