"""
Integration tests for the complete summarization pipeline.
Tests end-to-end summarization with realistic transcript data and LLM providers.
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

from core.summarize.pipeline import (
    run as summarize_run, load_transcript, chunk_transcript,
    summarize_chunks, apply_chain_of_density, create_final_summary
)
from core.summarize.templates import SummaryTemplates, detect_meeting_type, format_sop_output
from core.models import SummaryTemplate
from core.utils.exceptions import SummarizationError, ProviderError


class TestSummarizationPipelineIntegration:
    """Integration tests for summarization pipeline."""
    
    @patch('core.providers.openai_client.create_openai_summary')
    def test_complete_summarization_pipeline_openai(self, mock_openai_summary, 
                                                   transcript_files, tmp_path):
        """Test complete summarization pipeline with OpenAI."""
        transcript_file = transcript_files['json']
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Mock OpenAI responses for different stages
        chunk_summaries = [
            {
                "summary": "Chunk 1: Meeting introduction and Q3 performance review discussion.",
                "usage": {"total_tokens": 150},
                "model": "gpt-4o-mini"
            },
            {
                "summary": "Chunk 2: Customer acquisition metrics and retention rate analysis.", 
                "usage": {"total_tokens": 180},
                "model": "gpt-4o-mini"
            }
        ]
        
        final_summary = {
            "summary": """# Quarterly Review Meeting Summary

## Executive Summary
This meeting covered Q3 performance metrics, with particular focus on customer acquisition and retention rates. The team discussed a 23% increase in new customers and analyzed retention performance.

## Key Points
- Customer acquisition: 1,247 new customers (23% increase from Q2)
- Discussion of retention rates and performance metrics
- Review of quarterly dashboard and KPIs

## Action Items
- Continue monitoring customer acquisition trends
- Follow up on retention rate analysis
- Schedule next quarterly review

## Participants
- SPEAKER_00: Meeting facilitator, presented metrics
- SPEAKER_01: Asked questions about customer acquisition
- SPEAKER_02: Inquired about retention rates""",
            "usage": {"total_tokens": 420},
            "model": "gpt-4o-mini"
        }
        
        # Set up mock responses in sequence
        mock_openai_summary.side_effect = chunk_summaries + [final_summary]
        
        # Run summarization
        result = summarize_run(
            transcript_path=transcript_file,
            provider="openai",
            model="gpt-4o-mini",
            output_dir=output_dir,
            chunk_seconds=30,  # Small chunks for testing
            cod_passes=1
        )
        
        # Verify result
        assert result.exists()
        assert result.suffix == '.json'
        
        # Verify OpenAI was called correctly
        assert mock_openai_summary.call_count == 3  # 2 chunks + 1 final
        
        # Verify output files were created
        base_name = transcript_file.stem
        expected_json = output_dir / f"{base_name}.summary.json"
        expected_md = output_dir / f"{base_name}.summary.md"
        
        assert expected_json.exists()
        assert expected_md.exists()
        
        # Verify content
        with open(expected_json, 'r', encoding='utf-8') as f:
            summary_data = json.load(f)
        
        assert summary_data["provider"] == "openai"
        assert summary_data["model"] == "gpt-4o-mini"
        assert "Executive Summary" in summary_data["summary"]
        assert len(summary_data["chunk_summaries"]) == 2
    
    @patch('core.providers.anthropic_client.create_anthropic_summary')
    def test_complete_summarization_pipeline_anthropic(self, mock_anthropic_summary,
                                                      transcript_files, tmp_path):
        """Test complete summarization pipeline with Anthropic."""
        transcript_file = transcript_files['json']
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Mock Anthropic responses
        chunk_summaries = [
            {
                "summary": "Initial discussion about quarterly performance and metrics review.",
                "usage": {"input_tokens": 200, "output_tokens": 80},
                "model": "claude-3-haiku"
            }
        ]
        
        final_summary = {
            "summary": """# Meeting Analysis - Quarterly Review

## Context and Purpose
This quarterly review meeting focused on analyzing Q3 performance metrics, with emphasis on customer acquisition growth and retention analysis.

## Key Insights
The discussion revealed strong performance in customer acquisition (23% growth) and highlighted the importance of continued monitoring of customer metrics.

## Detailed Findings
- **Customer Growth**: 1,247 new customers acquired in Q3
- **Performance Metrics**: Dashboard review showing positive trends
- **Team Engagement**: Active participation with targeted questions

## Recommendations
Continue current acquisition strategies while developing retention improvement plans for Q4.

