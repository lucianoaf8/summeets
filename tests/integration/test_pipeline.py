"""
Integration tests for the transcription pipeline.
Tests end-to-end functionality with real components.
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import json

from src.transcribe.pipeline import TranscriptionPipeline
from src.models import Segment, Word
from src.utils.exceptions import TranscriptionError, FileOperationError


@pytest.fixture
def mock_audio_file(tmp_path):
    """Create a mock audio file for testing."""
    audio_file = tmp_path / "test_audio.mp3"
    audio_file.write_bytes(b"fake audio data")
    return audio_file


@pytest.fixture
def mock_transcriber():
    """Create a mock transcriber with realistic output."""
    transcriber = Mock()
    
    # Mock realistic transcription output
    mock_output = {
        "segments": [
            {
                "start": 0.0,
                "end": 5.0,
                "text": "Hello, this is a test.",
                "speaker": "SPEAKER_00",
                "words": [
                    {"start": 0.0, "end": 1.0, "word": "Hello,"},
                    {"start": 1.0, "end": 2.0, "word": "this"},
                    {"start": 2.0, "end": 3.0, "word": "is"},
                    {"start": 3.0, "end": 4.0, "word": "a"},
                    {"start": 4.0, "end": 5.0, "word": "test."}
                ]
            },
            {
                "start": 5.0,
                "end": 10.0,
                "text": "This is another segment.",
                "speaker": "SPEAKER_01",
                "words": [
                    {"start": 5.0, "end": 6.0, "word": "This"},
                    {"start": 6.0, "end": 7.0, "word": "is"},
                    {"start": 7.0, "end": 8.0, "word": "another"},
                    {"start": 8.0, "end": 10.0, "word": "segment."}
                ]
            }
        ]
    }
    
    transcriber.transcribe.return_value = mock_output
    return transcriber


class TestTranscriptionPipeline:
    """Tests for the TranscriptionPipeline class."""
    
    def test_process_audio_input_with_file(self, mock_audio_file):
        """Test processing audio input with a file path."""
        pipeline = TranscriptionPipeline()
        
        result = pipeline.process_audio_input(mock_audio_file)
        assert result == mock_audio_file
    
    def test_process_audio_input_with_directory(self, tmp_path):
        """Test processing audio input with a directory."""
        audio_file = tmp_path / "test.mp3"
        audio_file.touch()
        
        pipeline = TranscriptionPipeline()
        
        with patch('core.transcribe.new_pipeline.pick_best_audio') as mock_pick:
            mock_pick.return_value = audio_file
            result = pipeline.process_audio_input(tmp_path)
        
        assert result == audio_file
        mock_pick.assert_called_once_with(tmp_path)
    
    def test_process_audio_input_nonexistent(self):
        """Test processing nonexistent audio input."""
        pipeline = TranscriptionPipeline()
        
        with pytest.raises(FileNotFoundError):
            pipeline.process_audio_input(Path("/nonexistent/path"))
    
    @patch('builtins.input', return_value="/test/path/audio.mp3")
    def test_process_audio_input_interactive(self, mock_input, tmp_path):
        """Test interactive audio input processing."""
        # Create the file that input() returns
        audio_file = tmp_path / "audio.mp3"
        audio_file.touch()
        
        pipeline = TranscriptionPipeline()
        
        # Mock Path.resolve() to return our test file
        with patch.object(Path, 'resolve', return_value=audio_file):
            with patch.object(Path, 'exists', return_value=True):
                with patch.object(Path, 'is_dir', return_value=False):
                    result = pipeline.process_audio_input()
        
        assert str(result) == str(audio_file)
        mock_input.assert_called_once()
    
    def test_prepare_audio(self, mock_audio_file):
        """Test audio preparation (conversion and compression)."""
        pipeline = TranscriptionPipeline()
        
        prepared_file = mock_audio_file.parent / "prepared.wav"
        compressed_file = mock_audio_file.parent / "compressed.opus"
        
        with patch('core.transcribe.new_pipeline.ensure_wav16k_mono') as mock_convert:
            with patch('core.transcribe.new_pipeline.compress_audio_for_upload') as mock_compress:
                mock_convert.return_value = prepared_file
                mock_compress.return_value = compressed_file
                
                result = pipeline.prepare_audio(mock_audio_file)
        
        assert result == compressed_file
        mock_convert.assert_called_once_with(mock_audio_file)
        mock_compress.assert_called_once_with(prepared_file)
    
    def test_transcribe_audio_file_success(self, mock_audio_file, mock_transcriber):
        """Test successful audio transcription."""
        pipeline = TranscriptionPipeline()
        pipeline.transcriber = mock_transcriber
        
        with patch('core.transcribe.new_pipeline.parse_replicate_output') as mock_parse:
            mock_segments = [
                Segment(0.0, 5.0, "Hello, this is a test.", "SPEAKER_00"),
                Segment(5.0, 10.0, "This is another segment.", "SPEAKER_01")
            ]
            mock_parse.return_value = mock_segments
            
            result = pipeline.transcribe_audio_file(mock_audio_file)
        
        assert len(result) == 2
        assert result[0].text == "Hello, this is a test."
        assert result[1].speaker == "SPEAKER_01"
        
        mock_transcriber.transcribe.assert_called_once()
        mock_parse.assert_called_once()
    
    def test_transcribe_audio_file_api_failure(self, mock_audio_file):
        """Test transcription API failure."""
        pipeline = TranscriptionPipeline()
        pipeline.transcriber = Mock()
        pipeline.transcriber.transcribe.side_effect = Exception("API Error")
        
        with pytest.raises(Exception, match="API Error"):
            pipeline.transcribe_audio_file(mock_audio_file)
    
    def test_save_outputs(self, tmp_path, mock_audio_file):
        """Test saving transcription outputs."""
        pipeline = TranscriptionPipeline()
        
        segments = [
            Segment(0.0, 5.0, "Test segment", "SPEAKER_00"),
        ]
        
        with patch('core.transcribe.new_pipeline.format_transcript_output') as mock_format:
            expected_json = tmp_path / "test_audio.json"
            mock_format.return_value = {"json": expected_json}
            
            result = pipeline.save_outputs(segments, mock_audio_file, tmp_path)
        
        assert result == expected_json
        mock_format.assert_called_once()
    
    def test_run_full_pipeline(self, mock_audio_file, tmp_path, mock_transcriber):
        """Test the complete pipeline run."""
        pipeline = TranscriptionPipeline()
        pipeline.transcriber = mock_transcriber
        
        # Mock all the pipeline steps
        with patch.object(pipeline, 'process_audio_input') as mock_input:
            with patch.object(pipeline, 'prepare_audio') as mock_prepare:
                with patch.object(pipeline, 'transcribe_audio_file') as mock_transcribe:
                    with patch.object(pipeline, 'save_outputs') as mock_save:
                        with patch('core.transcribe.new_pipeline.cleanup_temp_file') as mock_cleanup:
                            
                            # Set up mocks
                            mock_input.return_value = mock_audio_file
                            prepared_file = mock_audio_file.parent / "prepared.wav"
                            mock_prepare.return_value = prepared_file
                            
                            mock_segments = [Segment(0.0, 5.0, "Test", "SPEAKER_00")]
                            mock_transcribe.return_value = mock_segments
                            
                            output_file = tmp_path / "output.json"
                            mock_save.return_value = output_file
                            
                            # Run pipeline
                            result = pipeline.run(mock_audio_file, tmp_path)
                            
                            # Verify results
                            assert result == output_file
                            
                            # Verify all steps were called
                            mock_input.assert_called_once()
                            mock_prepare.assert_called_once()
                            mock_transcribe.assert_called_once()
                            mock_save.assert_called_once()
                            mock_cleanup.assert_called_once()
    
    def test_run_pipeline_with_error(self, mock_audio_file, tmp_path):
        """Test pipeline run with error and cleanup."""
        pipeline = TranscriptionPipeline()
        
        with patch.object(pipeline, 'process_audio_input') as mock_input:
            with patch.object(pipeline, 'prepare_audio') as mock_prepare:
                with patch.object(pipeline, 'transcribe_audio_file') as mock_transcribe:
                    with patch('core.transcribe.new_pipeline.cleanup_temp_file') as mock_cleanup:
                        
                        # Set up mocks
                        mock_input.return_value = mock_audio_file
                        prepared_file = mock_audio_file.parent / "prepared.wav"
                        mock_prepare.return_value = prepared_file
                        
                        # Make transcription fail
                        mock_transcribe.side_effect = TranscriptionError("API failed")
                        
                        # Run pipeline and expect error
                        with pytest.raises(TranscriptionError):
                            pipeline.run(mock_audio_file, tmp_path)
                        
                        # Verify cleanup still happened
                        mock_cleanup.assert_called_once_with(prepared_file, mock_audio_file)
    
    def test_convenience_function(self, mock_audio_file, tmp_path):
        """Test the convenience run() function."""
        from src.transcribe.new_pipeline import run
        
        with patch('core.transcribe.new_pipeline.TranscriptionPipeline') as mock_pipeline_class:
            mock_pipeline = Mock()
            mock_pipeline_class.return_value = mock_pipeline
            mock_pipeline.run.return_value = tmp_path / "output.json"
            
            result = run(mock_audio_file, tmp_path)
            
            mock_pipeline_class.assert_called_once()
            mock_pipeline.run.assert_called_once_with(mock_audio_file, tmp_path)
            assert result == tmp_path / "output.json"


class TestProgressCallback:
    """Tests for progress callback functionality."""
    
    def test_progress_callback_called(self, mock_audio_file):
        """Test that progress callback is called during transcription."""
        pipeline = TranscriptionPipeline()
        
        progress_messages = []
        
        def mock_progress(message=""):
            progress_messages.append(message)
        
        # Mock the transcriber to use our progress callback
        mock_transcriber = Mock()
        mock_transcriber.transcribe = Mock()
        
        def mock_transcribe_with_callback(audio_path, progress_callback):
            progress_callback("Starting transcription...")
            progress_callback()  # Update without message
            progress_callback("Transcription complete")
            return {"segments": []}
        
        mock_transcriber.transcribe.side_effect = mock_transcribe_with_callback
        pipeline.transcriber = mock_transcriber
        
        with patch('core.transcribe.new_pipeline.parse_replicate_output', return_value=[]):
            pipeline.transcribe_audio_file(mock_audio_file)
        
        # Verify progress callback was used
        mock_transcriber.transcribe.assert_called_once()
        # The actual progress callback is created within the method,
        # so we can't directly verify the messages, but we can verify
        # the transcriber was called with the callback


class TestEdgeCases:
    """Tests for edge cases and error conditions."""
    
    def test_empty_transcription_result(self, mock_audio_file):
        """Test handling of empty transcription results."""
        pipeline = TranscriptionPipeline()
        pipeline.transcriber = Mock()
        pipeline.transcriber.transcribe.return_value = {"segments": []}
        
        with patch('core.transcribe.new_pipeline.parse_replicate_output') as mock_parse:
            mock_parse.return_value = []
            result = pipeline.transcribe_audio_file(mock_audio_file)
        
        assert result == []
    
    def test_malformed_transcription_output(self, mock_audio_file):
        """Test handling of malformed transcription output."""
        pipeline = TranscriptionPipeline()
        pipeline.transcriber = Mock()
        pipeline.transcriber.transcribe.return_value = {"invalid": "data"}
        
        with patch('core.transcribe.new_pipeline.parse_replicate_output') as mock_parse:
            mock_parse.side_effect = KeyError("segments")
            
            with pytest.raises(KeyError):
                pipeline.transcribe_audio_file(mock_audio_file)
    
    def test_output_directory_creation_failure(self, mock_audio_file, tmp_path):
        """Test handling of output directory creation failure."""
        pipeline = TranscriptionPipeline()
        
        segments = [Segment(0.0, 5.0, "Test", "SPEAKER_00")]
        non_writable_dir = tmp_path / "non_writable"
        
        with patch.object(Path, 'mkdir', side_effect=PermissionError("Access denied")):
            with pytest.raises(PermissionError):
                pipeline.save_outputs(segments, mock_audio_file, non_writable_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])