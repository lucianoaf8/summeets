"""
Performance tests for the Summeets application.
Tests memory usage, execution time, and scalability with large files.
"""
import pytest
import time
import psutil
import threading
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import json
from contextlib import contextmanager


@contextmanager
def measure_time():
    """Context manager to measure execution time."""
    start_time = time.perf_counter()
    yield lambda: time.perf_counter() - start_time
    end_time = time.perf_counter()


@contextmanager
def measure_memory():
    """Context manager to measure memory usage."""
    process = psutil.Process()
    start_memory = process.memory_info().rss
    yield lambda: process.memory_info().rss - start_memory
    end_memory = process.memory_info().rss


class TestAudioProcessingPerformance:
    """Test performance of audio processing operations."""
    
    @pytest.fixture
    def large_audio_metadata(self):
        """Mock metadata for large audio file."""
        return {
            "duration": 3600.0,  # 1 hour
            "size": 100 * 1024 * 1024,  # 100MB
            "sample_rate": 44100,
            "channels": 2,
            "bit_rate": 192000
        }
    
    @patch('subprocess.run')
    def test_audio_extraction_performance(self, mock_run, large_audio_metadata):
        """Test audio extraction performance with large files."""
        from src.audio.ffmpeg_ops import extract_audio_from_video
        
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""
        
        input_file = Path("/test/large_video.mp4")
        output_file = Path("/test/extracted_audio.m4a")
        
        with measure_time() as get_duration:
            with measure_memory() as get_memory:
                # Mock ffprobe info
                with patch('src.audio.ffmpeg_ops.ffprobe_info') as mock_probe:
                    mock_probe.return_value = large_audio_metadata
                    
                    result = extract_audio_from_video(
                        input_file, output_file, 
                        format="m4a", quality="high"
                    )
        
        duration = get_duration()
        memory_used = get_memory()
        
        # Performance assertions
        assert duration < 5.0  # Should complete in under 5 seconds (mocked)
        assert memory_used < 50 * 1024 * 1024  # Should use less than 50MB extra RAM
        assert result == output_file
    
    @patch('subprocess.run')
    def test_audio_compression_performance(self, mock_run):
        """Test audio compression performance."""
        from src.audio.compression import compress_audio_for_upload
        
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""
        
        # Simulate large WAV file
        input_file = Path("/test/large_audio.wav")
        
        with measure_time() as get_duration:
            result = compress_audio_for_upload(
                input_file, 
                target_bitrate="64k"
            )
        
        duration = get_duration()
        
        # Should complete quickly (mocked operation)
        assert duration < 2.0
        assert result.suffix == ".opus"
    
    def test_audio_selection_performance(self):
        """Test performance of audio file ranking with many files."""
        from src.audio.selection import rank_audio_files
        
        # Create list of many mock audio files
        audio_files = []
        for i in range(100):
            audio_files.append(Path(f"/test/audio_{i}.mp3"))
        
        # Mock ffprobe for all files
        def mock_probe_side_effect(path):
            return {
                'duration': 300.0,
                'bit_rate': 128000 + (hash(str(path)) % 100000),  # Vary quality
                'sample_rate': 44100,
                'channels': 2,
                'size': 5000000
            }
        
        with measure_time() as get_duration:
            with patch('src.audio.ffmpeg_ops.ffprobe_info', side_effect=mock_probe_side_effect):
                ranked_files = rank_audio_files(audio_files)
        
        duration = get_duration()
        
        # Should handle 100 files quickly
        assert duration < 5.0
        assert len(ranked_files) == 100


