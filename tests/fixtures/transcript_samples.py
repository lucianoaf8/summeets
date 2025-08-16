"""
Transcript data fixtures for testing transcription and summarization.
Provides realistic transcript data with speaker diarization.
"""
import pytest
from pathlib import Path
from typing import List, Dict, Any
import json
from datetime import datetime, timedelta


@pytest.fixture
def sample_transcript_segments():
    """Create realistic transcript segments for testing."""
    return [
        {
            "start": 0.0,
            "end": 5.432,
            "text": "Good morning everyone, and welcome to our quarterly review meeting.",
            "speaker": "SPEAKER_00",
            "words": [
                {"start": 0.0, "end": 0.5, "word": "Good"},
                {"start": 0.5, "end": 1.0, "word": "morning"},
                {"start": 1.0, "end": 1.8, "word": "everyone,"},
                {"start": 1.8, "end": 2.0, "word": "and"},
                {"start": 2.0, "end": 2.5, "word": "welcome"},
                {"start": 2.5, "end": 2.7, "word": "to"},
                {"start": 2.7, "end": 2.9, "word": "our"},
                {"start": 2.9, "end": 3.7, "word": "quarterly"},
                {"start": 3.7, "end": 4.2, "word": "review"},
                {"start": 4.2, "end": 5.432, "word": "meeting."}
            ]
        },
        {
            "start": 5.432,
            "end": 12.156,
            "text": "I'd like to start by reviewing our performance metrics from Q3.",
            "speaker": "SPEAKER_00",
            "words": [
                {"start": 5.432, "end": 5.8, "word": "I'd"},
                {"start": 5.8, "end": 6.2, "word": "like"},
                {"start": 6.2, "end": 6.4, "word": "to"},
                {"start": 6.4, "end": 6.8, "word": "start"},
                {"start": 6.8, "end": 7.0, "word": "by"},
                {"start": 7.0, "end": 7.6, "word": "reviewing"},
                {"start": 7.6, "end": 7.8, "word": "our"},
                {"start": 7.8, "end": 8.6, "word": "performance"},
                {"start": 8.6, "end": 9.2, "word": "metrics"},
                {"start": 9.2, "end": 9.5, "word": "from"},
                {"start": 9.5, "end": 12.156, "word": "Q3."}
            ]
        },
        {
            "start": 12.156,
            "end": 18.901,
            "text": "That sounds great. I have some questions about the customer acquisition numbers.",
            "speaker": "SPEAKER_01",
            "words": [
                {"start": 12.156, "end": 12.5, "word": "That"},
                {"start": 12.5, "end": 13.0, "word": "sounds"},
                {"start": 13.0, "end": 13.5, "word": "great."},
                {"start": 13.5, "end": 13.7, "word": "I"},
                {"start": 13.7, "end": 14.0, "word": "have"},
                {"start": 14.0, "end": 14.3, "word": "some"},
                {"start": 14.3, "end": 14.9, "word": "questions"},
                {"start": 14.9, "end": 15.2, "word": "about"},
                {"start": 15.2, "end": 15.4, "word": "the"},
                {"start": 15.4, "end": 16.2, "word": "customer"},
                {"start": 16.2, "end": 17.0, "word": "acquisition"},
                {"start": 17.0, "end": 18.901, "word": "numbers."}
            ]
        },
        {
            "start": 18.901,
            "end": 28.445,
            "text": "Of course. Let me pull up the dashboard. We acquired 1,247 new customers this quarter, which is a 23% increase from Q2.",
            "speaker": "SPEAKER_00",
            "words": [
                {"start": 18.901, "end": 19.2, "word": "Of"},
                {"start": 19.2, "end": 19.8, "word": "course."},
                {"start": 19.8, "end": 20.0, "word": "Let"},
                {"start": 20.0, "end": 20.2, "word": "me"},
                {"start": 20.2, "end": 20.5, "word": "pull"},
                {"start": 20.5, "end": 20.7, "word": "up"},
                {"start": 20.7, "end": 20.9, "word": "the"},
                {"start": 20.9, "end": 21.6, "word": "dashboard."},
                {"start": 21.6, "end": 21.8, "word": "We"},
                {"start": 21.8, "end": 22.4, "word": "acquired"},
                {"start": 22.4, "end": 23.2, "word": "1,247"},
                {"start": 23.2, "end": 23.5, "word": "new"},
                {"start": 23.5, "end": 24.2, "word": "customers"},
                {"start": 24.2, "end": 24.5, "word": "this"},
                {"start": 24.5, "end": 25.1, "word": "quarter,"},
                {"start": 25.1, "end": 25.4, "word": "which"},
                {"start": 25.4, "end": 25.6, "word": "is"},
                {"start": 25.6, "end": 25.7, "word": "a"},
                {"start": 25.7, "end": 26.2, "word": "23%"},
                {"start": 26.2, "end": 26.8, "word": "increase"},
                {"start": 26.8, "end": 27.1, "word": "from"},
                {"start": 27.1, "end": 28.445, "word": "Q2."}
            ]
        },
        {
            "start": 28.445,
            "end": 35.123,
            "text": "That's impressive! What was our retention rate during the same period?",
            "speaker": "SPEAKER_02",
            "words": [
                {"start": 28.445, "end": 29.0, "word": "That's"},
                {"start": 29.0, "end": 29.8, "word": "impressive!"},
                {"start": 29.8, "end": 30.1, "word": "What"},
                {"start": 30.1, "end": 30.3, "word": "was"},
                {"start": 30.3, "end": 30.5, "word": "our"},
                {"start": 30.5, "end": 31.2, "word": "retention"},
                {"start": 31.2, "end": 31.6, "word": "rate"},
                {"start": 31.6, "end": 31.9, "word": "during"},
                {"start": 31.9, "end": 32.1, "word": "the"},
                {"start": 32.1, "end": 32.5, "word": "same"},
                {"start": 32.5, "end": 35.123, "word": "period?"}
            ]
        }
    ]


