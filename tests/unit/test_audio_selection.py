"""
Unit tests for audio selection module.
Tests intelligent selection of best quality audio files.
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

from src.audio.selection import (
    get_audio_files, 
    score_audio_file, 
    pick_best_audio,
    SUPPORTED_EXTS,
    FORMAT_SCORES
)
from src.utils.exceptions import ValidationError


class TestGetAudioFiles:
    """Tests for get_audio_files function."""
    
    def test_single_audio_file(self, tmp_path):
        """Test with a single audio file."""
        audio_file = tmp_path / "test.mp3"
        audio_file.touch()
        
        result = get_audio_files(audio_file)
        assert result == [audio_file]
    
    def test_directory_with_audio_files(self, tmp_path):
        """Test with directory containing audio files."""
        audio1 = tmp_path / "audio1.mp3"
        audio2 = tmp_path / "audio2.wav"
        text_file = tmp_path / "readme.txt"
        
        audio1.touch()
        audio2.touch()
        text_file.touch()
        
        result = get_audio_files(tmp_path)
        assert len(result) == 2
        assert audio1 in result
        assert audio2 in result
    
    def test_nonexistent_path(self):
        """Test with nonexistent path."""
        with pytest.raises(FileNotFoundError):
            get_audio_files(Path("nonexistent"))
    
    def test_unsupported_file_format(self, tmp_path):
        """Test with unsupported file format."""
        text_file = tmp_path / "test.txt"
        text_file.touch()
        
        with pytest.raises(ValueError, match="Unsupported audio format"):
            get_audio_files(text_file)
    
    def test_directory_with_no_audio(self, tmp_path):
        """Test with directory containing no audio files."""
        text_file = tmp_path / "readme.txt"
        text_file.touch()
        
        with pytest.raises(ValueError, match="No supported audio files found"):
            get_audio_files(tmp_path)


class TestScoreAudioFile:
    """Tests for score_audio_file function."""
    
    def test_format_scoring(self, tmp_path):
        """Test that different formats get appropriate scores."""
        flac_file = tmp_path / "test.flac"
        mp3_file = tmp_path / "test.mp3"
        flac_file.touch()
        mp3_file.touch()
        
        flac_score = score_audio_file(flac_file)
        mp3_score = score_audio_file(mp3_file)
        
        # FLAC should score higher than MP3
        assert flac_score > mp3_score
        assert flac_score >= FORMAT_SCORES[".flac"]
        assert mp3_score >= FORMAT_SCORES[".mp3"]
    
    def test_normalized_file_bonus(self, tmp_path):
        """Test that normalized files get bonus points."""
        normal_file = tmp_path / "audio.mp3"
        norm_file = tmp_path / "audio_norm.mp3"
        normal_file.touch()
        norm_file.touch()
        
        normal_score = score_audio_file(normal_file)
        norm_score = score_audio_file(norm_file)
        
        # Normalized file should score much higher
        assert norm_score > normal_score
        assert (norm_score - normal_score) >= 1000
    
    def test_audio_info_scoring(self, tmp_path):
        """Test scoring with audio metadata."""
        audio_file = tmp_path / "test.wav"
        audio_file.touch()
        
        # Mock audio info with high quality metrics
        audio_info = {
            "sample_rate": 48000,
            "bit_rate": 128000,
            "duration": 3600  # 1 hour
        }
        
        score = score_audio_file(audio_file, audio_info)

        # Should include format score plus quality bonuses (with caps)
        # Sample rate: min(48000/1000, 100) = 48
        # Bit rate: min(128000/1000, 50) = 50 (capped)
        # Duration: min(3600/3600, 10) = 1
        expected_min = FORMAT_SCORES[".wav"] + 48 + 50 + 1
        assert score >= expected_min


class TestPickBestAudio:
    """Tests for pick_best_audio function."""
    
    def test_single_file_selection(self, tmp_path):
        """Test selection with single audio file."""
        audio_file = tmp_path / "test.mp3"
        audio_file.touch()
        
        result = pick_best_audio(audio_file)
        assert result == audio_file
    
    def test_best_format_selection(self, tmp_path):
        """Test selection of best format from multiple files."""
        mp3_file = tmp_path / "audio.mp3"
        flac_file = tmp_path / "audio.flac"
        mp3_file.touch()
        flac_file.touch()
        
        with patch('src.audio.selection.ffprobe_info') as mock_ffprobe:
            mock_ffprobe.return_value = {}
            result = pick_best_audio(tmp_path)
        
        # Should select FLAC over MP3
        assert result == flac_file
    
    def test_normalized_file_preference(self, tmp_path):
        """Test preference for normalized files."""
        regular_flac = tmp_path / "audio.flac"
        norm_mp3 = tmp_path / "audio_norm.mp3"
        regular_flac.touch()
        norm_mp3.touch()
        
        with patch('src.audio.selection.ffprobe_info') as mock_ffprobe:
            mock_ffprobe.return_value = {}
            result = pick_best_audio(tmp_path)
        
        # Normalized MP3 should beat regular FLAC due to 1000 point bonus
        assert result == norm_mp3
    
    @patch('src.audio.selection.ffprobe_info')
    def test_audio_quality_preference(self, mock_ffprobe, tmp_path):
        """Test preference based on audio quality metrics."""
        low_quality = tmp_path / "low.mp3"
        high_quality = tmp_path / "high.mp3"
        low_quality.touch()
        high_quality.touch()
        
        # Mock different quality metrics
        def mock_info_side_effect(path):
            if "low" in str(path):
                return {"sample_rate": 22050, "bit_rate": 64000}
            else:
                return {"sample_rate": 48000, "bit_rate": 320000}
        
        mock_ffprobe.side_effect = mock_info_side_effect
        
        result = pick_best_audio(tmp_path)
        assert result == high_quality
    
    def test_ffprobe_error_handling(self, tmp_path):
        """Test graceful handling of ffprobe errors."""
        audio_file = tmp_path / "test.mp3"
        audio_file.touch()
        
        with patch('src.audio.selection.ffprobe_info') as mock_ffprobe:
            mock_ffprobe.side_effect = Exception("FFprobe failed")
            
            # Should still work with basic scoring
            result = pick_best_audio(tmp_path)
            assert result == audio_file
    
    def test_empty_directory(self, tmp_path):
        """Test with empty directory."""
        with pytest.raises(ValueError, match="No supported audio files found"):
            pick_best_audio(tmp_path)
    
    def test_nonexistent_path(self):
        """Test with nonexistent path."""
        with pytest.raises(FileNotFoundError):
            pick_best_audio(Path("nonexistent"))


@pytest.fixture
def mock_audio_files(tmp_path):
    """Create a set of test audio files with different formats."""
    files = {}
    for ext in [".mp3", ".wav", ".flac", ".m4a"]:
        file_path = tmp_path / f"audio{ext}"
        file_path.touch()
        files[ext] = file_path
    return files


def test_integration_full_selection_process(mock_audio_files, tmp_path):
    """Integration test for the complete selection process."""
    with patch('src.audio.selection.ffprobe_info') as mock_ffprobe:
        # Mock consistent audio info
        mock_ffprobe.return_value = {
            "sample_rate": 44100,
            "bit_rate": 192000,
            "duration": 180
        }
        
        result = pick_best_audio(tmp_path)
        
        # Should select the highest-scoring format (M4A in this case)
        assert result == mock_audio_files[".m4a"]
        
        # Verify ffprobe was called for each file
        assert mock_ffprobe.call_count == len(mock_audio_files)


if __name__ == "__main__":
    pytest.main([__file__])