class TestTranscriptionPerformance:
    """Test performance of transcription operations."""
    
    def test_transcript_chunking_performance(self):
        """Test performance of transcript chunking with large transcripts."""
        from src.summarize.pipeline import chunk_transcript
        
        # Create large transcript with many segments
        large_transcript = []
        for i in range(1000):  # 1000 segments
            large_transcript.append({
                "start": i * 10.0,
                "end": (i + 1) * 10.0,
                "text": f"This is segment number {i} with some sample text content.",
                "speaker": f"SPEAKER_{i % 5}",  # 5 different speakers
                "words": []
            })
        
        with measure_time() as get_duration:
            with measure_memory() as get_memory:
                chunks = chunk_transcript(large_transcript, chunk_seconds=300)
        
        duration = get_duration()
        memory_used = get_memory()
        
        # Performance assertions
        assert duration < 2.0  # Should chunk quickly
        assert memory_used < 20 * 1024 * 1024  # Should use less than 20MB
        assert len(chunks) > 1  # Should create multiple chunks
    
    @patch('src.transcribe.replicate_api.ReplicateTranscriber')
    def test_transcription_pipeline_performance(self, mock_transcriber_class):
        """Test transcription pipeline performance."""
        from src.transcribe.pipeline import TranscriptionPipeline
        
        # Mock fast transcription response
        mock_transcriber = Mock()
        mock_transcriber_class.return_value = mock_transcriber
        mock_transcriber.transcribe.return_value = {
            "segments": [
                {
                    "start": 0.0,
                    "end": 5.0,
                    "text": "Test transcription",
                    "speaker": "SPEAKER_00",
                    "words": []
                }
            ]
        }
        
        temp_dir = Path(tempfile.mkdtemp())
        audio_file = temp_dir / "test.mp3"
        audio_file.write_bytes(b"fake audio data")
        
        with measure_time() as get_duration:
            with patch('src.transcribe.pipeline.ensure_wav16k_mono'):
                with patch('src.transcribe.pipeline.compress_audio_for_upload'):
                    with patch('src.transcribe.pipeline.cleanup_temp_file'):
                        pipeline = TranscriptionPipeline()
                        result = pipeline.run(audio_file, temp_dir / "output")
        
        duration = get_duration()
        
        # Should complete quickly (mocked)
        assert duration < 3.0
        assert result is not None
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


class TestSummarizationPerformance:
    """Test performance of summarization operations."""
    
    @patch('src.providers.openai_client.summarize_text')
    def test_summarization_performance(self, mock_openai_summary):
        """Test summarization performance with large transcripts."""
        from src.summarize.pipeline import summarize_run
        
        # Mock fast summary response
        mock_openai_summary.return_value = {
            "summary": "Test summary content",
            "usage": {"total_tokens": 150},
            "model": "gpt-4o-mini"
        }
        
        # Create large transcript file
        temp_dir = Path(tempfile.mkdtemp())
        transcript_file = temp_dir / "large_transcript.json"
        
        large_transcript = []
        for i in range(500):  # 500 segments
            large_transcript.append({
                "start": i * 5.0,
                "end": (i + 1) * 5.0,
                "text": f"This is a longer segment of text number {i} with more content to test summarization performance.",
                "speaker": f"SPEAKER_{i % 3}",
                "words": []
            })
        
        transcript_file.write_text(json.dumps(large_transcript))
        output_dir = temp_dir / "output"
        output_dir.mkdir()
        
        with measure_time() as get_duration:
            with measure_memory() as get_memory:
                result = summarize_run(
                    transcript_path=transcript_file,
                    provider="openai",
                    model="gpt-4o-mini",
                    output_dir=output_dir,
                    chunk_seconds=300
                )
        
        duration = get_duration()
        memory_used = get_memory()
        
        # Performance assertions
        assert duration < 10.0  # Should complete in under 10 seconds
        assert memory_used < 100 * 1024 * 1024  # Should use less than 100MB
        assert result.exists()
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_chain_of_density_performance(self):
        """Test Chain-of-Density processing performance."""
        from src.summarize.pipeline import apply_chain_of_density
        
        initial_summary = "This is a basic summary. " * 100  # Long initial summary
        
        mock_cod_responses = []
        for i in range(3):  # 3 CoD passes
            mock_cod_responses.append({
                "summary": f"Refined summary pass {i+1}. " * 50,
                "usage": {"total_tokens": 200 + i * 50},
                "model": "gpt-4o-mini"
            })
        
        with measure_time() as get_duration:
            with patch('src.providers.openai_client.summarize_text') as mock_summary:
                mock_summary.side_effect = mock_cod_responses
                
                final_summary = apply_chain_of_density(
                    initial_summary=initial_summary,
                    provider="openai",
                    model="gpt-4o-mini",
                    api_key="test-key",
                    passes=3
                )
        
        duration = get_duration()
        
        # Should complete multiple passes quickly (mocked)
        assert duration < 2.0
        assert "Refined summary" in final_summary["summary"]


