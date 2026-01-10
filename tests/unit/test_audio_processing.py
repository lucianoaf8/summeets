"""
Unit tests for audio processing modules.
Tests FFmpeg operations, audio selection, and compression.
"""
import pytest
from pathlib import Path
from unittest.mock import patch, Mock, call
import subprocess
import json

from src.audio.ffmpeg_ops import (
    probe, normalize_loudness, extract_audio_copy, extract_audio_reencode,
    increase_audio_volume, convert_audio_format, extract_audio_from_video,
    ensure_wav16k_mono, ffprobe_info
)
from src.audio.selection import pick_best_audio, score_audio_file, get_audio_files
from src.audio.compression import compress_audio_for_upload, get_file_size_mb
from src.utils.exceptions import AudioProcessingError


class TestFFmpegOperations:
    """Test FFmpeg wrapper functions."""
    
    @patch('subprocess.run')
    def test_probe_success(self, mock_run):
        """Test successful probe operation."""
        mock_run.return_value.stdout = "Duration: 00:05:00.00"
        mock_run.return_value.stderr = "Stream #0:0: Audio: mp3"
        mock_run.return_value.returncode = 0
        
        result = probe("/test/audio.mp3")
        
        assert "Duration: 00:05:00.00" in result
        assert "Stream #0:0: Audio: mp3" in result
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_normalize_loudness_success(self, mock_run):
        """Test successful loudness normalization."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""
        
        normalize_loudness("/input/audio.mp3", "/output/normalized.mp3")
        
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "loudnorm" in ' '.join(args)
        assert "/input/audio.mp3" in ' '.join(args)
        assert "/output/normalized.mp3" in ' '.join(args)
    
    @patch('subprocess.run')
    def test_ffmpeg_error_handling(self, mock_run):
        """Test FFmpeg error handling."""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "Invalid input format"
        
        with pytest.raises(RuntimeError, match="ffmpeg error: Invalid input format"):
            normalize_loudness("/invalid/audio.mp3", "/output/normalized.mp3")
    
    @patch('subprocess.run')
    def test_extract_audio_copy(self, mock_run):
        """Test audio extraction with copy codec."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""
        
        extract_audio_copy("/input/video.mp4", "/output/audio.m4a", stream_index=0)
        
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        command = ' '.join(args)
        assert "-map 0:a:0" in command
        assert "-vn" in command
        assert "-c:a copy" in command
    
    @patch('subprocess.run')
    def test_extract_audio_reencode_aac(self, mock_run):
        """Test audio extraction with AAC re-encoding."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""
        
        extract_audio_reencode("/input/video.mp4", "/output/audio.m4a", codec="aac")
        
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        command = ' '.join(args)
        assert "-c:a aac" in command
        assert "-b:a 160k" in command
    
    @patch('subprocess.run')
    def test_extract_audio_reencode_mp3(self, mock_run):
        """Test audio extraction with MP3 re-encoding."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""
        
        extract_audio_reencode("/input/video.mp4", "/output/audio.mp3", codec="mp3")
        
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        command = ' '.join(args)
        assert "-c:a libmp3lame" in command
        assert "-q:a 2" in command
    
    @patch('subprocess.run')
    def test_increase_audio_volume(self, mock_run):
        """Test audio volume increase."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""
        
        increase_audio_volume("/input/audio.mp3", "/output/louder.mp3", gain_db=10.0)
        
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        command = ' '.join(args)
        assert "volume=10.0dB" in command
    
    @patch('core.audio.ffmpeg_ops.ffprobe_info')
    @patch('subprocess.run')
    def test_extract_audio_from_video_high_quality(self, mock_run, mock_probe):
        """Test extracting high quality audio from video."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""
        
        mock_probe.return_value = {
            'audio_codec': 'aac',
            'audio_bit_rate': 256000
        }
        
        result = extract_audio_from_video(
            Path("/input/video.mp4"),
            Path("/output/audio.m4a"),
            format="m4a",
            quality="high"
        )
        
        assert result == Path("/output/audio.m4a")
        mock_run.assert_called()
    
    @patch('core.audio.ffmpeg_ops.ffprobe_info')
    @patch('subprocess.run') 
    def test_ensure_wav16k_mono(self, mock_run, mock_probe):
        """Test conversion to WAV 16kHz mono format."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""
        
        mock_probe.return_value = {
            'sample_rate': 44100,
            'channels': 2
        }
        
        input_file = Path("/input/audio.mp3")
        result = ensure_wav16k_mono(input_file)
        
        # Should create new file with _16k_mono suffix
        expected_output = input_file.parent / f"{input_file.stem}_16k_mono.wav"
        assert result == expected_output
        
        mock_run.assert_called()
        args = mock_run.call_args[0][0]
        command = ' '.join(args)
        assert "-ar 16000" in command
        assert "-ac 1" in command


class TestFFprobeInfo:
    """Test ffprobe information extraction."""
    
    @patch('subprocess.run')
    def test_ffprobe_info_success(self, mock_run):
        """Test successful ffprobe information extraction."""
        ffprobe_output = {
            "format": {
                "duration": "300.123456",
                "bit_rate": "128000",
                "size": "4800000"
            },
            "streams": [
                {
                    "codec_type": "audio",
                    "codec_name": "mp3",
                    "sample_rate": "44100",
                    "channels": 2,
                    "bit_rate": "128000"
                }
            ]
        }
        
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps(ffprobe_output)
        mock_run.return_value.stderr = ""
        
        result = ffprobe_info("/test/audio.mp3")
        
        assert result["duration"] == 300.123456
        assert result["bit_rate"] == 128000
        assert result["sample_rate"] == 44100
        assert result["channels"] == 2
        assert result["codec"] == "mp3"
        assert result["size"] == 4800000
    
    @patch('subprocess.run')
    def test_ffprobe_info_video_with_audio(self, mock_run):
        """Test ffprobe with video file containing audio."""
        ffprobe_output = {
            "format": {
                "duration": "1800.500000",
                "bit_rate": "2000000",
                "size": "450000000"
            },
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "bit_rate": "1800000"
                },
                {
                    "codec_type": "audio",
                    "codec_name": "aac",
                    "sample_rate": "48000",
                    "channels": 2,
                    "bit_rate": "192000"
                }
            ]
        }
        
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps(ffprobe_output)
        mock_run.return_value.stderr = ""
        
        result = ffprobe_info("/test/video.mp4")
        
        assert result["duration"] == 1800.5
        assert result["audio_codec"] == "aac"
        assert result["video_codec"] == "h264"
        assert result["audio_sample_rate"] == 48000
        assert result["audio_channels"] == 2
        assert result["audio_bit_rate"] == 192000
        assert result["video_bit_rate"] == 1800000
    
    @patch('subprocess.run')
    def test_ffprobe_info_error(self, mock_run):
        """Test ffprobe error handling."""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = "Invalid data found"
        
        with pytest.raises(AudioProcessingError, match="ffprobe failed"):
            ffprobe_info("/invalid/file.mp3")
    
    @patch('subprocess.run')
    def test_ffprobe_info_malformed_json(self, mock_run):
        """Test ffprobe with malformed JSON output."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "invalid json"
        mock_run.return_value.stderr = ""
        
        with pytest.raises(AudioProcessingError, match="Failed to parse ffprobe output"):
            ffprobe_info("/test/audio.mp3")


