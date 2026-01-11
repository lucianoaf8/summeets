"""
Unit tests for the workflow engine.
Tests flexible pipeline execution, conditional steps, and file type handling.
"""
import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from src.workflow import (
    WorkflowStep, WorkflowConfig, WorkflowEngine, execute_workflow
)
from src.models import TranscriptData, SummaryData
from src.utils.exceptions import SummeetsError


class TestWorkflowStep:
    """Test WorkflowStep dataclass functionality."""

    def test_workflow_step_creation(self):
        """Test WorkflowStep creation."""
        def dummy_function(settings):
            return {"result": "success"}

        step = WorkflowStep(
            name="test_step",
            enabled=True,
            function=dummy_function,
            settings={"param1": "value1"},
            required_input_type="audio"
        )

        assert step.name == "test_step"
        assert step.enabled is True
        assert step.function == dummy_function
        assert step.settings == {"param1": "value1"}
        assert step.required_input_type == "audio"

    def test_workflow_step_can_execute_enabled(self):
        """Test step execution check when enabled and type matches."""
        step = WorkflowStep(
            name="test_step",
            enabled=True,
            function=lambda x: x,
            settings={},
            required_input_type="audio"
        )

        assert step.can_execute("audio") is True
        assert step.can_execute("video") is False

    def test_workflow_step_can_execute_disabled(self):
        """Test step execution check when disabled."""
        step = WorkflowStep(
            name="test_step",
            enabled=False,
            function=lambda x: x,
            settings={},
            required_input_type="audio"
        )

        assert step.can_execute("audio") is False
        assert step.can_execute("video") is False

    def test_workflow_step_can_execute_no_type_requirement(self):
        """Test step execution check with no type requirement."""
        step = WorkflowStep(
            name="test_step",
            enabled=True,
            function=lambda x: x,
            settings={},
            required_input_type=None
        )

        assert step.can_execute("audio") is True
        assert step.can_execute("video") is True
        assert step.can_execute("transcript") is True


class TestWorkflowConfig:
    """Test WorkflowConfig dataclass functionality."""

    def test_workflow_config_creation(self, tmp_path):
        """Test WorkflowConfig creation with defaults."""
        input_file = tmp_path / "input.mp3"
        output_dir = tmp_path / "output"

        config = WorkflowConfig(
            input_file=input_file,
            output_dir=output_dir
        )

        assert config.input_file == input_file
        assert config.output_dir == output_dir
        assert config.extract_audio is True
        assert config.process_audio is True
        assert config.transcribe is True
        assert config.summarize is True
        assert config.audio_format == "m4a"
        assert config.audio_quality == "high"
        assert config.output_formats == ["m4a"]

    def test_workflow_config_custom_settings(self, tmp_path):
        """Test WorkflowConfig with custom settings."""
        config = WorkflowConfig(
            input_file=tmp_path / "input.wav",
            output_dir=tmp_path / "output",
            extract_audio=False,
            process_audio=True,
            audio_format="wav",
            increase_volume=True,
            volume_gain_db=15.0,
            output_formats=["wav", "mp3"],
            transcribe_model="custom-model",
            provider="anthropic",
            model="claude-3-sonnet"
        )

        assert config.extract_audio is False
        assert config.process_audio is True
        assert config.audio_format == "wav"
        assert config.increase_volume is True
        assert config.volume_gain_db == 15.0
        assert config.output_formats == ["wav", "mp3"]
        assert config.transcribe_model == "custom-model"
        assert config.provider == "anthropic"
        assert config.model == "claude-3-sonnet"

    def test_workflow_config_post_init(self, tmp_path):
        """Test WorkflowConfig post-init processing (uses default_factory)."""
        # Test that default_factory creates default formats
        config = WorkflowConfig(
            input_file=tmp_path / "input.mp3",
            output_dir=tmp_path / "output"
            # output_formats omitted - should use default_factory
        )

        assert config.output_formats == ["m4a"]