class TestWorkflowPerformance:
    """Test performance of complete workflows."""
    
    @patch('src.workflow.extract_audio_from_video')
    @patch('src.workflow.transcribe_run')
    @patch('src.workflow.summarize_run')
    def test_full_workflow_performance(self, mock_summarize, mock_transcribe, mock_extract):
        """Test performance of complete video-to-summary workflow."""
        from src.workflow import WorkflowEngine, WorkflowConfig
        
        temp_dir = Path(tempfile.mkdtemp())
        video_file = temp_dir / "test_video.mp4"
        output_dir = temp_dir / "output"
        
        video_file.write_bytes(b"fake video data")
        output_dir.mkdir()
        
        # Mock all operations
        mock_extract.return_value = temp_dir / "extracted.m4a"
        mock_transcribe.return_value = temp_dir / "transcript.json"
        mock_summarize.return_value = temp_dir / "summary.json"
        
        config = WorkflowConfig(
            input_file=video_file,
            output_dir=output_dir,
            provider="openai",
            model="gpt-4o-mini"
        )
        
        with measure_time() as get_duration:
            with measure_memory() as get_memory:
                with patch('src.utils.validation.validate_workflow_input') as mock_validate:
                    mock_validate.return_value = (video_file, "video")
                    
                    engine = WorkflowEngine(config)
                    results = engine.execute()
        
        duration = get_duration()
        memory_used = get_memory()
        
        # Performance assertions
        assert duration < 5.0  # Complete workflow in under 5 seconds
        assert memory_used < 150 * 1024 * 1024  # Use less than 150MB
        assert len(results) >= 2  # Should have multiple results
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_concurrent_workflow_performance(self):
        """Test performance of concurrent workflow execution."""
        from src.workflow import WorkflowEngine, WorkflowConfig
        
        temp_dir = Path(tempfile.mkdtemp())
        
        # Create multiple input files
        audio_files = []
        for i in range(5):
            audio_file = temp_dir / f"audio_{i}.mp3"
            audio_file.write_bytes(b"fake audio data")
            audio_files.append(audio_file)
        
        # Mock all operations to be fast
        with patch('src.workflow.transcribe_run') as mock_transcribe:
            with patch('src.workflow.summarize_run') as mock_summarize:
                mock_transcribe.return_value = temp_dir / "transcript.json"
                mock_summarize.return_value = temp_dir / "summary.json"
                
                def run_workflow(audio_file):
                    config = WorkflowConfig(
                        input_file=audio_file,
                        output_dir=temp_dir / "output",
                        extract_audio=False,
                        process_audio=False
                    )
                    
                    with patch('src.utils.validation.validate_workflow_input') as mock_validate:
                        mock_validate.return_value = (audio_file, "audio")
                        
                        engine = WorkflowEngine(config)
                        return engine.execute()
                
                # Run workflows concurrently
                with measure_time() as get_duration:
                    threads = []
                    for audio_file in audio_files:
                        thread = threading.Thread(target=run_workflow, args=(audio_file,))
                        threads.append(thread)
                        thread.start()
                    
                    for thread in threads:
                        thread.join()
        
        duration = get_duration()
        
        # Should handle 5 concurrent workflows efficiently
        assert duration < 10.0
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


class TestMemoryUsage:
    """Test memory usage patterns."""
    
    def test_large_transcript_memory_usage(self):
        """Test memory usage with very large transcripts."""
        # Simulate processing a very large transcript
        huge_transcript = []
        
        # Create transcript with 10,000 segments
        for i in range(10000):
            huge_transcript.append({
                "start": i * 1.0,
                "end": (i + 1) * 1.0,
                "text": f"Segment {i}: " + "word " * 20,  # ~100 words per segment
                "speaker": f"SPEAKER_{i % 10}",
                "words": [{"word": f"word_{j}", "start": i + j*0.1, "end": i + (j+1)*0.1} 
                         for j in range(20)]
            })
        
        with measure_memory() as get_memory_usage:
            # Process the large transcript
            total_words = 0
            for segment in huge_transcript:
                total_words += len(segment["words"])
                
            # Simulate chunking
            chunk_size = 1000
            chunks = [huge_transcript[i:i+chunk_size] 
                     for i in range(0, len(huge_transcript), chunk_size)]
        
        memory_used = get_memory_usage()
        
        # Should handle large transcript without excessive memory usage
        assert memory_used < 500 * 1024 * 1024  # Less than 500MB
        assert len(chunks) == 10  # Should create 10 chunks
        assert total_words == 200000  # 10k segments * 20 words each
    
    def test_memory_cleanup_after_processing(self):
        """Test that memory is properly cleaned up after processing."""
        import gc
        
        def create_large_data():
            # Create and process large data structure
            large_data = []
            for i in range(1000):
                large_data.append({
                    "id": i,
                    "content": "x" * 10000,  # 10KB per item
                    "metadata": {"key": "value"} * 100
                })
            return large_data
        
        # Measure memory before
        process = psutil.Process()
        memory_before = process.memory_info().rss
        
        # Create and process large data
        large_data = create_large_data()
        memory_during = process.memory_info().rss
        
        # Clean up
        del large_data
        gc.collect()
        memory_after = process.memory_info().rss
        
        # Memory should be released
        memory_increase = memory_during - memory_before
        memory_decrease = memory_during - memory_after
        
        assert memory_increase > 5 * 1024 * 1024  # Should have used > 5MB
        assert memory_decrease > memory_increase * 0.7  # Should free most memory
    
    def test_streaming_processing_memory_efficiency(self):
        """Test memory efficiency of streaming processing."""
        def process_transcript_streaming(segments):
            """Process transcript in streaming fashion to minimize memory usage."""
            results = []
            current_chunk = []
            chunk_size = 100  # Process 100 segments at a time
            
            for segment in segments:
                current_chunk.append(segment)
                
                if len(current_chunk) >= chunk_size:
                    # Process chunk and yield result
                    chunk_result = f"Processed {len(current_chunk)} segments"
                    results.append(chunk_result)
                    current_chunk = []  # Clear memory
            
            # Process remaining segments
            if current_chunk:
                chunk_result = f"Processed {len(current_chunk)} segments"
                results.append(chunk_result)
            
            return results
        
        # Create large transcript
        large_transcript = [
            {"id": i, "text": "content " * 100}  # Large content per segment
            for i in range(2000)
        ]
        
        with measure_memory() as get_memory_usage:
            results = process_transcript_streaming(large_transcript)
        
        memory_used = get_memory_usage()
        
        # Streaming should use less memory than batch processing
        assert memory_used < 100 * 1024 * 1024  # Less than 100MB
        assert len(results) == 20  # Should process in 20 chunks


