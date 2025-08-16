"""
Unit tests for LLM provider clients.
Tests OpenAI and Anthropic API integrations with comprehensive error handling.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import json

from core.providers.openai_client import OpenAIClient, create_openai_summary
from core.providers.anthropic_client import AnthropicClient, create_anthropic_summary
from core.utils.exceptions import ProviderError, RateLimitError, AuthenticationError


class TestOpenAIClient:
    """Test OpenAI client functionality."""
    
    def test_openai_client_initialization(self):
        """Test OpenAI client initialization."""
        with patch('openai.OpenAI') as mock_openai:
            client = OpenAIClient(api_key="test-key")
            
            assert client.api_key == "test-key"
            mock_openai.assert_called_once_with(api_key="test-key")
    
    def test_openai_client_initialization_from_env(self):
        """Test OpenAI client initialization from environment."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'env-key'}):
            with patch('openai.OpenAI') as mock_openai:
                client = OpenAIClient()
                
                assert client.api_key == "env-key"
                mock_openai.assert_called_once_with(api_key="env-key")
    
    def test_openai_client_missing_api_key(self):
        """Test OpenAI client with missing API key."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ProviderError, match="OpenAI API key not provided"):
                OpenAIClient()
    
    @patch('openai.OpenAI')
    def test_create_summary_success(self, mock_openai_class):
        """Test successful summary creation."""
        # Mock client and response
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "This is a comprehensive meeting summary."
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 500
        mock_response.usage.completion_tokens = 150
        mock_response.usage.total_tokens = 650
        
        mock_client.chat.completions.create.return_value = mock_response
        
        # Test summary creation
        transcript_text = "Meeting discussion about quarterly results..."
        result = create_openai_summary(
            transcript_text=transcript_text,
            api_key="test-key",
            model="gpt-4o-mini",
            max_tokens=1000,
            template="default"
        )
        
        assert result["summary"] == "This is a comprehensive meeting summary."
        assert result["usage"]["prompt_tokens"] == 500
        assert result["usage"]["completion_tokens"] == 150
        assert result["usage"]["total_tokens"] == 650
        assert result["model"] == "gpt-4o-mini"
        
        # Verify API call
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        
        assert call_args[1]["model"] == "gpt-4o-mini"
        assert call_args[1]["max_tokens"] == 1000
        assert len(call_args[1]["messages"]) == 2  # system + user
        assert transcript_text in call_args[1]["messages"][1]["content"]
    
    @patch('openai.OpenAI')
    def test_create_summary_with_custom_template(self, mock_openai_class):
        """Test summary creation with custom template."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "SOP summary with structured steps."
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 600
        mock_response.usage.completion_tokens = 200
        mock_response.usage.total_tokens = 800
        
        mock_client.chat.completions.create.return_value = mock_response
        
        result = create_openai_summary(
            transcript_text="Training session transcript...",
            api_key="test-key",
            model="gpt-4o",
            template="sop"
        )
        
        assert result["summary"] == "SOP summary with structured steps."
        
        # Verify SOP template was used
        call_args = mock_client.chat.completions.create.call_args
        system_message = call_args[1]["messages"][0]["content"]
        assert "SOP" in system_message or "procedure" in system_message.lower()
    
    @patch('openai.OpenAI')
    def test_openai_rate_limit_error(self, mock_openai_class):
        """Test OpenAI rate limit error handling."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        from openai import RateLimitError as OpenAIRateLimitError
        mock_client.chat.completions.create.side_effect = OpenAIRateLimitError(
            message="Rate limit exceeded",
            response=Mock(status_code=429),
            body={"error": {"code": "rate_limit_exceeded"}}
        )
        
        with pytest.raises(RateLimitError, match="OpenAI rate limit exceeded"):
            create_openai_summary(
                transcript_text="Test transcript",
                api_key="test-key",
                model="gpt-4o-mini"
            )
    
    @patch('openai.OpenAI')
    def test_openai_authentication_error(self, mock_openai_class):
        """Test OpenAI authentication error handling."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        from openai import AuthenticationError as OpenAIAuthError
        mock_client.chat.completions.create.side_effect = OpenAIAuthError(
            message="Invalid API key",
            response=Mock(status_code=401),
            body={"error": {"code": "invalid_api_key"}}
        )
        
        with pytest.raises(AuthenticationError, match="OpenAI authentication failed"):
            create_openai_summary(
                transcript_text="Test transcript",
                api_key="invalid-key",
                model="gpt-4o-mini"
            )
    
    @patch('openai.OpenAI')
    def test_openai_context_length_error(self, mock_openai_class):
        """Test OpenAI context length exceeded error."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        from openai import BadRequestError
        mock_client.chat.completions.create.side_effect = BadRequestError(
            message="Context length exceeded",
            response=Mock(status_code=400),
            body={"error": {"code": "context_length_exceeded"}}
        )
        
        with pytest.raises(ProviderError, match="Context length exceeded"):
            create_openai_summary(
                transcript_text="Very long transcript..." * 10000,
                api_key="test-key",
                model="gpt-4o-mini"
            )
    
    @patch('openai.OpenAI')
    def test_openai_generic_error(self, mock_openai_class):
        """Test OpenAI generic error handling."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        mock_client.chat.completions.create.side_effect = Exception("Unknown error")
        
        with pytest.raises(ProviderError, match="OpenAI API error"):
            create_openai_summary(
                transcript_text="Test transcript",
                api_key="test-key",
                model="gpt-4o-mini"
            )