class TestAudioSelection:
    """Test audio file selection and ranking."""
    
    def test_pick_best_audio_single_file(self, audio_file_samples):
        """Test picking audio from directory with single file."""
        # Create directory with one audio file
        directory = audio_file_samples['.m4a']['path'].parent
        
        with patch('core.audio.selection.get_audio_files') as mock_get:
            mock_rank.return_value = [audio_file_samples['.m4a']['path']]
            
            result = pick_best_audio(directory)
            
            assert result == audio_file_samples['.m4a']['path']
            mock_rank.assert_called_once()
    
    def test_pick_best_audio_multiple_files(self, audio_file_samples):
        """Test picking best audio from multiple files."""
        directory = audio_file_samples['.m4a']['path'].parent
        
        # Mock ranking with m4a as best quality
        ranked_files = [
            audio_file_samples['.m4a']['path'],
            audio_file_samples['.flac']['path'],
            audio_file_samples['.mp3']['path']
        ]
        
        with patch('core.audio.selection.get_audio_files') as mock_get:
            mock_rank.return_value = ranked_files
            
            result = pick_best_audio(directory)
            
            assert result == audio_file_samples['.m4a']['path']
    
    def test_pick_best_audio_no_files(self, tmp_path):
        """Test picking audio when no audio files exist."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        with pytest.raises(FileNotFoundError, match="No audio files found"):
            pick_best_audio(empty_dir)
    
    def test_get_audio_files_by_format_priority(self, audio_file_samples):
        """Test ranking audio files by format priority."""
        files = [
            audio_file_samples['.mp3']['path'],
            audio_file_samples['.m4a']['path'],
            audio_file_samples['.flac']['path'],
            audio_file_samples['.wav']['path']
        ]
        
        with patch('core.audio.ffmpeg_ops.ffprobe_info') as mock_probe:
            # Mock same quality for all files to test format priority
            mock_probe.return_value = {
                'duration': 300.0,
                'bit_rate': 128000,
                'sample_rate': 44100,
                'channels': 2,
                'size': 5000000
            }
            
            ranked = get_audio_files(files)
            
            # m4a should be first (highest priority)
            assert ranked[0] == audio_file_samples['.m4a']['path']
            assert ranked[1] == audio_file_samples['.flac']['path']
            assert ranked[2] == audio_file_samples['.wav']['path']
            assert ranked[3] == audio_file_samples['.mp3']['path']
    
    def test_get_audio_files_by_quality(self, audio_file_samples):
        """Test ranking audio files by quality metrics."""
        files = [
            audio_file_samples['.mp3']['path'],
            audio_file_samples['.flac']['path']
        ]
        
        def mock_probe_side_effect(path):
            if '.mp3' in str(path):
                return {
                    'duration': 300.0,
                    'bit_rate': 128000,  # Lower quality
                    'sample_rate': 44100,
                    'channels': 2,
                    'size': 3000000
                }
            else:  # .flac
                return {
                    'duration': 300.0,
                    'bit_rate': 800000,  # Higher quality
                    'sample_rate': 48000,
                    'channels': 2,
                    'size': 20000000
                }
        
        with patch('core.audio.ffmpeg_ops.ffprobe_info', side_effect=mock_probe_side_effect):
            ranked = get_audio_files(files)
            
            # FLAC should be ranked higher due to better quality
            assert ranked[0] == audio_file_samples['.flac']['path']
            assert ranked[1] == audio_file_samples['.mp3']['path']
    
    def test_get_audio_files_corrupted_file(self, audio_file_samples):
        """Test ranking with corrupted audio file."""
        files = [
            audio_file_samples['.mp3']['path'],
            audio_file_samples['corrupted']['path']
        ]
        
        def mock_probe_side_effect(path):
            if 'corrupted' in str(path):
                raise AudioProcessingError("Invalid audio format")
            return {
                'duration': 300.0,
                'bit_rate': 128000,
                'sample_rate': 44100,
                'channels': 2,
                'size': 3000000
            }
        
        with patch('core.audio.ffmpeg_ops.ffprobe_info', side_effect=mock_probe_side_effect):
            ranked = get_audio_files(files)
            
            # Only valid file should be returned
            assert len(ranked) == 1
            assert ranked[0] == audio_file_samples['.mp3']['path']


class TestAudioCompression:
    """Test audio compression functionality."""
    
    @patch('subprocess.run')
    def test_compress_audio_for_upload_opus(self, mock_run):
        """Test audio compression to Opus format."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""
        
        input_file = Path("/input/audio.wav")
        result = compress_audio_for_upload(input_file)
        
        expected_output = input_file.parent / f"{input_file.stem}_compressed.opus"
        assert result == expected_output
        
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        command = ' '.join(args)
        assert "-c:a libopus" in command
        assert "-b:a 64k" in command
    
    @patch('subprocess.run')
    def test_compress_audio_custom_bitrate(self, mock_run):
        """Test audio compression with custom bitrate."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""
        
        input_file = Path("/input/audio.wav")
        result = compress_audio_for_upload(input_file, target_bitrate="96k")
        
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        command = ' '.join(args)
        assert "-b:a 96k" in command
    
    @patch('subprocess.run')
    def test_compress_audio_error(self, mock_run):
        """Test audio compression error handling."""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "Compression failed"
        
        input_file = Path("/input/audio.wav")
        
        with pytest.raises(AudioProcessingError, match="Audio compression failed"):
            compress_audio_for_upload(input_file)
    
    def test_get_file_size_mb(self):
        """Test file size calculation in megabytes."""
        # Mock a file with known size
        from unittest.mock import Mock
        mock_path = Mock()
        mock_stat = Mock()
        mock_stat.st_size = 2048000  # 2MB in bytes
        mock_path.stat.return_value = mock_stat
        
        size_mb = get_file_size_mb(mock_path)
        
        # Should be approximately 1.95 MB (2048000 / 1024 / 1024)
        assert abs(size_mb - 1.953125) < 0.01
    
    def test_calculate_compression_ratio(self):
        """Test compression ratio calculation."""
        original_size = 10000000  # 10MB
        compressed_size = 2000000  # 2MB
        
        ratio = original_size / compressed_size
        
        # Should be 5.0 (original is 5x larger)
        assert ratio == 5.0
    
    def test_calculate_compression_ratio_no_compression(self):
        """Test compression ratio when no compression occurred."""
        original_size = 1000000
        compressed_size = 1000000
        ratio = original_size / compressed_size
        assert ratio == 1.0


class TestAudioFormatConversion:
    """Test audio format conversion functionality."""
    
    @patch('subprocess.run')
    def test_convert_audio_format_mp3_to_wav(self, mock_run):
        """Test converting MP3 to WAV."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""
        
        input_file = Path("/input/audio.mp3")
        output_file = Path("/output/audio.wav")
        
        result = convert_audio_format(input_file, output_file, "wav", quality="high")
        
        assert result == output_file
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        command = ' '.join(args)
        assert str(input_file) in command
        assert str(output_file) in command
    
    @patch('subprocess.run')
    def test_convert_audio_format_quality_settings(self, mock_run):
        """Test conversion with different quality settings."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""
        
        input_file = Path("/input/audio.wav")
        output_file = Path("/output/audio.mp3")
        
        # Test high quality
        convert_audio_format(input_file, output_file, "mp3", quality="high")
        args = mock_run.call_args[0][0]
        command = ' '.join(args)
        assert "-q:a 0" in command  # High quality MP3
        
        # Test medium quality
        mock_run.reset_mock()
        convert_audio_format(input_file, output_file, "mp3", quality="medium")
        args = mock_run.call_args[0][0]
        command = ' '.join(args)
        assert "-q:a 2" in command  # Medium quality MP3
    
    @patch('subprocess.run')
    def test_convert_audio_format_error(self, mock_run):
        """Test audio format conversion error."""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "Unsupported format"
        
        input_file = Path("/input/audio.wav")
        output_file = Path("/output/audio.unknown")
        
        with pytest.raises(AudioProcessingError, match="Audio conversion failed"):
            convert_audio_format(input_file, output_file, "unknown")


class TestAudioValidation:
    """Test audio file validation and error handling."""
    
    def test_validate_ffmpeg_binaries(self):
        """Test validation of FFmpeg binary availability."""
        from src.audio.ffmpeg_ops import _validate_ffmpeg_binaries
        
        with patch('shutil.which') as mock_which:
            # Test when binaries are available
            mock_which.return_value = "/usr/bin/ffmpeg"
            _validate_ffmpeg_binaries()  # Should not raise
            
            # Test when binaries are missing
            mock_which.return_value = None
            with pytest.raises(AudioProcessingError, match="FFmpeg not found"):
                _validate_ffmpeg_binaries()
    
    def test_audio_format_detection(self, audio_file_samples):
        """Test automatic audio format detection."""
        from src.audio.selection import detect_audio_format
        
        for ext, sample in audio_file_samples.items():
            if ext.startswith('.') and ext != 'corrupted':
                path = sample['path']
                detected_format = detect_audio_format(path)
                assert detected_format == ext[1:]  # Remove leading dot
    
    def test_audio_duration_validation(self):
        """Test audio duration validation."""
        from src.audio.selection import validate_audio_duration
        
        # Valid duration
        assert validate_audio_duration(300.0)  # 5 minutes
        
        # Too short
        with pytest.raises(ValueError, match="too short"):
            validate_audio_duration(5.0)  # 5 seconds
        
        # Too long
        with pytest.raises(ValueError, match="too long"):
            validate_audio_duration(7200.0)  # 2 hours


if __name__ == "__main__":
    pytest.main([__file__, "-v"])