## Meeting Participants
Three speakers participated: the meeting facilitator who presented metrics, and two team members who asked specific questions about customer data.""",
            "usage": {"input_tokens": 300, "output_tokens": 120},
            "model": "claude-3-haiku"
        }
        
        mock_anthropic_summary.side_effect = chunk_summaries + [final_summary]
        
        # Run summarization
        result = summarize_run(
            transcript_path=transcript_file,
            provider="anthropic",
            model="claude-3-haiku",
            output_dir=output_dir,
            template=SummaryTemplate.DEFAULT
        )
        
        # Verify Anthropic was called
        assert mock_anthropic_summary.call_count == 2  # 1 chunk + 1 final
        
        # Verify output structure
        with open(result, 'r', encoding='utf-8') as f:
            summary_data = json.load(f)
        
        assert summary_data["provider"] == "anthropic"
        assert summary_data["model"] == "claude-3-haiku"
        assert "Key Insights" in summary_data["summary"]
    
    def test_chunk_transcript_time_based(self, long_transcript_segments):
        """Test transcript chunking by time duration."""
        # Test with 60-second chunks
        chunks = chunk_transcript(long_transcript_segments, chunk_seconds=60)
        
        assert len(chunks) > 1  # Should create multiple chunks
        
        # Verify chunk content
        for chunk in chunks:
            assert len(chunk) > 0
            assert "[SPEAKER_" in chunk  # Should contain speaker labels
            
        # Verify all content is included
        full_text = '\n'.join(chunks)
        for segment in long_transcript_segments:
            assert segment["text"] in full_text
    
    def test_chunk_transcript_small_chunks(self, sample_transcript_segments):
        """Test transcript chunking with very small chunks."""
        # Test with 10-second chunks (smaller than individual segments)
        chunks = chunk_transcript(sample_transcript_segments, chunk_seconds=10)
        
        # Should still create reasonable chunks
        assert len(chunks) >= 1
        
        # Each chunk should be properly formatted
        for chunk in chunks:
            lines = chunk.strip().split('\n')
            for line in lines:
                assert '[SPEAKER_' in line and ']:' in line
    
    @patch('core.providers.openai_client.create_openai_summary')
    def test_template_detection_and_application(self, mock_openai_summary, 
                                              sop_transcript_segments, tmp_path):
        """Test automatic template detection and application."""
        # Create SOP transcript file
        transcript_file = tmp_path / "sop_transcript.json"
        with open(transcript_file, 'w', encoding='utf-8') as f:
            json.dump(sop_transcript_segments, f)
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Mock SOP-style summary
        sop_summary = {
            "summary": """# Training Session - Customer Onboarding Process

## Standard Operating Procedure (SOP)

### Overview
This training covered the new customer onboarding process with step-by-step procedures.

### Step-by-Step Process
1. **Initial Contact Verification**
   - Verify customer contact information
   - Confirm identity and authorization
   
2. **Documentation Collection**
   - Collect required documents from customer
   - Verify document completeness and validity
   
3. **Application Processing**
   - Process application through internal system
   - Follow verification procedures exactly as outlined

### Important Notes
- This process must be followed exactly as outlined
- Refer to procedure manual for detailed guidelines
- No deviations from standard process are permitted

### Training Completion
All staff must demonstrate understanding of each step before processing live applications.""",
            "usage": {"total_tokens": 280},
            "model": "gpt-4o-mini"
        }
        
        mock_openai_summary.return_value = sop_summary
        
        # Run with auto-detection
        result = summarize_run(
            transcript_path=transcript_file,
            provider="openai",
            model="gpt-4o-mini",
            output_dir=output_dir,
            auto_detect_template=True
        )
        
        # Verify template detection worked
        with open(result, 'r', encoding='utf-8') as f:
            summary_data = json.load(f)
        
        # Should detect SOP template
        assert summary_data.get("detected_template") == "sop"
        assert "Standard Operating Procedure" in summary_data["summary"]
        assert "Step-by-Step" in summary_data["summary"]
    
    @patch('core.providers.openai_client.create_openai_summary')
    def test_chain_of_density_processing(self, mock_openai_summary, 
                                       transcript_files, tmp_path):
        """Test Chain-of-Density refinement process."""
        transcript_file = transcript_files['json']
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Mock CoD passes with increasing density
        cod_responses = [
            {
                "summary": "Basic meeting summary with key points about Q3 performance review.",
                "usage": {"total_tokens": 120},
                "model": "gpt-4o-mini"
            },
            {
                "summary": """# Quarterly Review Meeting - Detailed Analysis

## Executive Summary
Comprehensive Q3 performance review focusing on customer acquisition growth (23% increase, 1,247 new customers) and retention metrics analysis.