class TestWorkflowEngine:
    """Test WorkflowEngine functionality."""

    def test_workflow_engine_initialization(self, tmp_path):
        """Test WorkflowEngine initialization."""
        input_file = tmp_path / "input.mp3"
        input_file.write_bytes(b"fake audio data")

        config = WorkflowConfig(
            input_file=input_file,
            output_dir=tmp_path / "output"
        )

        with patch('src.utils.validation.validate_workflow_input') as mock_validate:
            mock_validate.return_value = (input_file, "audio")

            engine = WorkflowEngine(config)

            assert engine.config == config
            assert engine.file_type == "audio"
            assert engine.current_audio_file is None
            assert engine.current_transcript is None
            assert engine.results == {}

    def test_workflow_engine_validate_config_audio_file(self, tmp_path):
        """Test config validation with audio file."""
        audio_file = tmp_path / "meeting.mp3"
        audio_file.write_bytes(b"fake audio content")
        output_dir = tmp_path / "output"

        config = WorkflowConfig(
            input_file=audio_file,
            output_dir=output_dir
        )

        with patch('src.utils.validation.validate_workflow_input') as mock_validate:
            mock_validate.return_value = (audio_file, "audio")

            engine = WorkflowEngine(config)

            assert engine.file_type == "audio"
            assert output_dir.exists()  # Should be created

    def test_workflow_engine_validate_config_video_file(self, tmp_path):
        """Test config validation with video file."""
        video_file = tmp_path / "meeting.mp4"
        video_file.write_bytes(b"fake video content")

        config = WorkflowConfig(
            input_file=video_file,
            output_dir=tmp_path / "output"
        )

        with patch('src.utils.validation.validate_workflow_input') as mock_validate:
            mock_validate.return_value = (video_file, "video")

            engine = WorkflowEngine(config)

            assert engine.file_type == "video"

    def test_workflow_engine_validate_config_transcript_file(self, tmp_path):
        """Test config validation with transcript file."""
        transcript_file = tmp_path / "transcript.json"
        transcript_file.write_text(json.dumps({"segments": []}))

        config = WorkflowConfig(
            input_file=transcript_file,
            output_dir=tmp_path / "output"
        )

        with patch('src.utils.validation.validate_workflow_input') as mock_validate:
            mock_validate.return_value = (transcript_file, "transcript")

            engine = WorkflowEngine(config)

            assert engine.file_type == "transcript"

    @pytest.mark.skip(reason="Implementation changed: _create_workflow_steps no longer exists")
    def test_create_workflow_steps(self, tmp_path):
        """Test workflow step creation."""
        input_file = tmp_path / "input.mp3"
        input_file.write_bytes(b"fake audio")

        config = WorkflowConfig(
            input_file=input_file,
            output_dir=tmp_path / "output"
        )

        with patch('src.utils.validation.validate_workflow_input') as mock_validate:
            mock_validate.return_value = (config.input_file, "audio")

            engine = WorkflowEngine(config)
            steps = engine._create_workflow_steps()

            assert len(steps) == 4
            step_names = [step.name for step in steps]
            assert "extract_audio" in step_names
            assert "process_audio" in step_names
            assert "transcribe" in step_names
            assert "summarize" in step_names

    @pytest.mark.skip(reason="Implementation changed: _create_workflow_steps no longer exists")
    def test_create_workflow_steps_disabled(self, tmp_path):
        """Test workflow step creation with disabled steps."""
        input_file = tmp_path / "input.mp3"
        input_file.write_bytes(b"fake audio")

        config = WorkflowConfig(
            input_file=input_file,
            output_dir=tmp_path / "output",
            extract_audio=False,
            process_audio=False
        )

        with patch('src.utils.validation.validate_workflow_input') as mock_validate:
            mock_validate.return_value = (config.input_file, "audio")

            engine = WorkflowEngine(config)
            steps = engine._create_workflow_steps()

            # Check that disabled steps are marked as disabled
            extract_step = next(s for s in steps if s.name == "extract_audio")
            process_step = next(s for s in steps if s.name == "process_audio")

            assert extract_step.enabled is False
            assert process_step.enabled is False

    @patch('src.workflow.transcribe_run')
    @patch('src.workflow.summarize_run')
    @patch('src.workflow.ensure_wav16k_mono')
    def test_execute_workflow_audio_file(self, mock_ensure_wav, mock_summarize, mock_transcribe, tmp_path):
        """Test workflow execution with audio file."""
        audio_file = tmp_path / "meeting.mp3"
        audio_file.write_bytes(b"fake audio data")
        output_dir = tmp_path / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        config = WorkflowConfig(
            input_file=audio_file,
            output_dir=output_dir,
            extract_audio=False,  # Skip for audio file
            process_audio=False   # Skip for simplicity
        )

        # Mock transcription and summarization
        transcript_file = output_dir / "transcript.json"
        summary_file = output_dir / "summary.md"
        wav_file = tmp_path / "meeting_16k.wav"

        mock_ensure_wav.return_value = wav_file
        mock_transcribe.return_value = transcript_file
        mock_summarize.return_value = (summary_file, None)  # Returns tuple

        with patch('src.utils.validation.validate_workflow_input') as mock_validate:
            mock_validate.return_value = (audio_file, "audio")

            engine = WorkflowEngine(config)
            results = engine.execute()

            assert "transcribe" in results
            assert "summarize" in results
            mock_transcribe.assert_called_once()
            mock_summarize.assert_called_once()

    @patch('src.workflow.extract_audio_from_video')
    @patch('src.workflow.transcribe_run')
    @patch('src.workflow.summarize_run')
    @patch('src.workflow.ensure_wav16k_mono')
    @patch('src.workflow.get_data_manager')
    def test_execute_workflow_video_file(self, mock_data_mgr, mock_ensure_wav, mock_summarize,
                                         mock_transcribe, mock_extract, tmp_path):
        """Test workflow execution with video file."""
        video_file = tmp_path / "meeting.mp4"
        video_file.write_bytes(b"fake video data")
        output_dir = tmp_path / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        config = WorkflowConfig(
            input_file=video_file,
            output_dir=output_dir,
            process_audio=False  # Skip for simplicity
        )

        # Mock extraction, transcription, and summarization
        extracted_audio = output_dir / "extracted.m4a"
        transcript_file = output_dir / "transcript.json"
        summary_file = output_dir / "summary.md"
        wav_file = tmp_path / "meeting_16k.wav"

        # Mock data manager
        mock_dm = Mock()
        mock_dm.get_audio_path.return_value = extracted_audio
        mock_data_mgr.return_value = mock_dm

        mock_extract.return_value = extracted_audio
        mock_ensure_wav.return_value = wav_file
        mock_transcribe.return_value = transcript_file
        mock_summarize.return_value = (summary_file, None)  # Returns tuple

        with patch('src.utils.validation.validate_workflow_input') as mock_validate:
            mock_validate.return_value = (video_file, "video")

            engine = WorkflowEngine(config)
            results = engine.execute()

            assert "extract_audio" in results
            assert "transcribe" in results
            assert "summarize" in results
            mock_extract.assert_called_once()
            mock_transcribe.assert_called_once()
            mock_summarize.assert_called_once()

    @patch('src.workflow.summarize_run')
    def test_execute_workflow_transcript_file(self, mock_summarize, tmp_path):
        """Test workflow execution with transcript file."""
        transcript_file = tmp_path / "transcript.json"
        transcript_data = {
            "segments": [
                {"start": 0.0, "end": 5.0, "text": "Hello world", "speaker": "SPEAKER_00"}
            ]
        }
        transcript_file.write_text(json.dumps(transcript_data))
        output_dir = tmp_path / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        config = WorkflowConfig(
            input_file=transcript_file,
            output_dir=output_dir
        )

        # Mock summarization - returns tuple
        summary_file = output_dir / "summary.md"
        mock_summarize.return_value = (summary_file, None)

        with patch('src.utils.validation.validate_workflow_input') as mock_validate:
            mock_validate.return_value = (transcript_file, "transcript")

            engine = WorkflowEngine(config)
            results = engine.execute()

            # Only summarization should actually run; other steps are skipped
            assert "summarize" in results
            # Extract audio isn't in results for transcript files (step doesn't run)
            # But process_audio and transcribe run but are skipped
            if "transcribe" in results:
                assert results["transcribe"].get("skipped") is True
            if "process_audio" in results:
                assert results["process_audio"].get("skipped") is True
            mock_summarize.assert_called_once()

    def test_execute_workflow_with_progress_callback(self, tmp_path):
        """Test workflow execution with progress callback."""
        audio_file = tmp_path / "meeting.mp3"
        audio_file.write_bytes(b"fake audio")

        config = WorkflowConfig(
            input_file=audio_file,
            output_dir=tmp_path / "output",
            extract_audio=False,
            process_audio=False,
            transcribe=False,
            summarize=False
        )

        progress_calls = []

        def progress_callback(step, total, step_name, status):
            progress_calls.append({
                'step': step,
                'total': total,
                'step_name': step_name,
                'status': status
            })

        with patch('src.utils.validation.validate_workflow_input') as mock_validate:
            mock_validate.return_value = (audio_file, "audio")

            engine = WorkflowEngine(config)
            results = engine.execute(progress_callback=progress_callback)

            # Should have final completion callback
            assert len(progress_calls) >= 1
            final_call = progress_calls[-1]
            assert final_call['step_name'] == "complete"
            assert final_call['status'] == "Workflow completed successfully"


