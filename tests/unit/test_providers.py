"""
Unit tests for LLM provider clients.
Tests OpenAI and Anthropic API integrations with comprehensive error handling.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import json

from src.providers.openai_client import (
    client as openai_client,
    summarize_text as openai_summarize_text,
    summarize_chunks as openai_summarize_chunks,
    reset_client as openai_reset_client,
    _validate_api_key as openai_validate_api_key
)
from src.providers.anthropic_client import (
    client as anthropic_client,
    summarize_text as anthropic_summarize_text,
    summarize_chunks as anthropic_summarize_chunks,
    reset_client as anthropic_reset_client,
    _validate_api_key as anthropic_validate_api_key
)
from src.utils.exceptions import OpenAIError, AnthropicError


class TestOpenAIApiKeyValidation:
    """Test OpenAI API key validation."""

    def test_validate_api_key_valid(self):
        """Test valid OpenAI API key format."""
        valid_key = "sk-test1234567890123456"  # 24 chars, starts with sk-
        assert openai_validate_api_key(valid_key) is True

    def test_validate_api_key_valid_proj(self):
        """Test valid OpenAI project API key format."""
        valid_key = "sk-proj-test123456789012"  # starts with sk-proj-
        assert openai_validate_api_key(valid_key) is True

    def test_validate_api_key_empty(self):
        """Test empty API key."""
        assert openai_validate_api_key("") is False
        assert openai_validate_api_key(None) is False

    def test_validate_api_key_wrong_prefix(self):
        """Test API key with wrong prefix."""
        assert openai_validate_api_key("invalid-key-12345678") is False

    def test_validate_api_key_too_short(self):
        """Test API key that's too short."""
        assert openai_validate_api_key("sk-short") is False


class TestOpenAIClient:
    """Test OpenAI client functionality."""

    def setup_method(self):
        """Reset client cache before each test."""
        openai_reset_client()

    @patch('src.providers.openai_client.SETTINGS')
    @patch('src.providers.openai_client.OpenAI')
    def test_openai_client_initialization(self, mock_openai_class, mock_settings):
        """Test OpenAI client initialization."""
        # Use a valid API key format
        mock_settings.openai_api_key = "sk-test1234567890123456"
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        result = openai_client()

        mock_openai_class.assert_called_once_with(api_key="sk-test1234567890123456")
        assert result == mock_client

    @patch('src.providers.openai_client.SETTINGS')
    def test_openai_client_missing_api_key(self, mock_settings):
        """Test OpenAI client with missing API key."""
        mock_settings.openai_api_key = ""

        with pytest.raises(OpenAIError, match="Invalid or missing OpenAI API key"):
            openai_client()

    @patch('src.providers.openai_client.SETTINGS')
    def test_openai_client_invalid_api_key(self, mock_settings):
        """Test OpenAI client with invalid API key format."""
        mock_settings.openai_api_key = "invalid-key"

        with pytest.raises(OpenAIError, match="Invalid or missing OpenAI API key"):
            openai_client()

    @patch('src.providers.openai_client.client')
    @patch('src.providers.openai_client.SETTINGS')
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

    @patch('src.providers.openai_client.client')
    @patch('src.providers.openai_client.SETTINGS')
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


class TestAnthropicApiKeyValidation:
    """Test Anthropic API key validation."""

    def test_validate_api_key_valid(self):
        """Test valid Anthropic API key format."""
        valid_key = "sk-ant-test12345678901234567890"  # 30+ chars, starts with sk-ant-
        assert anthropic_validate_api_key(valid_key) is True

    def test_validate_api_key_empty(self):
        """Test empty API key."""
        assert anthropic_validate_api_key("") is False
        assert anthropic_validate_api_key(None) is False

    def test_validate_api_key_wrong_prefix(self):
        """Test API key with wrong prefix."""
        assert anthropic_validate_api_key("sk-test1234567890123456789012") is False

    def test_validate_api_key_too_short(self):
        """Test API key that's too short."""
        assert anthropic_validate_api_key("sk-ant-short") is False


class TestAnthropicClient:
    """Test Anthropic client functionality."""

    def setup_method(self):
        """Reset client cache before each test."""
        anthropic_reset_client()

    @patch('src.providers.anthropic_client.SETTINGS')
    @patch('src.providers.anthropic_client.Anthropic')
    def test_anthropic_client_initialization(self, mock_anthropic_class, mock_settings):
        """Test Anthropic client initialization."""
        # Use a valid API key format (sk-ant- prefix, min 30 chars)
        mock_settings.anthropic_api_key = "sk-ant-test12345678901234567890"
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        result = anthropic_client()

        mock_anthropic_class.assert_called_once_with(api_key="sk-ant-test12345678901234567890")
        assert result == mock_client

    @patch('src.providers.anthropic_client.SETTINGS')
    def test_anthropic_client_missing_api_key(self, mock_settings):
        """Test Anthropic client with missing API key."""
        mock_settings.anthropic_api_key = ""

        with pytest.raises(AnthropicError, match="Invalid or missing Anthropic API key"):
            anthropic_client()

    @patch('src.providers.anthropic_client.SETTINGS')
    def test_anthropic_client_invalid_api_key(self, mock_settings):
        """Test Anthropic client with invalid API key format."""
        mock_settings.anthropic_api_key = "invalid-key"

        with pytest.raises(AnthropicError, match="Invalid or missing Anthropic API key"):
            anthropic_client()

    @patch('src.providers.anthropic_client.client')
    @patch('src.providers.anthropic_client.SETTINGS')
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

    @patch('src.providers.anthropic_client.client')
    @patch('src.providers.anthropic_client.SETTINGS')
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