class TestAnthropicClient:
    """Test Anthropic client functionality."""
    
    def test_anthropic_client_initialization(self):
        """Test Anthropic client initialization."""
        with patch('anthropic.Anthropic') as mock_anthropic:
            client = AnthropicClient(api_key="test-key")
            
            assert client.api_key == "test-key"
            mock_anthropic.assert_called_once_with(api_key="test-key")
    
    def test_anthropic_client_initialization_from_env(self):
        """Test Anthropic client initialization from environment."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'env-key'}):
            with patch('anthropic.Anthropic') as mock_anthropic:
                client = AnthropicClient()
                
                assert client.api_key == "env-key"
                mock_anthropic.assert_called_once_with(api_key="env-key")
    
    def test_anthropic_client_missing_api_key(self):
        """Test Anthropic client with missing API key."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ProviderError, match="Anthropic API key not provided"):
                AnthropicClient()
    
    @patch('anthropic.Anthropic')
    def test_create_anthropic_summary_success(self, mock_anthropic_class):
        """Test successful Anthropic summary creation."""
        # Mock client and response
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        mock_response = Mock()
        mock_content_block = Mock()
        mock_content_block.text = "This is a detailed meeting analysis created by Claude."
        mock_response.content = [mock_content_block]
        mock_response.usage = Mock()
        mock_response.usage.input_tokens = 450
        mock_response.usage.output_tokens = 180
        
        mock_client.messages.create.return_value = mock_response
        
        # Test summary creation
        transcript_text = "Meeting discussion about product strategy..."
        result = create_anthropic_summary(
            transcript_text=transcript_text,
            api_key="test-key",
            model="claude-3-haiku",
            max_tokens=1500,
            template="decision"
        )
        
        assert result["summary"] == "This is a detailed meeting analysis created by Claude."
        assert result["usage"]["input_tokens"] == 450
        assert result["usage"]["output_tokens"] == 180
        assert result["model"] == "claude-3-haiku"
        
        # Verify API call
        mock_client.messages.create.assert_called_once()
        call_args = mock_client.messages.create.call_args
        
        assert call_args[1]["model"] == "claude-3-haiku"
        assert call_args[1]["max_tokens"] == 1500
        assert len(call_args[1]["messages"]) == 1  # user message
        assert transcript_text in call_args[1]["messages"][0]["content"]
        assert "system" in call_args[1]  # system prompt
    
    @patch('anthropic.Anthropic')
    def test_create_anthropic_summary_brainstorm_template(self, mock_anthropic_class):
        """Test Anthropic summary with brainstorm template."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        mock_response = Mock()
        mock_content_block = Mock()
        mock_content_block.text = "Brainstorming session summary with creative ideas."
        mock_response.content = [mock_content_block]
        mock_response.usage = Mock()
        mock_response.usage.input_tokens = 300
        mock_response.usage.output_tokens = 120
        
        mock_client.messages.create.return_value = mock_response
        
        result = create_anthropic_summary(
            transcript_text="Creative brainstorming session...",
            api_key="test-key",
            model="claude-3-sonnet",
            template="brainstorm"
        )
        
        assert result["summary"] == "Brainstorming session summary with creative ideas."
        
        # Verify brainstorm template was used
        call_args = mock_client.messages.create.call_args
        system_prompt = call_args[1]["system"]
        assert "brainstorm" in system_prompt.lower() or "creative" in system_prompt.lower()
    
    @patch('anthropic.Anthropic')
    def test_anthropic_rate_limit_error(self, mock_anthropic_class):
        """Test Anthropic rate limit error handling."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        from anthropic import RateLimitError as AnthropicRateLimitError
        mock_client.messages.create.side_effect = AnthropicRateLimitError(
            message="Rate limit exceeded",
            response=Mock(status_code=429),
            body={"error": {"type": "rate_limit_error"}}
        )
        
        with pytest.raises(RateLimitError, match="Anthropic rate limit exceeded"):
            create_anthropic_summary(
                transcript_text="Test transcript",
                api_key="test-key",
                model="claude-3-haiku"
            )
    
    @patch('anthropic.Anthropic')
    def test_anthropic_authentication_error(self, mock_anthropic_class):
        """Test Anthropic authentication error handling."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        from anthropic import AuthenticationError as AnthropicAuthError
        mock_client.messages.create.side_effect = AnthropicAuthError(
            message="Invalid API key",
            response=Mock(status_code=401),
            body={"error": {"type": "authentication_error"}}
        )
        
        with pytest.raises(AuthenticationError, match="Anthropic authentication failed"):
            create_anthropic_summary(
                transcript_text="Test transcript",
                api_key="invalid-key",
                model="claude-3-haiku"
            )
    
    @patch('anthropic.Anthropic')
    def test_anthropic_overloaded_error(self, mock_anthropic_class):
        """Test Anthropic service overloaded error."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        from anthropic import OverloadedError
        mock_client.messages.create.side_effect = OverloadedError(
            message="Service temporarily overloaded",
            response=Mock(status_code=529),
            body={"error": {"type": "overloaded_error"}}
        )
        
        with pytest.raises(ProviderError, match="Anthropic service overloaded"):
            create_anthropic_summary(
                transcript_text="Test transcript",
                api_key="test-key",
                model="claude-3-haiku"
            )


