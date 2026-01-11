"""Unit tests for tokenizer module."""
import pytest
from unittest.mock import patch, MagicMock

from src.tokenizer import (
    TokenBudget,
    get_openai_encoding,
    count_openai_text_tokens,
    count_openai_chat_like,
    plan_fit
)


class TestTokenBudget:
    """Tests for TokenBudget dataclass."""

    def test_fits_within_budget(self):
        """Budget fits when input + output + margin <= context."""
        budget = TokenBudget(
            context_window=4000,
            max_output_tokens=1000,
            safety_margin=100
        )
        # 4000 - 1000 - 100 = 2900 available for input
        assert budget.fits(2900) is True
        assert budget.fits(2899) is True

    def test_exceeds_budget(self):
        """Budget doesn't fit when exceeding context."""
        budget = TokenBudget(
            context_window=4000,
            max_output_tokens=1000,
            safety_margin=100
        )
        # 2901 + 1000 + 100 = 4001 > 4000
        assert budget.fits(2901) is False

    def test_zero_margin(self):
        """Works with zero safety margin."""
        budget = TokenBudget(
            context_window=4000,
            max_output_tokens=1000,
            safety_margin=0
        )
        assert budget.fits(3000) is True
        assert budget.fits(3001) is False


class TestOpenAITokenCounting:
    """Tests for OpenAI token counting functions."""

    @pytest.fixture
    def mock_tiktoken(self):
        """Mock tiktoken for testing."""
        with patch('src.tokenizer.tiktoken') as mock:
            mock_enc = MagicMock()
            mock_enc.encode.return_value = [1, 2, 3, 4, 5]  # 5 tokens
            mock.get_encoding.return_value = mock_enc
            yield mock

    def test_get_openai_encoding_default(self, mock_tiktoken):
        """Gets default encoding."""
        get_openai_encoding()
        mock_tiktoken.get_encoding.assert_called_with("o200k_base")

    def test_get_openai_encoding_custom(self, mock_tiktoken):
        """Gets custom encoding."""
        get_openai_encoding("cl100k_base")
        mock_tiktoken.get_encoding.assert_called_with("cl100k_base")

    def test_count_text_tokens(self, mock_tiktoken):
        """Counts tokens in text."""
        count = count_openai_text_tokens("Hello world")
        assert count == 5

    def test_count_chat_like_simple(self, mock_tiktoken):
        """Counts tokens in chat messages."""
        messages = [
            {"role": "user", "content": "Hello"}
        ]
        count = count_openai_chat_like(messages)
        assert count == 5

    def test_count_chat_like_with_list_content(self, mock_tiktoken):
        """Handles list content with text parts."""
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Hello"},
                    {"type": "image", "url": "..."}
                ]
            }
        ]
        count = count_openai_chat_like(messages)
        assert count == 5

    def test_tiktoken_not_installed(self):
        """Raises error when tiktoken not installed."""
        with patch('src.tokenizer.tiktoken', None):
            with pytest.raises(RuntimeError, match="tiktoken not installed"):
                get_openai_encoding()


class TestPlanFit:
    """Tests for plan_fit function."""

    @pytest.fixture
    def mock_openai_count(self):
        """Mock OpenAI token counting."""
        with patch('src.tokenizer.count_openai_chat_like') as mock:
            mock.return_value = 500
            yield mock

    def test_plan_fit_openai_fits(self, mock_openai_count):
        """OpenAI message fits in budget."""
        budget = TokenBudget(
            context_window=4000,
            max_output_tokens=1000,
            safety_margin=100
        )
        messages = [{"role": "user", "content": "Test"}]

        tokens, fits = plan_fit("openai", "gpt-4", messages, budget)

        assert tokens == 500
        assert fits is True

    def test_plan_fit_openai_too_large(self, mock_openai_count):
        """OpenAI message too large for budget."""
        mock_openai_count.return_value = 3500

        budget = TokenBudget(
            context_window=4000,
            max_output_tokens=1000,
            safety_margin=100
        )
        messages = [{"role": "user", "content": "Test"}]

        tokens, fits = plan_fit("openai", "gpt-4", messages, budget)

        assert tokens == 3500
        assert fits is False

    def test_plan_fit_with_system_prompt(self, mock_openai_count):
        """Includes system prompt in count."""
        budget = TokenBudget(context_window=4000, max_output_tokens=1000)
        messages = [{"role": "user", "content": "Test"}]

        plan_fit("openai", "gpt-4", messages, budget, system="Be helpful")

        # Verify system message was included
        call_args = mock_openai_count.call_args[0][0]
        assert len(call_args) == 2
        assert call_args[0]["role"] == "system"

    def test_plan_fit_unknown_provider(self):
        """Raises error for unknown provider."""
        budget = TokenBudget(context_window=4000, max_output_tokens=1000)
        messages = [{"role": "user", "content": "Test"}]

        with pytest.raises(ValueError, match="Unknown provider"):
            plan_fit("unknown", "model", messages, budget)
