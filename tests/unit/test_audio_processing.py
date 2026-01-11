"""
Unit tests for audio processing modules.
Tests FFmpeg operations, audio selection, and compression.
"""
import pytest
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
import subprocess
import json
import tempfile

from src.audio.ffmpeg_ops import (
    probe, normalize_loudness, extract_audio_copy, extract_audio_reencode,
    increase_audio_volume, convert_audio_format, extract_audio_from_video,
    ensure_wav16k_mono, ffprobe_info, run_cmd, probe_video_info
)
from src.audio.selection import pick_best_audio, score_audio_file, get_audio_files, SUPPORTED_EXTS
from src.audio.compression import compress_audio_for_upload, get_file_size_mb, CompressionError


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
    def test_extract_audio_reencode_wav(self, mock_run):
        """Test audio extraction with WAV re-encoding."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""

        extract_audio_reencode("/input/video.mp4", "/output/audio.wav", codec="wav")

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        command = ' '.join(args)
        assert "-c:a pcm_s16le" in command
        assert "-ar 48000" in command

    def test_extract_audio_reencode_invalid_codec(self):
        """Test audio extraction with invalid codec raises error."""
        with pytest.raises(ValueError, match="codec must be one of"):
            extract_audio_reencode("/input/video.mp4", "/output/audio.xyz", codec="invalid")

    @patch('subprocess.run')
    def test_increase_audio_volume(self, mock_run):
        """Test audio volume increase."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""

        result = increase_audio_volume(Path("/input/audio.mp3"), Path("/output/louder.mp3"), gain_db=10.0)

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        command = ' '.join(args)
        assert "volume=10.0dB" in command

    @patch('subprocess.run')
    def test_extract_audio_from_video_high_quality(self, mock_run):
        """Test extracting high quality audio from video."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "audio.m4a"
            result = extract_audio_from_video(
                Path("/input/video.mp4"),
                output_path,
                format="m4a",
                quality="high"
            )

            assert result == output_path
            mock_run.assert_called()
            args = mock_run.call_args[0][0]
            command = ' '.join(args)
            assert "-c:a aac" in command
            assert "-b:a 192k" in command

    @patch('subprocess.run')
    def test_extract_audio_from_video_unsupported_format(self, mock_run):
        """Test extracting audio with unsupported format."""
        with pytest.raises(ValueError, match="Unsupported format"):
            extract_audio_from_video(
                Path("/input/video.mp4"),
                Path("/output/audio.xyz"),
                format="xyz"
            )

    @patch('src.audio.ffmpeg_ops._run_cmd')
    @patch('src.utils.fsio.get_data_manager')
    def test_ensure_wav16k_mono(self, mock_dm, mock_run_cmd):
        """Test conversion to WAV 16kHz mono format."""
        mock_dm_instance = Mock()
        output_path = Path("/data/audio/test/test_16k.wav")
        mock_dm_instance.get_audio_path.return_value = output_path
        mock_dm.return_value = mock_dm_instance

        input_file = Path("/input/audio.mp3")

        # Simulate file doesn't exist so conversion happens
        with patch.object(Path, 'exists', return_value=False):
            result = ensure_wav16k_mono(input_file)

        # Check conversion was called
        mock_run_cmd.assert_called_once()
        assert result == output_path


class TestFFprobeInfo:
    """Test ffprobe information extraction."""

    @patch('subprocess.Popen')
    def test_ffprobe_info_success(self, mock_popen):
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

        mock_process = Mock()
        mock_process.communicate.return_value = (json.dumps(ffprobe_output), "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        result = ffprobe_info(Path("/test/audio.mp3"))

        assert result["duration"] == pytest.approx(300.123456)
        assert result["bit_rate"] == 128000
        assert result["sample_rate"] == 44100
        assert result["channels"] == 2
        assert result["codec"] == "mp3"
        assert result["size"] == 4800000

    @patch('subprocess.Popen')
    def test_ffprobe_info_error_returns_empty(self, mock_popen):
        """Test ffprobe returns empty dict on error."""
        mock_process = Mock()
        mock_process.communicate.return_value = ("", "Invalid data found")
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        result = ffprobe_info(Path("/invalid/file.mp3"))

        assert result == {}

    @patch('subprocess.Popen')
    def test_ffprobe_info_malformed_json_returns_empty(self, mock_popen):
        """Test ffprobe returns empty dict with malformed JSON."""
        mock_process = Mock()
        mock_process.communicate.return_value = ("invalid json", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        result = ffprobe_info(Path("/test/audio.mp3"))

        assert result == {}

    @patch('subprocess.Popen')
    def test_ffprobe_info_no_audio_streams_returns_empty(self, mock_popen):
        """Test ffprobe returns empty dict when no audio streams."""
        ffprobe_output = {
            "format": {"duration": "300"},
            "streams": [{"codec_type": "video"}]
        }

        mock_process = Mock()
        mock_process.communicate.return_value = (json.dumps(ffprobe_output), "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        result = ffprobe_info(Path("/test/video.mp4"))

        assert result == {}


class TestProbeVideoInfo:
    """Test video probe functionality."""

    @patch('subprocess.Popen')
    def test_probe_video_info_success(self, mock_popen):
        """Test successful video probe."""
        ffprobe_output = {
            "format": {
                "duration": "1800.500000",
                "bit_rate": "2000000",
                "size": "450000000",
                "format_name": "mov,mp4"
            },
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "r_frame_rate": "30/1"
                },
                {
                    "codec_type": "audio",
                    "codec_name": "aac",
                    "sample_rate": "48000",
                    "channels": 2
                }
            ]
        }

        mock_process = Mock()
        mock_process.communicate.return_value = (json.dumps(ffprobe_output), "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        result = probe_video_info(Path("/test/video.mp4"))

        assert result["duration"] == pytest.approx(1800.5)
        assert result["video_codec"] == "h264"
        assert result["audio_codec"] == "aac"
        assert result["width"] == 1920
        assert result["height"] == 1080
        assert result["sample_rate"] == 48000
        assert result["channels"] == 2


class TestRunCmd:
    """Test run_cmd function."""

    @patch('subprocess.Popen')
    def test_run_cmd_success(self, mock_popen):
        """Test successful command execution."""
        mock_process = Mock()
        mock_process.communicate.return_value = ("output", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        returncode, stdout, stderr = run_cmd(["echo", "test"])

        assert returncode == 0
        assert stdout == "output"
        assert stderr == ""

    @patch('subprocess.Popen')
    def test_run_cmd_error(self, mock_popen):
        """Test command execution with error."""
        mock_process = Mock()
        mock_process.communicate.return_value = ("", "error message")
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        returncode, stdout, stderr = run_cmd(["invalid", "command"])

        assert returncode == 1
        assert stderr == "error message"


class TestAudioSelection:
    """Test audio file selection and ranking."""

    def test_get_audio_files_single_file(self, tmp_path):
        """Test get_audio_files with a single audio file."""
        audio_file = tmp_path / "audio.m4a"
        audio_file.write_bytes(b"fake audio")

        result = get_audio_files(audio_file)

        assert result == [audio_file]

    def test_get_audio_files_directory(self, tmp_path):
        """Test get_audio_files with a directory."""
        (tmp_path / "audio1.m4a").write_bytes(b"fake")
        (tmp_path / "audio2.mp3").write_bytes(b"fake")
        (tmp_path / "doc.txt").write_bytes(b"text")  # Should be ignored

        result = get_audio_files(tmp_path)

        assert len(result) == 2
        assert all(f.suffix.lower() in SUPPORTED_EXTS for f in result)

    def test_get_audio_files_nonexistent_raises(self, tmp_path):
        """Test get_audio_files with nonexistent path."""
        nonexistent = tmp_path / "nonexistent"

        with pytest.raises(FileNotFoundError):
            get_audio_files(nonexistent)

    def test_get_audio_files_unsupported_format_raises(self, tmp_path):
        """Test get_audio_files with unsupported format."""
        txt_file = tmp_path / "document.txt"
        txt_file.write_bytes(b"text")

        with pytest.raises(ValueError, match="Unsupported audio format"):
            get_audio_files(txt_file)

    def test_get_audio_files_empty_dir_raises(self, tmp_path):
        """Test get_audio_files with empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with pytest.raises(ValueError, match="No supported audio files"):
            get_audio_files(empty_dir)

    def test_score_audio_file_format_preference(self, tmp_path):
        """Test format preference in scoring."""
        m4a_file = tmp_path / "audio.m4a"
        mp3_file = tmp_path / "audio.mp3"
        m4a_file.write_bytes(b"x" * 1000)
        mp3_file.write_bytes(b"x" * 1000)

        m4a_score = score_audio_file(m4a_file)
        mp3_score = score_audio_file(mp3_file)

        assert m4a_score > mp3_score  # m4a preferred over mp3

    def test_score_audio_file_normalized_bonus(self, tmp_path):
        """Test normalized file gets bonus score."""
        regular_file = tmp_path / "audio.m4a"
        normalized_file = tmp_path / "audio_norm.m4a"
        regular_file.write_bytes(b"x" * 1000)
        normalized_file.write_bytes(b"x" * 1000)

        regular_score = score_audio_file(regular_file)
        normalized_score = score_audio_file(normalized_file)

        assert normalized_score > regular_score

    def test_score_audio_file_with_metadata(self, tmp_path):
        """Test scoring with audio metadata."""
        audio_file = tmp_path / "audio.m4a"
        audio_file.write_bytes(b"x" * 1000)

        audio_info = {
            'sample_rate': 48000,
            'bit_rate': 256000,
            'duration': 3600
        }

        score = score_audio_file(audio_file, audio_info)

        # Should be higher than without metadata
        base_score = score_audio_file(audio_file)
        assert score > base_score

    @patch('src.audio.selection.ffprobe_info')
    def test_pick_best_audio_single_file(self, mock_probe, tmp_path):
        """Test pick_best_audio with single file."""
        audio_file = tmp_path / "audio.m4a"
        audio_file.write_bytes(b"x" * 1000)

        mock_probe.return_value = {'duration': 300, 'bit_rate': 128000}

        result = pick_best_audio(audio_file)

        assert result == audio_file

    @patch('src.audio.selection.ffprobe_info')
    def test_pick_best_audio_multiple_files(self, mock_probe, tmp_path):
        """Test pick_best_audio selects highest scored file."""
        m4a_file = tmp_path / "audio.m4a"
        mp3_file = tmp_path / "audio.mp3"
        m4a_file.write_bytes(b"x" * 1000)
        mp3_file.write_bytes(b"x" * 1000)

        mock_probe.return_value = {'duration': 300, 'bit_rate': 128000}

        result = pick_best_audio(tmp_path)

        assert result == m4a_file  # m4a has higher format score

    def test_pick_best_audio_empty_dir(self, tmp_path):
        """Test pick_best_audio with empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with pytest.raises(ValueError):
            pick_best_audio(empty_dir)


class TestAudioCompression:
    """Test audio compression functionality."""

    def test_get_file_size_mb(self, tmp_path):
        """Test file size calculation in megabytes."""
        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"x" * (1024 * 1024))  # 1 MB

        size_mb = get_file_size_mb(test_file)

        assert size_mb == pytest.approx(1.0, rel=0.01)

    def test_compress_audio_returns_input_if_small_enough(self, tmp_path):
        """Test compression returns input if already small enough."""
        small_file = tmp_path / "small.ogg"
        small_file.write_bytes(b"x" * 1000)  # Very small

        result = compress_audio_for_upload(small_file, max_mb=1.0)

        assert result == small_file

    def test_compress_audio_nonexistent_raises(self, tmp_path):
        """Test compression with nonexistent file."""
        nonexistent = tmp_path / "nonexistent.ogg"

        with pytest.raises(FileNotFoundError):
            compress_audio_for_upload(nonexistent)

    @patch('src.audio.compression.run_cmd')
    def test_compress_audio_tries_lower_bitrates(self, mock_run_cmd, tmp_path):
        """Test compression tries progressively lower bitrates."""
        large_file = tmp_path / "large.wav"
        large_file.write_bytes(b"x" * (30 * 1024 * 1024))  # 30 MB

        # First attempt fails (still too large), second succeeds
        output_file = None

        def run_cmd_side_effect(cmd):
            nonlocal output_file
            # Extract output path from command
            output_file = Path(cmd[-1])
            # Create a small output file
            output_file.write_bytes(b"x" * (1024 * 1024))  # 1 MB
            return (0, "", "")

        mock_run_cmd.side_effect = run_cmd_side_effect

        result = compress_audio_for_upload(large_file, max_mb=24.0)

        assert result.exists()
        mock_run_cmd.assert_called()

    @patch('src.audio.compression.run_cmd')
    def test_compress_audio_raises_on_failure(self, mock_run_cmd, tmp_path):
        """Test compression raises when cannot meet size target."""
        large_file = tmp_path / "large.wav"
        large_file.write_bytes(b"x" * (100 * 1024 * 1024))  # 100 MB

        def run_cmd_side_effect(cmd):
            output_file = Path(cmd[-1])
            # Always create a file that's still too large
            output_file.write_bytes(b"x" * (50 * 1024 * 1024))  # 50 MB
            return (0, "", "")

        mock_run_cmd.side_effect = run_cmd_side_effect

        with pytest.raises(CompressionError, match="Could not compress"):
            compress_audio_for_upload(large_file, max_mb=1.0)


class TestAudioFormatConversion:
    """Test audio format conversion functionality."""

    @patch('subprocess.run')
    def test_convert_audio_format_mp3_high(self, mock_run):
        """Test converting to MP3 high quality."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""

        result = convert_audio_format(
            Path("/input/audio.wav"),
            Path("/output/audio.mp3"),
            "mp3",
            quality="high"
        )

        assert result == Path("/output/audio.mp3")
        args = mock_run.call_args[0][0]
        command = ' '.join(args)
        assert "-c:a libmp3lame" in command
        assert "-q:a 0" in command

    @patch('subprocess.run')
    def test_convert_audio_format_mp3_medium(self, mock_run):
        """Test converting to MP3 medium quality."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""

        convert_audio_format(
            Path("/input/audio.wav"),
            Path("/output/audio.mp3"),
            "mp3",
            quality="medium"
        )

        args = mock_run.call_args[0][0]
        command = ' '.join(args)
        assert "-q:a 2" in command

    @patch('subprocess.run')
    def test_convert_audio_format_m4a(self, mock_run):
        """Test converting to M4A."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""

        convert_audio_format(
            Path("/input/audio.wav"),
            Path("/output/audio.m4a"),
            "m4a",
            quality="high"
        )

        args = mock_run.call_args[0][0]
        command = ' '.join(args)
        assert "-c:a aac" in command
        assert "-b:a 192k" in command

    @patch('subprocess.run')
    def test_convert_audio_format_flac(self, mock_run):
        """Test converting to FLAC."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""

        convert_audio_format(
            Path("/input/audio.wav"),
            Path("/output/audio.flac"),
            "flac",
            quality="high"
        )

        args = mock_run.call_args[0][0]
        command = ' '.join(args)
        assert "-c:a flac" in command
        assert "-compression_level 8" in command

    @patch('subprocess.run')
    def test_convert_audio_format_ogg(self, mock_run):
        """Test converting to OGG."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""

        convert_audio_format(
            Path("/input/audio.wav"),
            Path("/output/audio.ogg"),
            "ogg",
            quality="medium"
        )

        args = mock_run.call_args[0][0]
        command = ' '.join(args)
        assert "-c:a libvorbis" in command

    def test_convert_audio_format_unsupported(self):
        """Test converting to unsupported format."""
        with pytest.raises(ValueError, match="Unsupported format"):
            convert_audio_format(
                Path("/input/audio.wav"),
                Path("/output/audio.xyz"),
                "xyz"
            )

    @patch('subprocess.run')
    def test_convert_audio_format_error(self, mock_run):
        """Test audio format conversion error."""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "Conversion failed"

        with pytest.raises(RuntimeError, match="ffmpeg error"):
            convert_audio_format(
                Path("/input/audio.wav"),
                Path("/output/audio.mp3"),
                "mp3"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