class TestProviderSelection:
    """Test provider selection and fallback logic."""
    
    def test_select_best_provider_openai_available(self):
        """Test provider selection when OpenAI is available."""
        from core.providers import select_best_provider
        
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            provider = select_best_provider(preference="openai")
            assert provider == "openai"
    
    def test_select_best_provider_anthropic_available(self):
        """Test provider selection when Anthropic is available."""
        from core.providers import select_best_provider
        
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            provider = select_best_provider(preference="anthropic")
            assert provider == "anthropic"
    
    def test_select_best_provider_fallback(self):
        """Test provider selection with fallback."""
        from core.providers import select_best_provider
        
        # Mock OpenAI unavailable, Anthropic available
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            provider = select_best_provider(preference="openai")
            assert provider == "anthropic"  # Falls back to available provider
    
    def test_select_best_provider_none_available(self):
        """Test provider selection when none are available."""
        from core.providers import select_best_provider
        
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ProviderError, match="No LLM providers available"):
                select_best_provider()


class TestProviderUtils:
    """Test provider utility functions."""
    
    def test_validate_model_name_openai(self):
        """Test OpenAI model name validation."""
        from core.providers.openai_client import validate_model_name
        
        # Valid models
        assert validate_model_name("gpt-4o") == "gpt-4o"
        assert validate_model_name("gpt-4o-mini") == "gpt-4o-mini"
        assert validate_model_name("gpt-3.5-turbo") == "gpt-3.5-turbo"
        
        # Invalid model
        with pytest.raises(ValueError, match="Unsupported OpenAI model"):
            validate_model_name("invalid-model")
    
    def test_validate_model_name_anthropic(self):
        """Test Anthropic model name validation."""
        from core.providers.anthropic_client import validate_model_name
        
        # Valid models
        assert validate_model_name("claude-3-opus") == "claude-3-opus"
        assert validate_model_name("claude-3-sonnet") == "claude-3-sonnet"
        assert validate_model_name("claude-3-haiku") == "claude-3-haiku"
        
        # Invalid model
        with pytest.raises(ValueError, match="Unsupported Anthropic model"):
            validate_model_name("invalid-claude")
    
    def test_estimate_token_count(self):
        """Test token count estimation."""
        from core.providers import estimate_token_count
        
        text = "This is a test message for token counting."
        
        # Should return reasonable estimate
        token_count = estimate_token_count(text)
        assert isinstance(token_count, int)
        assert token_count > 0
        assert token_count < 100  # Should be reasonable for short text
    
    def test_chunk_text_by_tokens(self):
        """Test text chunking by token count."""
        from core.providers import chunk_text_by_tokens
        
        # Long text that needs chunking
        long_text = "This is a sentence. " * 100  # ~500 tokens
        
        chunks = chunk_text_by_tokens(long_text, max_tokens=100)
        
        assert len(chunks) > 1
        for chunk in chunks:
            estimated_tokens = estimate_token_count(chunk)
            assert estimated_tokens <= 120  # Some buffer for estimation error
    
    def test_format_provider_response(self):
        """Test provider response formatting."""
        from core.providers import format_provider_response
        
        openai_response = {
            "summary": "Test summary",
            "usage": {"total_tokens": 500},
            "model": "gpt-4o-mini"
        }
        
        formatted = format_provider_response(openai_response, "openai")
        
        assert formatted["provider"] == "openai"
        assert formatted["summary"] == "Test summary"
        assert formatted["token_usage"] == 500
        assert formatted["model"] == "gpt-4o-mini"


