"""
Unit tests for LLM provider clients.
Tests OpenAI and Anthropic API integrations with comprehensive error handling.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import json

from core.providers.openai_client import client as openai_client, summarize_text as openai_summarize_text, summarize_chunks as openai_summarize_chunks
from core.providers.anthropic_client import client as anthropic_client, summarize_text as anthropic_summarize_text, summarize_chunks as anthropic_summarize_chunks
from core.utils.exceptions import SummeetsError


class TestOpenAIClient:
    """Test OpenAI client functionality."""
    
    @patch('core.utils.config.SETTINGS')
    @patch('openai.OpenAI')
    def test_openai_client_initialization(self, mock_openai_class, mock_settings):
        """Test OpenAI client initialization."""
        mock_settings.openai_api_key = "sk-test-key"
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        client = openai_client()
        
        mock_openai_class.assert_called_once_with(api_key="sk-test-key")
        assert client == mock_client
    
    @patch('core.utils.config.SETTINGS')
    def test_openai_client_missing_api_key(self, mock_settings):
        """Test OpenAI client with missing API key."""
        mock_settings.openai_api_key = ""
        
        with pytest.raises(SummeetsError, match="Invalid or missing OpenAI API key"):
            openai_client()
    
    @patch('core.utils.config.SETTINGS')
    def test_openai_client_invalid_api_key(self, mock_settings):
        """Test OpenAI client with invalid API key format."""
        mock_settings.openai_api_key = "invalid-key"
        
        with pytest.raises(SummeetsError, match="Invalid or missing OpenAI API key"):
            openai_client()
    
    @patch('core.providers.openai_client.client')
    @patch('core.utils.config.SETTINGS')
    def test_summarize_text_success(self, mock_settings, mock_client_func):
        """Test successful text summarization."""
        mock_settings.model = "gpt-4o-mini"
        mock_settings.summary_max_tokens = 1000
        
        mock_client = Mock()
        mock_client_func.return_value = mock_client
        
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "This is a comprehensive meeting summary."
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        mock_client.chat.completions.create.return_value = mock_response
        
        result = openai_summarize_text("Meeting discussion about quarterly results...")
        
        assert result == "This is a comprehensive meeting summary."
        mock_client.chat.completions.create.assert_called_once()
    
    @patch('core.providers.openai_client.client')
    @patch('core.utils.config.SETTINGS')
    def test_summarize_chunks_success(self, mock_settings, mock_client_func):
        """Test successful chunk summarization."""
        mock_settings.model = "gpt-4o-mini"
        
        mock_client = Mock()
        mock_client_func.return_value = mock_client
        
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "Chunk summary"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        mock_client.chat.completions.create.return_value = mock_response
        
        chunks = ["First chunk", "Second chunk"]
        schema = {"type": "object", "properties": {"summary": {"type": "string"}}}
        
        result = openai_summarize_chunks(chunks, schema, 500)
        
        assert len(result) == 2
        assert result[0] == "Chunk summary"
        assert result[1] == "Chunk summary"
        assert mock_client.chat.completions.create.call_count == 2
    

class TestAnthropicClient:
    """Test Anthropic client functionality."""
    
    @patch('core.utils.config.SETTINGS')
    @patch('anthropic.Anthropic')
    def test_anthropic_client_initialization(self, mock_anthropic_class, mock_settings):
        """Test Anthropic client initialization."""
        mock_settings.anthropic_api_key = "sk-ant-test-key"
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        client = anthropic_client()
        
        mock_anthropic_class.assert_called_once_with(api_key="sk-ant-test-key")
        assert client == mock_client
    
    @patch('core.utils.config.SETTINGS')
    def test_anthropic_client_missing_api_key(self, mock_settings):
        """Test Anthropic client with missing API key."""
        mock_settings.anthropic_api_key = ""
        
        with pytest.raises(SummeetsError, match="Invalid or missing Anthropic API key"):
            anthropic_client()
    
    @patch('core.utils.config.SETTINGS')
    def test_anthropic_client_invalid_api_key(self, mock_settings):
        """Test Anthropic client with invalid API key format."""
        mock_settings.anthropic_api_key = "invalid-key"
        
        with pytest.raises(SummeetsError, match="Invalid or missing Anthropic API key"):
            anthropic_client()
    
    @patch('core.providers.anthropic_client.client')
    @patch('core.utils.config.SETTINGS')
    def test_summarize_text_success(self, mock_settings, mock_client_func):
        """Test successful text summarization."""
        mock_settings.model = "claude-3-haiku"
        mock_settings.summary_max_tokens = 1000
        
        mock_client = Mock()
        mock_client_func.return_value = mock_client
        
        mock_response = Mock()
        mock_content_block = Mock()
        mock_content_block.text = "This is a detailed meeting analysis created by Claude."
        mock_response.content = [mock_content_block]
        
        mock_client.messages.create.return_value = mock_response
        
        result = anthropic_summarize_text("Meeting discussion about product strategy...")
        
        assert result == "This is a detailed meeting analysis created by Claude."
        mock_client.messages.create.assert_called_once()
    
    @patch('core.providers.anthropic_client.client')
    @patch('core.utils.config.SETTINGS')
    def test_summarize_chunks_success(self, mock_settings, mock_client_func):
        """Test successful chunk summarization."""
        mock_settings.model = "claude-3-haiku"
        
        mock_client = Mock()
        mock_client_func.return_value = mock_client
        
        mock_response = Mock()
        mock_content_block = Mock()
        mock_content_block.text = "Chunk summary"
        mock_response.content = [mock_content_block]
        
        mock_client.messages.create.return_value = mock_response
        
        chunks = ["First chunk", "Second chunk"]
        system_prompt = "You are a helpful assistant."
        
        result = anthropic_summarize_chunks(chunks, system_prompt, 500)
        
        assert len(result) == 2
        assert result[0] == "Chunk summary"
        assert result[1] == "Chunk summary"
        assert mock_client.messages.create.call_count == 2



if __name__ == "__main__":
    pytest.main([__file__, "-v"])