class TestWorkflowSteps:
    """Test individual workflow step implementations."""

    @patch('src.workflow.extract_audio_from_video')
    @patch('src.workflow.get_data_manager')
    def test_extract_audio_step(self, mock_data_mgr, mock_extract, tmp_path):
        """Test extract audio workflow step."""
        video_file = tmp_path / "input.mp4"
        video_file.write_bytes(b"fake video")
        output_dir = tmp_path / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        config = WorkflowConfig(
            input_file=video_file,
            output_dir=output_dir
        )

        extracted_file = output_dir / "input_extracted.m4a"

        # Mock data manager
        mock_dm = Mock()
        mock_dm.get_audio_path.return_value = extracted_file
        mock_data_mgr.return_value = mock_dm

        mock_extract.return_value = extracted_file

        with patch('src.utils.validation.validate_workflow_input') as mock_validate:
            mock_validate.return_value = (video_file, "video")

            engine = WorkflowEngine(config)

            settings = {
                "format": "m4a",
                "quality": "high"
            }

            result = engine._extract_audio_step(settings)

            assert result["output_file"] == str(extracted_file)
            assert result["format"] == "m4a"
            assert result["quality"] == "high"
            assert engine.current_audio_file == extracted_file
            mock_extract.assert_called_once()

    def test_extract_audio_step_skip_for_audio(self, tmp_path):
        """Test extract audio step skips for audio files."""
        audio_file = tmp_path / "input.mp3"
        audio_file.write_bytes(b"fake audio")

        config = WorkflowConfig(
            input_file=audio_file,
            output_dir=tmp_path / "output"
        )

        with patch('src.utils.validation.validate_workflow_input') as mock_validate:
            mock_validate.return_value = (audio_file, "audio")

            engine = WorkflowEngine(config)

            result = engine._extract_audio_step({})

            assert result["skipped"] is True
            assert result["reason"] == "Not a video file"

    @patch('src.workflow.increase_audio_volume')
    @patch('src.workflow.normalize_loudness')
    @patch('src.workflow.convert_audio_format')
    @patch('src.workflow.get_data_manager')
    def test_process_audio_step(self, mock_data_mgr, mock_convert, mock_normalize, mock_volume, tmp_path):
        """Test process audio workflow step."""
        audio_file = tmp_path / "input.mp3"
        audio_file.write_bytes(b"fake audio")

        output_dir = tmp_path / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        config = WorkflowConfig(
            input_file=audio_file,
            output_dir=output_dir
        )

        # Mock processed files
        volume_file = output_dir / "input_volume.mp3"
        norm_file = output_dir / "input_volume_normalized.mp3"
        converted_file = output_dir / "input_volume_normalized.wav"

        # Mock data manager
        mock_dm = Mock()
        mock_dm.get_audio_path.side_effect = [volume_file, norm_file]
        mock_data_mgr.return_value = mock_dm

        mock_volume.return_value = volume_file
        # normalize_loudness doesn't return a value - it writes to output_path
        mock_normalize.return_value = None
        mock_convert.return_value = converted_file

        with patch('src.utils.validation.validate_workflow_input') as mock_validate:
            mock_validate.return_value = (audio_file, "audio")

            engine = WorkflowEngine(config)
            engine.current_audio_file = audio_file

            settings = {
                "increase_volume": True,
                "volume_gain_db": 12.0,
                "normalize_audio": True,
                "output_formats": ["wav"]
            }

            result = engine._process_audio_step(settings)

            assert len(result["processed_files"]) == 3  # volume, normalize, convert
            assert any(f["type"] == "volume_adjustment" for f in result["processed_files"])
            assert any(f["type"] == "normalization" for f in result["processed_files"])
            assert any(f["type"] == "format_conversion" for f in result["processed_files"])

            mock_volume.assert_called_once()
            mock_normalize.assert_called_once()
            mock_convert.assert_called_once()

    @patch('src.workflow.transcribe_run')
    @patch('src.workflow.ensure_wav16k_mono')
    def test_transcribe_step(self, mock_ensure_wav, mock_transcribe, tmp_path):
        """Test transcribe workflow step."""
        audio_file = tmp_path / "input.mp3"
        audio_file.write_bytes(b"fake audio")
        output_dir = tmp_path / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        config = WorkflowConfig(
            input_file=audio_file,
            output_dir=output_dir
        )

        # Mock transcription
        wav_file = tmp_path / "input_16k_mono.wav"
        transcript_file = output_dir / "transcript.json"

        mock_ensure_wav.return_value = wav_file
        mock_transcribe.return_value = transcript_file

        with patch('src.utils.validation.validate_workflow_input') as mock_validate:
            mock_validate.return_value = (audio_file, "audio")

            engine = WorkflowEngine(config)
            engine.current_audio_file = audio_file

            settings = {
                "model": "thomasmol/whisper-diarization",
                "language": "auto"
            }

            result = engine._transcribe_step(settings)

            assert result["transcript_file"] == str(transcript_file)
            assert result["model"] == "thomasmol/whisper-diarization"
            assert result["language"] == "auto"
            assert engine.current_transcript is not None

            mock_ensure_wav.assert_called_once_with(audio_file)
            mock_transcribe.assert_called_once()

    @patch('src.workflow.summarize_run')
    def test_summarize_step(self, mock_summarize, tmp_path):
        """Test summarize workflow step."""
        transcript_file = tmp_path / "transcript.json"
        transcript_file.write_text(json.dumps({"segments": []}))
        output_dir = tmp_path / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        config = WorkflowConfig(
            input_file=transcript_file,
            output_dir=output_dir
        )

        # Mock summarization - returns tuple (summary_file, metadata)
        summary_file = output_dir / "summary.md"
        mock_summarize.return_value = (summary_file, {"word_count": 100})

        with patch('src.utils.validation.validate_workflow_input') as mock_validate:
            mock_validate.return_value = (transcript_file, "transcript")

            engine = WorkflowEngine(config)
            # Set up transcript data
            engine.current_transcript = TranscriptData(
                segments=[],
                duration=0.0,
                output_file=transcript_file
            )

            settings = {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "template": "default"
            }

            result = engine._summarize_step(settings)

            assert result["summary_file"] == str(summary_file)
            assert result["provider"] == "openai"
            assert result["model"] == "gpt-4o-mini"
            assert result["template"] == "default"

            mock_summarize.assert_called_once()