@pytest.fixture
def long_transcript_segments():
    """Create longer transcript for chunking and summarization testing."""
    segments = []
    current_time = 0.0
    speakers = ["SPEAKER_00", "SPEAKER_01", "SPEAKER_02"]
    
    topics = [
        "Let's start with our quarterly performance review.",
        "Our revenue increased by fifteen percent this quarter.",
        "The customer satisfaction scores have improved significantly.",
        "We need to discuss the new product launch timeline.",
        "The marketing campaign performed better than expected.",
        "There are some technical challenges we need to address.",
        "Let's review the budget allocation for next quarter.",
        "I think we should prioritize the mobile application development.",
        "The team has been working very hard on this project.",
        "We should schedule a follow-up meeting next week.",
    ]
    
    for i, topic in enumerate(topics * 18):  # 180 segments total (~30 min)
        speaker = speakers[i % len(speakers)]
        segment_duration = 8.0 + (i % 5)  # 8-12 seconds per segment
        
        segment = {
            "start": current_time,
            "end": current_time + segment_duration,
            "text": topic,
            "speaker": speaker,
            "words": _create_words_for_text(topic, current_time, segment_duration)
        }
        
        segments.append(segment)
        current_time += segment_duration
    
    return segments


@pytest.fixture
def sop_transcript_segments():
    """Create transcript that should be detected as SOP/training content."""
    return [
        {
            "start": 0.0,
            "end": 8.5,
            "text": "Welcome to today's training session on our new customer onboarding process.",
            "speaker": "TRAINER",
            "words": []
        },
        {
            "start": 8.5,
            "end": 16.2,
            "text": "First, let me walk you through step one: initial customer contact verification.",
            "speaker": "TRAINER", 
            "words": []
        },
        {
            "start": 16.2,
            "end": 24.8,
            "text": "Step two involves collecting the required documentation from the customer.",
            "speaker": "TRAINER",
            "words": []
        },
        {
            "start": 24.8,
            "end": 33.1,
            "text": "Finally, step three is to process the application through our internal system.",
            "speaker": "TRAINER",
            "words": []
        },
        {
            "start": 33.1,
            "end": 40.5,
            "text": "Remember, this process must be followed exactly as outlined in the procedure manual.",
            "speaker": "TRAINER",
            "words": []
        }
    ]


@pytest.fixture
def decision_transcript_segments():
    """Create transcript that should be detected as decision-making content."""
    return [
        {
            "start": 0.0,
            "end": 7.5,
            "text": "We need to make a decision about the new product pricing strategy.",
            "speaker": "CEO",
            "words": []
        },
        {
            "start": 7.5,
            "end": 15.2,
            "text": "I propose we set the price at $99 per month for the premium tier.",
            "speaker": "PRODUCT_MANAGER",
            "words": []
        },
        {
            "start": 15.2,
            "end": 22.8,
            "text": "That seems high. Market research suggests $79 would be more competitive.",
            "speaker": "MARKETING_DIRECTOR",
            "words": []
        },
        {
            "start": 22.8,
            "end": 30.5,
            "text": "Let's compromise at $89. Everyone in favor, please vote now.",
            "speaker": "CEO",
            "words": []
        },
        {
            "start": 30.5,
            "end": 35.2,
            "text": "Motion carried. The premium tier will be priced at $89 per month.",
            "speaker": "CEO",
            "words": []
        }
    ]


@pytest.fixture
def brainstorm_transcript_segments():
    """Create transcript that should be detected as brainstorming content."""
    return [
        {
            "start": 0.0,
            "end": 6.5,
            "text": "Let's brainstorm ideas for improving our customer experience.",
            "speaker": "FACILITATOR",
            "words": []
        },
        {
            "start": 6.5,
            "end": 12.8,
            "text": "What if we added a live chat feature to our website?",
            "speaker": "PARTICIPANT_01",
            "words": []
        },
        {
            "start": 12.8,
            "end": 18.9,
            "text": "Great idea! We could also implement a customer feedback widget.",
            "speaker": "PARTICIPANT_02",
            "words": []
        },
        {
            "start": 18.9,
            "end": 25.1,
            "text": "I'm thinking we could create personalized onboarding flows for different user types.",
            "speaker": "PARTICIPANT_03",
            "words": []
        },
        {
            "start": 25.1,
            "end": 31.5,
            "text": "These are all excellent suggestions. Let's capture everything on the whiteboard.",
            "speaker": "FACILITATOR",
            "words": []
        }
    ]


