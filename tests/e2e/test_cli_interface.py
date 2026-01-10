"""
End-to-end tests for the CLI interface.
Tests complete CLI workflows with realistic scenarios and mocked external services.
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json
import tempfile
import subprocess
from typer.testing import CliRunner

from cli.app import app, main
from src.utils.exceptions import SummeetsError


class TestCLIBasicCommands:
    """Test basic CLI command functionality."""
    
    def setup_method(self):
        """Set up CLI runner for each test."""
        self.runner = CliRunner()
    
    def test_cli_help_command(self):
        """Test CLI help output."""
        result = self.runner.invoke(app, ["--help"])
        
        assert result.exit_code == 0
        assert "Summeets" in result.stdout
        assert "transcribe" in result.stdout
        assert "summarize" in result.stdout
        assert "process" in result.stdout
    
    def test_cli_version_command(self):
        """Test CLI version output."""
        result = self.runner.invoke(app, ["--version"])
        
        assert result.exit_code == 0
        assert "Summeets" in result.stdout
    
    def test_cli_config_command(self):
        """Test CLI config display."""
        with patch.dict('os.environ', {
            'OPENAI_API_KEY': 'test-key',
            'LLM_PROVIDER': 'openai',
            'LLM_MODEL': 'gpt-4o-mini'
        }):
            result = self.runner.invoke(app, ["config"])
            
            assert result.exit_code == 0
            assert "LLM Provider" in result.stdout
            assert "openai" in result.stdout


class TestCLIAudioCommands:
    """Test CLI audio processing commands."""
    
    def setup_method(self):
        """Set up CLI runner and test data."""
        self.runner = CliRunner()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test data."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('core.audio.ffmpeg_ops.probe')
    def test_cli_probe_command(self, mock_probe):
        """Test CLI probe command."""
        # Create test audio file
        audio_file = self.temp_dir / "test.mp3"
        audio_file.write_bytes(b"fake audio data")
        
        mock_probe.return_value = "Duration: 00:05:00.00, Audio: mp3, 44100 Hz"
        
        result = self.runner.invoke(app, ["probe", str(audio_file)])
        
        assert result.exit_code == 0
        assert "Duration" in result.stdout
        assert "Audio" in result.stdout
        mock_probe.assert_called_once_with(str(audio_file))
    
    @patch('core.audio.ffmpeg_ops.normalize_loudness')
    def test_cli_normalize_command(self, mock_normalize):
        """Test CLI normalize command."""
        input_file = self.temp_dir / "input.mp3"
        output_file = self.temp_dir / "output.mp3"
        input_file.write_bytes(b"fake audio data")
        
        result = self.runner.invoke(app, [
            "normalize", 
            str(input_file), 
            str(output_file)
        ])
        
        assert result.exit_code == 0
        mock_normalize.assert_called_once()
    
    @patch('core.audio.ffmpeg_ops.extract_audio_from_video')
    def test_cli_extract_command(self, mock_extract):
        """Test CLI extract command."""
        video_file = self.temp_dir / "video.mp4"
        audio_file = self.temp_dir / "audio.m4a"
        video_file.write_bytes(b"fake video data")
        
        mock_extract.return_value = audio_file
        
        result = self.runner.invoke(app, [
            "extract",
            str(video_file),
            str(audio_file),
            "--codec", "aac"
        ])
        
        assert result.exit_code == 0
        mock_extract.assert_called_once()
        call_args = mock_extract.call_args
        assert call_args[0][0] == video_file
        assert call_args[0][1] == audio_file
    
    def test_cli_extract_invalid_file(self):
        """Test CLI extract with invalid input file."""
        nonexistent_file = self.temp_dir / "nonexistent.mp4"
        output_file = self.temp_dir / "output.m4a"
        
        result = self.runner.invoke(app, [
            "extract",
            str(nonexistent_file),
            str(output_file)
        ])
        
        assert result.exit_code != 0
        assert "does not exist" in result.stdout


class TestCLITranscriptionCommands:
    """Test CLI transcription functionality."""
    
    def setup_method(self):
        """Set up CLI runner and test data."""
        self.runner = CliRunner()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test data."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('core.transcribe.pipeline.transcribe_run')
    def test_cli_transcribe_command(self, mock_transcribe):
        """Test CLI transcribe command."""
        audio_file = self.temp_dir / "meeting.mp3"
        output_dir = self.temp_dir / "output"
        transcript_file = output_dir / "meeting.json"
        
        audio_file.write_bytes(b"fake audio data")
        output_dir.mkdir()
        
        mock_transcribe.return_value = transcript_file
        
        with patch.dict('os.environ', {'REPLICATE_API_TOKEN': 'test-token'}):
            result = self.runner.invoke(app, [
                "transcribe",
                str(audio_file),
                "--output-dir", str(output_dir)
            ])
        
        assert result.exit_code == 0
        mock_transcribe.assert_called_once()
        call_args = mock_transcribe.call_args
        assert call_args[1]['transcript_path'] == audio_file
        assert call_args[1]['output_dir'] == output_dir
    
    @patch('core.transcribe.pipeline.transcribe_run')
    def test_cli_transcribe_with_options(self, mock_transcribe):
        """Test CLI transcribe with custom options."""
        audio_file = self.temp_dir / "meeting.wav"
        output_dir = self.temp_dir / "output"
        transcript_file = output_dir / "meeting.json"
        
        audio_file.write_bytes(b"fake audio data")
        output_dir.mkdir()
        
        mock_transcribe.return_value = transcript_file
        
        with patch.dict('os.environ', {'REPLICATE_API_TOKEN': 'test-token'}):
            result = self.runner.invoke(app, [
                "transcribe",
                str(audio_file),
                "--output-dir", str(output_dir),
                "--model", "custom-model",
                "--language", "es"
            ])
        
        assert result.exit_code == 0
        call_args = mock_transcribe.call_args
        assert call_args[1]['model'] == "custom-model"
        assert call_args[1]['language'] == "es"
    
    def test_cli_transcribe_missing_api_key(self):
        """Test CLI transcribe without API key."""
        audio_file = self.temp_dir / "meeting.mp3"
        audio_file.write_bytes(b"fake audio data")
        
        with patch.dict('os.environ', {}, clear=True):
            result = self.runner.invoke(app, [
                "transcribe",
                str(audio_file)
            ])
        
        assert result.exit_code != 0
        assert "API token" in result.stdout or "API key" in result.stdout


class TestCLISummarizationCommands:
    """Test CLI summarization functionality."""
    
    def setup_method(self):
        """Set up CLI runner and test data."""
        self.runner = CliRunner()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test data."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('core.summarize.pipeline.summarize_run')
    def test_cli_summarize_command(self, mock_summarize):
        """Test CLI summarize command with OpenAI."""
        # Create test transcript file
        transcript_file = self.temp_dir / "transcript.json"
        output_dir = self.temp_dir / "output"
        summary_file = output_dir / "transcript.summary.json"
        
        transcript_data = {
            "segments": [
                {
                    "start": 0.0,
                    "end": 5.0,
                    "text": "Meeting started",
                    "speaker": "SPEAKER_00"
                }
            ]
        }
        transcript_file.write_text(json.dumps(transcript_data))
        output_dir.mkdir()
        
        mock_summarize.return_value = summary_file
        
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            result = self.runner.invoke(app, [
                "summarize",
                str(transcript_file),
                "--provider", "openai",
                "--model", "gpt-4o-mini",
                "--output-dir", str(output_dir)
            ])
        
        assert result.exit_code == 0
        mock_summarize.assert_called_once()
        call_args = mock_summarize.call_args
        assert call_args[1]['transcript_path'] == transcript_file
        assert call_args[1]['provider'] == "openai"
        assert call_args[1]['model'] == "gpt-4o-mini"
    
    @patch('core.summarize.pipeline.summarize_run')
    def test_cli_summarize_anthropic(self, mock_summarize):
        """Test CLI summarize command with Anthropic."""
        transcript_file = self.temp_dir / "transcript.json"
        output_dir = self.temp_dir / "output"
        summary_file = output_dir / "transcript.summary.json"
        
        transcript_data = {"segments": []}
        transcript_file.write_text(json.dumps(transcript_data))
        output_dir.mkdir()
        
        mock_summarize.return_value = summary_file
        
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            result = self.runner.invoke(app, [
                "summarize",
                str(transcript_file),
                "--provider", "anthropic",
                "--model", "claude-3-haiku",
                "--template", "decision"
            ])
        
        assert result.exit_code == 0
        call_args = mock_summarize.call_args
        assert call_args[1]['provider'] == "anthropic"
        assert call_args[1]['model'] == "claude-3-haiku"
        assert call_args[1]['template'] == "decision"
    
    def test_cli_summarize_invalid_transcript(self):
        """Test CLI summarize with invalid transcript file."""
        nonexistent_file = self.temp_dir / "nonexistent.json"
        
        result = self.runner.invoke(app, [
            "summarize",
            str(nonexistent_file),
            "--provider", "openai"
        ])
        
        assert result.exit_code != 0
        assert "does not exist" in result.stdout
    
    def test_cli_summarize_missing_api_key(self):
        """Test CLI summarize without API key."""
        transcript_file = self.temp_dir / "transcript.json"
        transcript_file.write_text('{"segments": []}')
        
        with patch.dict('os.environ', {}, clear=True):
            result = self.runner.invoke(app, [
                "summarize",
                str(transcript_file),
                "--provider", "openai"
            ])
        
        assert result.exit_code != 0
        assert "API key" in result.stdout


class TestCLIWorkflowCommands:
    """Test CLI end-to-end workflow commands."""
    
    def setup_method(self):
        """Set up CLI runner and test data."""
        self.runner = CliRunner()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test data."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('core.workflow.execute_workflow')
    def test_cli_process_command_audio(self, mock_execute):
        """Test CLI process command with audio file."""
        audio_file = self.temp_dir / "meeting.mp3"
        output_dir = self.temp_dir / "output"
        
        audio_file.write_bytes(b"fake audio data")
        
        mock_execute.return_value = {
            "transcribe": self.temp_dir / "transcript.json",
            "summarize": self.temp_dir / "summary.json"
        }
        
        with patch.dict('os.environ', {
            'REPLICATE_API_TOKEN': 'test-token',
            'OPENAI_API_KEY': 'test-key'
        }):
            result = self.runner.invoke(app, [
                "process",
                str(audio_file),
                "--output-dir", str(output_dir),
                "--provider", "openai"
            ])
        
        assert result.exit_code == 0
        mock_execute.assert_called_once()
        
        # Verify workflow config
        call_args = mock_execute.call_args[0][0]
        assert call_args.input_file == audio_file
        assert call_args.output_dir == output_dir
        assert call_args.provider == "openai"
    
    @patch('core.workflow.execute_workflow')
    def test_cli_process_command_video(self, mock_execute):
        """Test CLI process command with video file."""
        video_file = self.temp_dir / "meeting.mp4"
        output_dir = self.temp_dir / "output"
        
        video_file.write_bytes(b"fake video data")
        
        mock_execute.return_value = {
            "extract_audio": self.temp_dir / "extracted.m4a",
            "transcribe": self.temp_dir / "transcript.json", 
            "summarize": self.temp_dir / "summary.json"
        }
        
        with patch.dict('os.environ', {
            'REPLICATE_API_TOKEN': 'test-token',
            'ANTHROPIC_API_KEY': 'test-key'
        }):
            result = self.runner.invoke(app, [
                "process",
                str(video_file),
                "--provider", "anthropic",
                "--model", "claude-3-sonnet",
                "--audio-format", "wav",
                "--increase-volume",
                "--template", "sop"
            ])
        
        assert result.exit_code == 0
        
        call_args = mock_execute.call_args[0][0]
        assert call_args.input_file == video_file
        assert call_args.provider == "anthropic"
        assert call_args.model == "claude-3-sonnet"
        assert call_args.audio_format == "wav"
        assert call_args.increase_volume is True
        assert call_args.template == "sop"
    
    @patch('core.workflow.execute_workflow')
    def test_cli_process_command_transcript_only(self, mock_execute):
        """Test CLI process command with transcript file."""
        transcript_file = self.temp_dir / "transcript.json"
        transcript_data = {"segments": []}
        transcript_file.write_text(json.dumps(transcript_data))
        
        mock_execute.return_value = {
            "summarize": self.temp_dir / "summary.json"
        }
        
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            result = self.runner.invoke(app, [
                "process",
                str(transcript_file),
                "--provider", "openai"
            ])
        
        assert result.exit_code == 0
        
        call_args = mock_execute.call_args[0][0]
        assert call_args.input_file == transcript_file
        assert call_args.extract_audio is False
        assert call_args.transcribe is False
        assert call_args.summarize is True
    
    def test_cli_process_progress_display(self):
        """Test CLI process command progress display."""
        audio_file = self.temp_dir / "meeting.mp3"
        audio_file.write_bytes(b"fake audio data")
        
        progress_calls = []
        
        def mock_execute_with_progress(config, progress_callback=None):
            if progress_callback:
                progress_callback(1, 3, "transcribe", "Transcribing audio...")
                progress_callback(2, 3, "summarize", "Creating summary...")
                progress_callback(3, 3, "complete", "Workflow completed")
            return {"transcribe": self.temp_dir / "transcript.json"}
        
        with patch('core.workflow.execute_workflow', side_effect=mock_execute_with_progress):
            with patch.dict('os.environ', {
                'REPLICATE_API_TOKEN': 'test-token',
                'OPENAI_API_KEY': 'test-key'
            }):
                result = self.runner.invoke(app, [
                    "process",
                    str(audio_file),
                    "--verbose"
                ])
        
        assert result.exit_code == 0
        assert "Transcribing" in result.stdout
        assert "Creating summary" in result.stdout
        assert "completed" in result.stdout


class TestCLIErrorHandling:
    """Test CLI error handling and edge cases."""
    
    def setup_method(self):
        """Set up CLI runner."""
        self.runner = CliRunner()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test data."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_cli_invalid_command(self):
        """Test CLI with invalid command."""
        result = self.runner.invoke(app, ["invalid-command"])
        
        assert result.exit_code != 0
        assert "No such command" in result.stdout
    
    def test_cli_missing_required_argument(self):
        """Test CLI with missing required arguments."""
        result = self.runner.invoke(app, ["transcribe"])
        
        assert result.exit_code != 0
        assert "Missing argument" in result.stdout
    
    def test_cli_invalid_file_path(self):
        """Test CLI with invalid file path."""
        result = self.runner.invoke(app, [
            "transcribe",
            "/nonexistent/path/audio.mp3"
        ])
        
        assert result.exit_code != 0
        assert "does not exist" in result.stdout
    
    def test_cli_invalid_provider(self):
        """Test CLI with invalid provider."""
        transcript_file = self.temp_dir / "transcript.json"
        transcript_file.write_text('{"segments": []}')
        
        result = self.runner.invoke(app, [
            "summarize",
            str(transcript_file),
            "--provider", "invalid-provider"
        ])
        
        assert result.exit_code != 0
        assert "Invalid value" in result.stdout
    
    def test_cli_invalid_model(self):
        """Test CLI with invalid model."""
        transcript_file = self.temp_dir / "transcript.json"
        transcript_file.write_text('{"segments": []}')
        
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            result = self.runner.invoke(app, [
                "summarize",
                str(transcript_file),
                "--provider", "openai",
                "--model", "invalid-model"
            ])
        
        assert result.exit_code != 0
    
    @patch('core.workflow.execute_workflow')
    def test_cli_workflow_error(self, mock_execute):
        """Test CLI workflow with execution error."""
        audio_file = self.temp_dir / "meeting.mp3"
        audio_file.write_bytes(b"fake audio data")
        
        mock_execute.side_effect = SummeetsError("Workflow execution failed")
        
        with patch.dict('os.environ', {
            'REPLICATE_API_TOKEN': 'test-token',
            'OPENAI_API_KEY': 'test-key'
        }):
            result = self.runner.invoke(app, [
                "process",
                str(audio_file)
            ])
        
        assert result.exit_code != 0
        assert "failed" in result.stdout.lower()
    
    def test_cli_output_directory_creation(self):
        """Test CLI creates output directory if it doesn't exist."""
        audio_file = self.temp_dir / "meeting.mp3"
        nonexistent_dir = self.temp_dir / "new_output"
        
        audio_file.write_bytes(b"fake audio data")
        
        with patch('core.workflow.execute_workflow') as mock_execute:
            mock_execute.return_value = {}
            
            with patch.dict('os.environ', {
                'REPLICATE_API_TOKEN': 'test-token',
                'OPENAI_API_KEY': 'test-key'
            }):
                result = self.runner.invoke(app, [
                    "process",
                    str(audio_file),
                    "--output-dir", str(nonexistent_dir)
                ])
        
        # Should succeed and create directory
        assert result.exit_code == 0
        assert nonexistent_dir.exists()