class TestProviderRetryLogic:
    """Test provider retry and error recovery logic."""
    
    @patch('time.sleep')  # Speed up tests
    @patch('openai.OpenAI')
    def test_openai_retry_on_rate_limit(self, mock_openai_class, mock_sleep):
        """Test OpenAI retry logic on rate limit."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        from openai import RateLimitError as OpenAIRateLimitError
        
        # First call fails, second succeeds
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "Success after retry"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 100
        
        mock_client.chat.completions.create.side_effect = [
            OpenAIRateLimitError("Rate limit", Mock(status_code=429), {}),
            mock_response
        ]
        
        # Should succeed after retry
        result = create_openai_summary(
            transcript_text="Test",
            api_key="test-key",
            model="gpt-4o-mini",
            retry_attempts=2
        )
        
        assert result["summary"] == "Success after retry"
        assert mock_client.chat.completions.create.call_count == 2
        mock_sleep.assert_called_once()  # Should have waited between retries
    
    @patch('time.sleep')
    @patch('anthropic.Anthropic')
    def test_anthropic_retry_on_overload(self, mock_anthropic_class, mock_sleep):
        """Test Anthropic retry logic on service overload."""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        from anthropic import OverloadedError
        
        # First call fails, second succeeds
        mock_response = Mock()
        mock_content_block = Mock()
        mock_content_block.text = "Success after retry"
        mock_response.content = [mock_content_block]
        mock_response.usage = Mock()
        mock_response.usage.input_tokens = 50
        mock_response.usage.output_tokens = 25
        
        mock_client.messages.create.side_effect = [
            OverloadedError("Overloaded", Mock(status_code=529), {}),
            mock_response
        ]
        
        # Should succeed after retry
        result = create_anthropic_summary(
            transcript_text="Test",
            api_key="test-key",
            model="claude-3-haiku",
            retry_attempts=2
        )
        
        assert result["summary"] == "Success after retry"
        assert mock_client.messages.create.call_count == 2
        mock_sleep.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])