@pytest.fixture
def transcript_files(tmp_path, sample_transcript_segments):
    """Create various transcript file formats for testing."""
    files = {}
    
    # JSON format
    json_file = tmp_path / "meeting_transcript.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(sample_transcript_segments, f, indent=2)
    files['json'] = json_file
    
    # SRT format
    srt_file = tmp_path / "meeting_transcript.srt"
    srt_content = _segments_to_srt(sample_transcript_segments)
    srt_file.write_text(srt_content, encoding='utf-8')
    files['srt'] = srt_file
    
    # Plain text format
    txt_file = tmp_path / "meeting_transcript.txt"
    txt_content = '\n'.join([
        f"[{seg['speaker']}]: {seg['text']}"
        for seg in sample_transcript_segments
    ])
    txt_file.write_text(txt_content, encoding='utf-8')
    files['txt'] = txt_file
    
    # Malformed JSON for error testing
    malformed_file = tmp_path / "malformed_transcript.json"
    malformed_file.write_text('{"segments": [invalid json}', encoding='utf-8')
    files['malformed'] = malformed_file
    
    # Empty file
    empty_file = tmp_path / "empty_transcript.json"
    empty_file.write_text('{"segments": []}', encoding='utf-8')
    files['empty'] = empty_file
    
    return files


@pytest.fixture
def chunked_transcript_data(long_transcript_segments):
    """Create pre-chunked transcript data for summarization testing."""
    # Chunk every 30 segments (approximately 5 minutes)
    chunk_size = 30
    chunks = []
    
    for i in range(0, len(long_transcript_segments), chunk_size):
        chunk_segments = long_transcript_segments[i:i + chunk_size]
        chunk_text = '\n'.join([
            f"[{seg['speaker']}]: {seg['text']}"
            for seg in chunk_segments
        ])
        chunks.append({
            'chunk_index': i // chunk_size,
            'start_time': chunk_segments[0]['start'],
            'end_time': chunk_segments[-1]['end'],
            'text': chunk_text,
            'segment_count': len(chunk_segments)
        })
    
    return chunks


@pytest.fixture
def replicate_api_response(sample_transcript_segments):
    """Mock realistic Replicate API response."""
    return {
        "status": "succeeded",
        "output": {
            "segments": sample_transcript_segments
        },
        "logs": "Processing completed successfully",
        "metrics": {
            "predict_time": 45.2,
            "total_time": 47.8
        }
    }


@pytest.fixture
def replicate_api_error_response():
    """Mock Replicate API error responses."""
    return {
        "timeout": {
            "status": "failed",
            "error": "Request timeout after 300 seconds"
        },
        "file_too_large": {
            "status": "failed", 
            "error": "File size exceeds maximum limit of 25MB"
        },
        "invalid_audio": {
            "status": "failed",
            "error": "Could not decode audio file"
        },
        "rate_limit": {
            "status": "failed",
            "error": "Rate limit exceeded. Please try again later."
        }
    }


def _create_words_for_text(text: str, start_time: float, duration: float) -> List[Dict[str, Any]]:
    """Create word-level timing for a text segment."""
    words = text.replace(',', '').replace('.', '').replace('!', '').replace('?', '').split()
    if not words:
        return []
    
    time_per_word = duration / len(words)
    word_data = []
    
    current_time = start_time
    for word in words:
        word_data.append({
            "start": round(current_time, 3),
            "end": round(current_time + time_per_word, 3),
            "word": word
        })
        current_time += time_per_word
    
    return word_data


def _segments_to_srt(segments: List[Dict[str, Any]]) -> str:
    """Convert segments to SRT format."""
    srt_lines = []
    
    for i, segment in enumerate(segments, 1):
        start_time = _seconds_to_srt_time(segment['start'])
        end_time = _seconds_to_srt_time(segment['end'])
        speaker = segment.get('speaker', 'Unknown')
        text = segment['text']
        
        srt_lines.extend([
            str(i),
            f"{start_time} --> {end_time}",
            f"[{speaker}]: {text}",
            ""
        ])
    
    return '\n'.join(srt_lines)


def _seconds_to_srt_time(seconds: float) -> str:
    """Convert seconds to SRT time format (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def create_multilingual_transcript_segments():
    """Create transcript segments with multiple languages for testing."""
    return [
        {
            "start": 0.0,
            "end": 5.0,
            "text": "Welcome to our international meeting.",
            "speaker": "SPEAKER_EN",
            "language": "en"
        },
        {
            "start": 5.0,
            "end": 10.0,
            "text": "Bonjour et bienvenue à notre réunion.",
            "speaker": "SPEAKER_FR", 
            "language": "fr"
        },
        {
            "start": 10.0,
            "end": 15.0,
            "text": "Hola y bienvenidos a nuestra reunión.",
            "speaker": "SPEAKER_ES",
            "language": "es"
        }
    ]