class TestWorkflowErrorHandling:
    """Test workflow error handling and recovery."""

    def test_workflow_validation_error(self, tmp_path):
        """Test workflow with validation error."""
        nonexistent_file = tmp_path / "nonexistent.mp3"

        config = WorkflowConfig(
            input_file=nonexistent_file,
            output_dir=tmp_path / "output"
        )

        # The validation function is imported in workflow.py, so patch at that location
        # It raises FileNotFoundError for nonexistent files
        with pytest.raises(FileNotFoundError, match="does not exist"):
            WorkflowEngine(config)

    @patch('src.workflow.ensure_wav16k_mono')
    def test_workflow_step_error(self, mock_ensure_wav, tmp_path):
        """Test workflow with step execution error."""
        audio_file = tmp_path / "input.mp3"
        audio_file.write_bytes(b"fake audio")

        config = WorkflowConfig(
            input_file=audio_file,
            output_dir=tmp_path / "output",
            extract_audio=False,
            process_audio=False,
            summarize=False
        )

        with patch('src.utils.validation.validate_workflow_input') as mock_validate:
            mock_validate.return_value = (audio_file, "audio")

            with patch('src.workflow.transcribe_run') as mock_transcribe:
                mock_ensure_wav.return_value = audio_file
                mock_transcribe.side_effect = Exception("Transcription failed")

                engine = WorkflowEngine(config)

                with pytest.raises(SummeetsError, match="Error in step 'transcribe'"):
                    engine.execute()

    def test_workflow_missing_dependencies(self, tmp_path):
        """Test workflow with missing dependencies."""
        audio_file = tmp_path / "input.mp3"
        audio_file.write_bytes(b"fake audio")

        config = WorkflowConfig(
            input_file=audio_file,
            output_dir=tmp_path / "output"
        )

        with patch('src.utils.validation.validate_workflow_input') as mock_validate:
            mock_validate.return_value = (audio_file, "audio")

            engine = WorkflowEngine(config)

            # Try to run summarize step without transcript
            settings = {"provider": "openai", "model": "gpt-4o-mini"}

            with pytest.raises(SummeetsError, match="No transcript available"):
                engine._summarize_step(settings)


class TestWorkflowConvenienceFunction:
    """Test the convenience execute_workflow function."""

    @patch('src.workflow.WorkflowEngine')
    def test_execute_workflow_function(self, mock_engine_class, tmp_path):
        """Test execute_workflow convenience function."""
        config = WorkflowConfig(
            input_file=tmp_path / "input.mp3",
            output_dir=tmp_path / "output"
        )

        # Mock engine
        mock_engine = Mock()
        mock_engine.execute.return_value = {"test": "result"}
        mock_engine_class.return_value = mock_engine

        progress_callback = Mock()

        result = execute_workflow(config, progress_callback)

        assert result == {"test": "result"}
        mock_engine_class.assert_called_once_with(config)
        mock_engine.execute.assert_called_once_with(progress_callback)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