class TestCLIIntegrationScenarios:
    """Test realistic CLI usage scenarios."""
    
    def setup_method(self):
        """Set up CLI runner and test environment."""
        self.runner = CliRunner()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test data."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_cli_full_workflow_audio_to_summary(self):
        """Test complete workflow from audio to summary."""
        # Create test files
        audio_file = self.temp_dir / "meeting.mp3"
        output_dir = self.temp_dir / "output"
        transcript_file = output_dir / "meeting.json"
        summary_file = output_dir / "meeting.summary.json"
        
        audio_file.write_bytes(b"fake audio data")
        output_dir.mkdir()
        
        # Mock the complete workflow
        with patch('core.workflow.execute_workflow') as mock_execute:
            mock_execute.return_value = {
                "transcribe": transcript_file,
                "summarize": summary_file
            }
            
            with patch.dict('os.environ', {
                'REPLICATE_API_TOKEN': 'test-token',
                'OPENAI_API_KEY': 'test-key'
            }):
                result = self.runner.invoke(app, [
                    "process",
                    str(audio_file),
                    "--output-dir", str(output_dir),
                    "--provider", "openai",
                    "--model", "gpt-4o-mini",
                    "--template", "default",
                    "--verbose"
                ])
        
        assert result.exit_code == 0
        assert "Processing complete" in result.stdout or "completed" in result.stdout
        mock_execute.assert_called_once()
        
        # Verify configuration
        config = mock_execute.call_args[0][0]
        assert config.input_file == audio_file
        assert config.output_dir == output_dir
        assert config.provider == "openai"
        assert config.model == "gpt-4o-mini"
        assert config.template == "default"
    
    def test_cli_batch_processing_simulation(self):
        """Test CLI simulation of batch processing multiple files."""
        # Create multiple test audio files
        audio_files = []
        for i in range(3):
            audio_file = self.temp_dir / f"meeting_{i}.mp3"
            audio_file.write_bytes(b"fake audio data")
            audio_files.append(audio_file)
        
        output_dir = self.temp_dir / "batch_output"
        output_dir.mkdir()
        
        # Process each file
        with patch('core.workflow.execute_workflow') as mock_execute:
            mock_execute.return_value = {"transcribe": output_dir / "transcript.json"}
            
            with patch.dict('os.environ', {
                'REPLICATE_API_TOKEN': 'test-token',
                'ANTHROPIC_API_KEY': 'test-key'
            }):
                for audio_file in audio_files:
                    result = self.runner.invoke(app, [
                        "process",
                        str(audio_file),
                        "--output-dir", str(output_dir),
                        "--provider", "anthropic"
                    ])
                    
                    assert result.exit_code == 0
        
        # Should have been called once for each file
        assert mock_execute.call_count == 3
    
    def test_cli_pipeline_individual_steps(self):
        """Test running individual pipeline steps via CLI."""
        # Create test video file
        video_file = self.temp_dir / "presentation.mp4"
        audio_file = self.temp_dir / "presentation.m4a"
        transcript_file = self.temp_dir / "presentation.json"
        summary_file = self.temp_dir / "presentation.summary.json"
        
        video_file.write_bytes(b"fake video data")
        
        # Step 1: Extract audio
        with patch('core.audio.ffmpeg_ops.extract_audio_from_video') as mock_extract:
            mock_extract.return_value = audio_file
            
            result = self.runner.invoke(app, [
                "extract",
                str(video_file),
                str(audio_file),
                "--codec", "aac"
            ])
            
            assert result.exit_code == 0
        
        # Step 2: Transcribe (simulate audio file exists)
        audio_file.write_bytes(b"fake audio data")
        
        with patch('core.transcribe.pipeline.transcribe_run') as mock_transcribe:
            mock_transcribe.return_value = transcript_file
            
            with patch.dict('os.environ', {'REPLICATE_API_TOKEN': 'test-token'}):
                result = self.runner.invoke(app, [
                    "transcribe",
                    str(audio_file)
                ])
            
            assert result.exit_code == 0
        
        # Step 3: Summarize (simulate transcript exists)
        transcript_data = {"segments": [{"text": "test", "speaker": "SPEAKER_00"}]}
        transcript_file.write_text(json.dumps(transcript_data))
        
        with patch('core.summarize.pipeline.summarize_run') as mock_summarize:
            mock_summarize.return_value = summary_file
            
            with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
                result = self.runner.invoke(app, [
                    "summarize",
                    str(transcript_file),
                    "--provider", "openai"
                ])
            
            assert result.exit_code == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])