class TestScalabilityLimits:
    """Test application behavior at scale limits."""
    
    def test_maximum_audio_duration_handling(self):
        """Test handling of very long audio files."""
        from src.utils.validation import validate_audio_duration
        
        # Test various durations
        test_durations = [
            60.0,      # 1 minute - should pass
            3600.0,    # 1 hour - should pass
            7200.0,    # 2 hours - at limit
            10800.0    # 3 hours - should fail
        ]
        
        for duration in test_durations:
            if duration <= 7200.0:  # 2 hours max
                # Should not raise exception
                result = validate_audio_duration(duration)
                assert result is True
            else:
                # Should raise exception for too long
                with pytest.raises(ValueError, match="too long"):
                    validate_audio_duration(duration)
    
    def test_maximum_transcript_segments_handling(self):
        """Test handling of transcripts with many segments."""
        segment_counts = [100, 1000, 5000, 10000]
        
        for count in segment_counts:
            # Create transcript with specified number of segments
            segments = []
            for i in range(count):
                segments.append({
                    "start": i * 1.0,
                    "end": (i + 1) * 1.0,
                    "text": f"Segment {i}",
                    "speaker": f"SPEAKER_{i % 5}"
                })
            
            with measure_time() as get_duration:
                # Simulate processing
                speaker_counts = {}
                for segment in segments:
                    speaker = segment["speaker"]
                    speaker_counts[speaker] = speaker_counts.get(speaker, 0) + 1
            
            duration = get_duration()
            
            # Should handle even large numbers of segments efficiently
            assert duration < 1.0  # Process any count in under 1 second
            assert len(speaker_counts) <= 5  # Should identify speakers correctly
    
    def test_concurrent_processing_limits(self):
        """Test limits of concurrent processing."""
        import threading
        import queue
        
        max_concurrent = 10
        task_queue = queue.Queue()
        results = []
        
        def worker():
            while True:
                try:
                    task = task_queue.get(timeout=1)
                    if task is None:
                        break
                    
                    # Simulate processing
                    time.sleep(0.1)
                    results.append(f"Processed task {task}")
                    task_queue.task_done()
                except queue.Empty:
                    break
        
        # Add tasks to queue
        for i in range(50):
            task_queue.put(i)
        
        # Start worker threads
        threads = []
        for _ in range(max_concurrent):
            thread = threading.Thread(target=worker)
            thread.start()
            threads.append(thread)
        
        # Wait for completion
        with measure_time() as get_duration:
            task_queue.join()
            
            # Signal threads to stop
            for _ in range(max_concurrent):
                task_queue.put(None)
            
            for thread in threads:
                thread.join()
        
        duration = get_duration()
        
        # Should process 50 tasks with 10 workers efficiently
        assert len(results) == 50
        assert duration < 10.0  # Should complete in reasonable time


if __name__ == "__main__":
    pytest.main([__file__, "-v"])