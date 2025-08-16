"""
Integration tests for the complete transcription pipeline.
Tests end-to-end transcription flow with realistic scenarios.
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json
import time

from core.transcribe.pipeline import TranscriptionPipeline, run as transcribe_run
from core.transcribe.replicate_api import ReplicateTranscriber
from core.transcribe.formatting import format_transcript_output, parse_replicate_output
from core.utils.exceptions import TranscriptionError, AudioProcessingError


class TestTranscriptionPipelineIntegration:
    """Integration tests for transcription pipeline."""
    
    @patch('core.transcribe.pipeline.ReplicateTranscriber')
    @patch('core.transcribe.pipeline.ensure_wav16k_mono')
    @patch('core.transcribe.pipeline.compress_audio_for_upload')
    @patch('core.transcribe.pipeline.cleanup_temp_file')
    def test_complete_transcription_pipeline(self, mock_cleanup, mock_compress, 
                                           mock_ensure_wav, mock_transcriber_class, 
                                           audio_file_samples, tmp_path):
        """Test complete transcription pipeline from audio to output files."""
        # Setup
        input_audio = audio_file_samples['.mp3']['path']
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Mock audio processing
        wav_file = tmp_path / "processed.wav"
        compressed_file = tmp_path / "compressed.opus"
        mock_ensure_wav.return_value = wav_file
        mock_compress.return_value = compressed_file
        
        # Mock transcriber
        mock_transcriber = Mock()
        mock_transcriber_class.return_value = mock_transcriber
        
        # Realistic transcription response
        transcription_response = {
            "segments": [
                {
                    "start": 0.0,
                    "end": 5.432,
                    "text": "Good morning everyone, welcome to our quarterly review meeting.",
                    "speaker": "SPEAKER_00",
                    "words": [
                        {"start": 0.0, "end": 0.5, "word": "Good"},
                        {"start": 0.5, "end": 1.0, "word": "morning"},
                        {"start": 1.0, "end": 1.8, "word": "everyone,"},
                        {"start": 1.8, "end": 2.5, "word": "welcome"},
                        {"start": 2.5, "end": 5.432, "word": "to our quarterly review meeting."}
                    ]
                },
                {
                    "start": 5.432,
                    "end": 12.156,
                    "text": "I'd like to start by reviewing our performance metrics from Q3.",
                    "speaker": "SPEAKER_00",
                    "words": [
                        {"start": 5.432, "end": 6.0, "word": "I'd"},
                        {"start": 6.0, "end": 6.5, "word": "like"},
                        {"start": 6.5, "end": 12.156, "word": "to start by reviewing our performance metrics from Q3."}
                    ]
                }
            ]
        }
        
        mock_transcriber.transcribe.return_value = transcription_response
        
        # Execute pipeline
        pipeline = TranscriptionPipeline()
        result = pipeline.run(input_audio, output_dir)
        
        # Verify results
        assert result.exists()
        assert result.suffix == '.json'
        assert result.parent == output_dir
        
        # Verify processing steps were called
        mock_ensure_wav.assert_called_once_with(input_audio)
        mock_compress.assert_called_once_with(wav_file)
        mock_transcriber.transcribe.assert_called_once_with(compressed_file, progress_callback=mock_transcriber.transcribe.call_args[1]['progress_callback'])
        mock_cleanup.assert_called_once_with(compressed_file, input_audio)
        
        # Verify output files were created (mocked in format_transcript_output)
        expected_base_name = input_audio.stem
        expected_json = output_dir / f"{expected_base_name}.json"
        
        with patch('core.transcribe.formatting.format_transcript_output') as mock_format:
            mock_format.return_value = {"json": expected_json}
            
            # Re-run just the save step to verify formatting
            from core.models import Segment
            segments = [
                Segment(0.0, 5.432, "Good morning everyone, welcome to our quarterly review meeting.", "SPEAKER_00"),
                Segment(5.432, 12.156, "I'd like to start by reviewing our performance metrics from Q3.", "SPEAKER_00")
            ]
            
            pipeline.save_outputs(segments, input_audio, output_dir)
            mock_format.assert_called_once()
    
    @patch('core.transcribe.pipeline.ReplicateTranscriber')
    def test_transcription_with_progress_tracking(self, mock_transcriber_class, 
                                                audio_file_samples, tmp_path):
        """Test transcription pipeline with progress tracking."""
        input_audio = audio_file_samples['.m4a']['path']
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Mock transcriber with progress simulation
        mock_transcriber = Mock()
        mock_transcriber_class.return_value = mock_transcriber
        
        progress_calls = []
        
        def mock_transcribe_with_progress(audio_path, progress_callback):
            # Simulate progress updates
            progress_callback("Uploading audio file...")
            time.sleep(0.1)  # Simulate processing time
            progress_callback("Processing with Whisper...")
            time.sleep(0.1)
            progress_callback("Running speaker diarization...")
            time.sleep(0.1)
            progress_callback("Finalizing transcription...")
            
            return {
                "segments": [
                    {
                        "start": 0.0,
                        "end": 3.0,
                        "text": "Test transcription with progress tracking.",
                        "speaker": "SPEAKER_00",
                        "words": []
                    }
                ]
            }
        
        mock_transcriber.transcribe.side_effect = mock_transcribe_with_progress
        
        # Track progress
        def track_progress(message=""):
            progress_calls.append(message)
        
        # Mock other pipeline components
        with patch('core.transcribe.pipeline.ensure_wav16k_mono') as mock_wav:
            with patch('core.transcribe.pipeline.compress_audio_for_upload') as mock_compress:
                with patch('core.transcribe.pipeline.cleanup_temp_file'):
                    mock_wav.return_value = tmp_path / "test.wav"
                    mock_compress.return_value = tmp_path / "test.opus"
                    
                    pipeline = TranscriptionPipeline()
                    result = pipeline.run(input_audio, output_dir)
                    
                    # Verify progress was tracked
                    assert len(progress_calls) >= 4  # At least 4 progress updates
                    assert any("Uploading" in call for call in progress_calls)
                    assert any("Whisper" in call for call in progress_calls)
                    assert any("diarization" in call for call in progress_calls)
    
    @patch('core.transcribe.pipeline.ReplicateTranscriber')
    def test_transcription_error_handling(self, mock_transcriber_class, 
                                        audio_file_samples, tmp_path):
        """Test transcription pipeline error handling."""
        input_audio = audio_file_samples['.mp3']['path']
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Mock transcriber with error
        mock_transcriber = Mock()
        mock_transcriber_class.return_value = mock_transcriber
        mock_transcriber.transcribe.side_effect = Exception("API Error: Rate limit exceeded")
        
        # Mock other pipeline components
        with patch('core.transcribe.pipeline.ensure_wav16k_mono') as mock_wav:
            with patch('core.transcribe.pipeline.compress_audio_for_upload') as mock_compress:
                with patch('core.transcribe.pipeline.cleanup_temp_file') as mock_cleanup:
                    mock_wav.return_value = tmp_path / "test.wav"
                    compressed_file = tmp_path / "test.opus"
                    mock_compress.return_value = compressed_file
                    
                    pipeline = TranscriptionPipeline()
                    
                    # Should raise error but still cleanup
                    with pytest.raises(Exception, match="API Error"):
                        pipeline.run(input_audio, output_dir)
                    
                    # Verify cleanup was called even on error
                    mock_cleanup.assert_called_once_with(compressed_file, input_audio)
    
    @patch('core.transcribe.replicate_api.replicate')
    def test_replicate_api_integration(self, mock_replicate, audio_file_samples):
        """Test Replicate API integration."""
        # Mock Replicate client
        mock_client = Mock()
        mock_replicate.Client.return_value = mock_client
        
        # Mock model and prediction
        mock_model = Mock()
        mock_version = Mock()
        mock_version.id = "test-version-123"
        mock_model.latest_version = mock_version
        mock_client.models.get.return_value = mock_model
        
        mock_prediction = Mock()
        mock_prediction.id = "test-prediction-456"
        mock_prediction.status = "starting"
        mock_client.predictions.create.return_value = mock_prediction
        
        # Mock prediction polling
        call_count = 0
        def mock_get_prediction(prediction_id):
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                mock_prediction.status = "processing"
                mock_prediction.logs = "Processing audio..."
                return mock_prediction
            elif call_count == 2:
                mock_prediction.status = "succeeded"
                mock_prediction.logs = "Transcription completed"
                mock_prediction.output = {
                    "segments": [
                        {
                            "start": 0.0,
                            "end": 5.0,
                            "text": "This is a test transcription from Replicate API.",
                            "speaker": "SPEAKER_00",
                            "words": []
                        }
                    ]
                }
                return mock_prediction
        
        mock_client.predictions.get.side_effect = mock_get_prediction
        
        # Test transcriber
        transcriber = ReplicateTranscriber(api_token="test-token")
        
        audio_file = audio_file_samples['.mp3']['path']
        result = transcriber.transcribe(audio_file)
        
        # Verify API calls
        mock_client.models.get.assert_called_once()
        mock_client.predictions.create.assert_called_once()
        assert mock_client.predictions.get.call_count == 2
        
        # Verify result
        assert "segments" in result
        assert len(result["segments"]) == 1
        assert result["segments"][0]["text"] == "This is a test transcription from Replicate API."
    
    def test_transcript_formatting_integration(self, sample_transcript_segments, tmp_path):
        """Test transcript formatting with multiple output formats."""
        from core.models import Segment
        from core.transcribe.formatting import format_transcript_output
        
        # Convert sample data to Segment objects
        segments = []
        for seg_data in sample_transcript_segments:
            segment = Segment(
                start=seg_data["start"],
                end=seg_data["end"],
                text=seg_data["text"],
                speaker=seg_data["speaker"],
                words=seg_data.get("words", [])
            )
            segments.append(segment)
        
        # Test formatting
        audio_file = tmp_path / "meeting.mp3"
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        result = format_transcript_output(segments, audio_file, output_dir)
        
        # Should create multiple formats
        assert "json" in result
        assert "srt" in result
        assert "txt" in result
        
        # Verify files exist
        assert result["json"].exists()
        assert result["srt"].exists()
        assert result["txt"].exists()
        
        # Verify JSON content
        with open(result["json"], 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        assert len(json_data) == len(segments)
        assert json_data[0]["text"] == segments[0].text
        assert json_data[0]["speaker"] == segments[0].speaker
        
        # Verify SRT content
        srt_content = result["srt"].read_text(encoding='utf-8')
        assert "SPEAKER_00" in srt_content
        assert "quarterly review meeting" in srt_content
        assert "-->" in srt_content  # SRT timestamp format
        
        # Verify TXT content
        txt_content = result["txt"].read_text(encoding='utf-8')
        assert "[SPEAKER_00]:" in txt_content
        assert "quarterly review meeting" in txt_content
    
    @patch('core.transcribe.pipeline.pick_best_audio')
    def test_directory_input_handling(self, mock_pick_audio, directory_with_mixed_files, tmp_path):
        """Test transcription pipeline with directory input."""
        directory = directory_with_mixed_files['directory']
        best_audio = directory_with_mixed_files['audio_files'][0]  # First audio file
        
        mock_pick_audio.return_value = best_audio
        
        # Mock the rest of the pipeline
        with patch('core.transcribe.pipeline.ReplicateTranscriber') as mock_transcriber_class:
            with patch('core.transcribe.pipeline.ensure_wav16k_mono') as mock_wav:
                with patch('core.transcribe.pipeline.compress_audio_for_upload') as mock_compress:
                    with patch('core.transcribe.pipeline.cleanup_temp_file'):
                        # Setup mocks
                        mock_transcriber = Mock()
                        mock_transcriber_class.return_value = mock_transcriber
                        mock_transcriber.transcribe.return_value = {"segments": []}
                        
                        mock_wav.return_value = tmp_path / "test.wav"
                        mock_compress.return_value = tmp_path / "test.opus"
                        
                        # Test pipeline
                        pipeline = TranscriptionPipeline()
                        
                        # Should process directory input
                        audio_file = pipeline.process_audio_input(directory)
                        
                        assert audio_file == best_audio
                        mock_pick_audio.assert_called_once_with(directory)
    
    def test_convenience_function_integration(self, audio_file_samples, tmp_path):
        """Test the convenience transcribe_run function."""
        input_audio = audio_file_samples['.wav']['path']
        output_dir = tmp_path / "output"
        
        # Mock the pipeline
        with patch('core.transcribe.pipeline.TranscriptionPipeline') as mock_pipeline_class:
            mock_pipeline = Mock()
            mock_pipeline_class.return_value = mock_pipeline
            
            expected_result = output_dir / "result.json"
            mock_pipeline.run.return_value = expected_result
            
            # Test convenience function
            result = transcribe_run(input_audio, output_dir)
            
            assert result == expected_result
            mock_pipeline_class.assert_called_once()
            mock_pipeline.run.assert_called_once_with(input_audio, output_dir)
    
    def test_large_file_handling(self, large_audio_file_mock, tmp_path):
        """Test transcription pipeline with large audio files."""
        # Simulate large file processing
        large_file_metadata = large_audio_file_mock
        
        with patch('core.transcribe.pipeline.ReplicateTranscriber') as mock_transcriber_class:
            with patch('core.transcribe.pipeline.ensure_wav16k_mono') as mock_wav:
                with patch('core.transcribe.pipeline.compress_audio_for_upload') as mock_compress:
                    with patch('core.transcribe.pipeline.cleanup_temp_file'):
                        # Mock file size check
                        with patch('pathlib.Path.stat') as mock_stat:
                            mock_stat.return_value.st_size = large_file_metadata['size']
                            
                            # Mock transcriber
                            mock_transcriber = Mock()
                            mock_transcriber_class.return_value = mock_transcriber
                            
                            # Should handle large files by compression
                            mock_wav.return_value = tmp_path / "large.wav"
                            mock_compress.return_value = tmp_path / "large_compressed.opus"
                            
                            # Mock successful transcription
                            mock_transcriber.transcribe.return_value = {"segments": []}
                            
                            pipeline = TranscriptionPipeline()
                            
                            # Create mock file path
                            large_file_path = Path(large_file_metadata['path'])
                            
                            # Should process successfully
                            result = pipeline.prepare_audio(large_file_path)
                            
                            # Verify compression was used
                            mock_compress.assert_called_once()
                            assert str(result).endswith('.opus')


class TestTranscriptionEdgeCases:
    """Test transcription pipeline edge cases and error scenarios."""
    
    def test_empty_transcription_result(self, audio_file_samples, tmp_path):
        """Test handling of empty transcription results."""
        input_audio = audio_file_samples['.mp3']['path']
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        with patch('core.transcribe.pipeline.ReplicateTranscriber') as mock_transcriber_class:
            with patch('core.transcribe.pipeline.ensure_wav16k_mono'):
                with patch('core.transcribe.pipeline.compress_audio_for_upload'):
                    with patch('core.transcribe.pipeline.cleanup_temp_file'):
                        # Mock empty transcription result
                        mock_transcriber = Mock()
                        mock_transcriber_class.return_value = mock_transcriber
                        mock_transcriber.transcribe.return_value = {"segments": []}
                        
                        pipeline = TranscriptionPipeline()
                        result = pipeline.run(input_audio, output_dir)
                        
                        # Should still create output files even with empty result
                        assert result.exists()
    
    def test_malformed_transcription_output(self, audio_file_samples, tmp_path):
        """Test handling of malformed transcription output."""
        input_audio = audio_file_samples['.mp3']['path']
        
        with patch('core.transcribe.pipeline.ReplicateTranscriber') as mock_transcriber_class:
            # Mock malformed response
            mock_transcriber = Mock()
            mock_transcriber_class.return_value = mock_transcriber
            mock_transcriber.transcribe.return_value = {"invalid": "format"}
            
            pipeline = TranscriptionPipeline()
            
            with pytest.raises(Exception):  # Should fail on malformed data
                pipeline.transcribe_audio_file(input_audio)
    
    def test_network_timeout_handling(self, audio_file_samples):
        """Test handling of network timeouts."""
        input_audio = audio_file_samples['.mp3']['path']
        
        with patch('core.transcribe.pipeline.ReplicateTranscriber') as mock_transcriber_class:
            # Mock network timeout
            mock_transcriber = Mock()
            mock_transcriber_class.return_value = mock_transcriber
            
            from requests.exceptions import Timeout
            mock_transcriber.transcribe.side_effect = Timeout("Request timeout")
            
            pipeline = TranscriptionPipeline()
            
            with pytest.raises(Timeout):
                pipeline.transcribe_audio_file(input_audio)
    
    def test_insufficient_disk_space(self, audio_file_samples, tmp_path):
        """Test handling of insufficient disk space."""
        input_audio = audio_file_samples['.mp3']['path']
        output_dir = tmp_path / "output"
        
        # Mock disk space error during file writing
        with patch('core.transcribe.formatting.format_transcript_output') as mock_format:
            mock_format.side_effect = OSError("No space left on device")
            
            with patch('core.transcribe.pipeline.ReplicateTranscriber') as mock_transcriber_class:
                mock_transcriber = Mock()
                mock_transcriber_class.return_value = mock_transcriber
                mock_transcriber.transcribe.return_value = {"segments": []}
                
                pipeline = TranscriptionPipeline()
                
                with pytest.raises(OSError, match="No space left on device"):
                    pipeline.run(input_audio, output_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])