## Key Performance Indicators
- Customer acquisition: 1,247 new customers (23% increase from Q2)
- Retention rate analysis: Discussed current performance trends
- Dashboard metrics: Reviewed quarterly KPIs and performance indicators

## Discussion Points
Team actively engaged with targeted questions about customer acquisition numbers and retention rate performance during the same period.

## Action Items and Next Steps
- Continue monitoring customer acquisition trends and metrics
- Follow up on retention rate analysis and improvement strategies
- Schedule follow-up quarterly review meeting for Q4 planning""",
                "usage": {"total_tokens": 180},
                "model": "gpt-4o-mini"
            }
        ]
        
        mock_openai_summary.side_effect = cod_responses
        
        # Run with multiple CoD passes
        result = summarize_run(
            transcript_path=transcript_file,
            provider="openai",
            model="gpt-4o-mini",
            output_dir=output_dir,
            chunk_seconds=300,  # Large chunks to avoid chunking
            cod_passes=2
        )
        
        # Verify CoD was applied
        assert mock_openai_summary.call_count == 2  # Initial + 1 CoD pass
        
        # Verify final summary is more detailed
        with open(result, 'r', encoding='utf-8') as f:
            summary_data = json.load(f)
        
        final_summary = summary_data["summary"]
        assert len(final_summary) > cod_responses[0]["summary"]  # Should be longer/denser
        assert "Executive Summary" in final_summary
        assert "Key Performance Indicators" in final_summary
    
    @patch('core.providers.openai_client.create_openai_summary')
    def test_error_handling_and_recovery(self, mock_openai_summary, 
                                       transcript_files, tmp_path):
        """Test error handling in summarization pipeline."""
        transcript_file = transcript_files['json']
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Mock failure then success
        from core.utils.exceptions import RateLimitError
        
        responses = [
            RateLimitError("Rate limit exceeded"),  # First call fails
            {
                "summary": "Successfully recovered summary after rate limit error.",
                "usage": {"total_tokens": 150},
                "model": "gpt-4o-mini"
            }
        ]
        
        mock_openai_summary.side_effect = responses
        
        # Should handle error and retry
        with patch('time.sleep'):  # Speed up retry
            with pytest.raises(RateLimitError):
                summarize_run(
                    transcript_path=transcript_file,
                    provider="openai",
                    model="gpt-4o-mini", 
                    output_dir=output_dir
                )
    
    def test_large_transcript_processing(self, chunked_transcript_data, tmp_path):
        """Test processing of large transcripts with multiple chunks."""
        # Create large transcript file
        large_transcript = []
        for chunk_data in chunked_transcript_data:
            # Convert chunk text back to segments
            lines = chunk_data['text'].split('\n')
            for i, line in enumerate(lines):
                if line.strip():
                    speaker = line.split(':')[0].strip('[]')
                    text = ':'.join(line.split(':')[1:]).strip()
                    large_transcript.append({
                        "start": chunk_data['start_time'] + i * 5,
                        "end": chunk_data['start_time'] + (i + 1) * 5,
                        "text": text,
                        "speaker": speaker,
                        "words": []
                    })
        
        transcript_file = tmp_path / "large_transcript.json"
        with open(transcript_file, 'w', encoding='utf-8') as f:
            json.dump(large_transcript, f)
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Mock provider responses for multiple chunks
        with patch('core.providers.openai_client.create_openai_summary') as mock_summary:
            # Mock responses for each chunk plus final summary
            chunk_responses = [
                {
                    "summary": f"Summary of chunk {i+1}",
                    "usage": {"total_tokens": 100},
                    "model": "gpt-4o-mini"
                }
                for i in range(len(chunked_transcript_data))
            ]
            
            final_response = {
                "summary": "Comprehensive summary of all chunks combined.",
                "usage": {"total_tokens": 300},
                "model": "gpt-4o-mini"
            }
            
            mock_summary.side_effect = chunk_responses + [final_response]
            
            result = summarize_run(
                transcript_path=transcript_file,
                provider="openai",
                model="gpt-4o-mini",
                output_dir=output_dir,
                chunk_seconds=300  # Will create multiple chunks
            )
            
            # Verify multiple chunks were processed
            expected_calls = len(chunked_transcript_data) + 1  # chunks + final
            assert mock_summary.call_count == expected_calls
            
            # Verify output
            with open(result, 'r', encoding='utf-8') as f:
                summary_data = json.load(f)
            
            assert len(summary_data["chunk_summaries"]) == len(chunked_transcript_data)
    
    def test_multilingual_transcript_handling(self, tmp_path):
        """Test handling of multilingual transcripts."""
        from tests.fixtures.transcript_samples import create_multilingual_transcript_segments
        
        multilingual_segments = create_multilingual_transcript_segments()
        
        transcript_file = tmp_path / "multilingual_transcript.json"
        with open(transcript_file, 'w', encoding='utf-8') as f:
            json.dump(multilingual_segments, f)
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        with patch('core.providers.openai_client.create_openai_summary') as mock_summary:
            mock_summary.return_value = {
                "summary": "Multilingual meeting summary covering English, French, and Spanish content.",
                "usage": {"total_tokens": 150},
                "model": "gpt-4o-mini"
            }
            
            result = summarize_run(
                transcript_path=transcript_file,
                provider="openai",
                model="gpt-4o-mini",
                output_dir=output_dir
            )
            
            # Should handle multilingual content gracefully
            assert result.exists()
            
            # Verify the transcript was processed
            mock_summary.assert_called_once()
            call_args = mock_summary.call_args[1]
            transcript_text = call_args["transcript_text"]
            
            # Should contain all languages
            assert "Welcome" in transcript_text  # English
            assert "Bonjour" in transcript_text   # French
            assert "Hola" in transcript_text      # Spanish


class TestTemplateDetectionIntegration:
    """Integration tests for template detection and formatting."""
    
    def test_detect_sop_template(self, sop_transcript_segments):
        """Test detection of SOP/training content."""
        # Convert to text for detection
        transcript_text = '\n'.join([
            f"[{seg['speaker']}]: {seg['text']}" 
            for seg in sop_transcript_segments
        ])
        
        detected_template = detect_meeting_type(transcript_text)
        assert detected_template == SummaryTemplate.SOP
    
    def test_detect_decision_template(self, decision_transcript_segments):
        """Test detection of decision-making content."""
        transcript_text = '\n'.join([
            f"[{seg['speaker']}]: {seg['text']}"
            for seg in decision_transcript_segments
        ])
        
        detected_template = detect_meeting_type(transcript_text)
        assert detected_template == SummaryTemplate.DECISION
    
    def test_detect_brainstorm_template(self, brainstorm_transcript_segments):
        """Test detection of brainstorming content."""
        transcript_text = '\n'.join([
            f"[{seg['speaker']}]: {seg['text']}"
            for seg in brainstorm_transcript_segments
        ])
        
        detected_template = detect_meeting_type(transcript_text)
        assert detected_template == SummaryTemplate.BRAINSTORM
    
    def test_format_sop_output(self):
        """Test SOP-specific output formatting."""
        raw_summary = """This training session covered the customer onboarding process. Step 1 is verification. Step 2 is documentation. Step 3 is processing. Follow these procedures exactly."""
        
        formatted = format_sop_output(raw_summary)
        
        # Should be formatted as proper SOP
        assert "## Standard Operating Procedure" in formatted
        assert "### Step 1:" in formatted or "1." in formatted
        assert "### Step 2:" in formatted or "2." in formatted
        assert "### Step 3:" in formatted or "3." in formatted


class TestSummarizationEdgeCases:
    """Test edge cases and error scenarios."""
    
    def test_empty_transcript_handling(self, tmp_path):
        """Test handling of empty transcripts."""
        empty_transcript = {"segments": []}
        
        transcript_file = tmp_path / "empty_transcript.json"
        with open(transcript_file, 'w', encoding='utf-8') as f:
            json.dump(empty_transcript, f)
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        with patch('core.providers.openai_client.create_openai_summary') as mock_summary:
            mock_summary.return_value = {
                "summary": "No content available for summarization.",
                "usage": {"total_tokens": 10},
                "model": "gpt-4o-mini"
            }
            
            result = summarize_run(
                transcript_path=transcript_file,
                provider="openai",
                model="gpt-4o-mini",
                output_dir=output_dir
            )
            
            # Should handle gracefully
            assert result.exists()
    
    def test_malformed_transcript_file(self, tmp_path):
        """Test handling of malformed transcript files."""
        malformed_file = tmp_path / "malformed.json"
        malformed_file.write_text('{"segments": [invalid json}')
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        with pytest.raises(json.JSONDecodeError):
            summarize_run(
                transcript_path=malformed_file,
                provider="openai",
                model="gpt-4o-mini",
                output_dir=output_dir
            )
    
    def test_missing_transcript_file(self, tmp_path):
        """Test handling of missing transcript file."""
        nonexistent_file = tmp_path / "nonexistent.json"
        output_dir = tmp_path / "output"
        
        with pytest.raises(FileNotFoundError):
            summarize_run(
                transcript_path=nonexistent_file,
                provider="openai",
                model="gpt-4o-mini",
                output_dir=output_dir
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])