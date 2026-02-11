"""Summarization strategies for different use cases.

Provides pluggable summarization strategies including:
- MapReduceStrategy: Parallel chunk summarization with reduction
- TemplateAwareStrategy: Template-specific structured output

Classes:
    SummarizationStrategy: Protocol for strategy implementations
    MapReduceStrategy: Map-reduce summarization
    TemplateAwareStrategy: Template-aware summarization

Functions:
    call_llm: Unified LLM call wrapper
"""
import logging
from typing import List, Dict, Protocol, Optional

from ..utils.config import SETTINGS
from ..utils.sanitization import sanitize_transcript_for_summary
from ..providers import openai_client, anthropic_client

log = logging.getLogger(__name__)


class SummarizationStrategy(Protocol):
    """Protocol for summarization strategies."""

    def summarize(
        self,
        chunks: List[List[Dict]],
        provider: str,
        model: str
    ) -> str:
        """Summarize transcript chunks.

        Args:
            chunks: List of segment lists
            provider: LLM provider name
            model: Model identifier

        Returns:
            Summary text
        """
        ...


def call_llm(
    prompt: str,
    system_prompt: Optional[str],
    provider: str,
    max_tokens: int,
    enable_thinking: bool = False,
    thinking_budget: int = 0
) -> str:
    """Unified LLM call wrapper.

    Args:
        prompt: User prompt text
        system_prompt: System prompt (optional)
        provider: Provider name (openai/anthropic)
        max_tokens: Maximum output tokens
        enable_thinking: Enable extended thinking (Anthropic only)
        thinking_budget: Thinking token budget

    Returns:
        LLM response text

    Raises:
        ValueError: If provider is unknown
    """
    if provider == "openai":
        return openai_client.summarize_text(
            prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens
        )
    elif provider == "anthropic":
        return anthropic_client.summarize_text(
            prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            enable_thinking=enable_thinking,
            thinking_budget=thinking_budget
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")


class MapReduceStrategy:
    """Map-reduce summarization strategy.

    Summarizes chunks independently (map) then combines (reduce).
    """

    def __init__(
        self,
        system_prompt: str,
        chunk_prompt_template: str,
        reduce_prompt_template: str,
        chunk_max_tokens: int = 800
    ):
        self.system_prompt = system_prompt
        self.chunk_prompt_template = chunk_prompt_template
        self.reduce_prompt_template = reduce_prompt_template
        self.chunk_max_tokens = chunk_max_tokens

    def summarize(
        self,
        chunks: List[List[Dict]],
        provider: str,
        model: str
    ) -> str:
        """Execute map-reduce summarization."""
        from .chunking import format_chunk_text

        log.info(f"Map-reduce: {len(chunks)} chunks with {provider}")

        # Map phase
        partial_summaries = []
        for i, chunk in enumerate(chunks):
            log.info(f"Summarizing chunk {i+1}/{len(chunks)}")

            chunk_text = sanitize_transcript_for_summary(format_chunk_text(chunk))
            prompt = self.chunk_prompt_template.format(chunk=chunk_text)

            summary = call_llm(
                prompt=prompt,
                system_prompt=self.system_prompt,
                provider=provider,
                max_tokens=self.chunk_max_tokens
            )
            partial_summaries.append(summary)

        # Reduce phase
        if len(partial_summaries) == 1:
            return partial_summaries[0]

        parts_text = self._format_partials(partial_summaries)
        reduce_prompt = self.reduce_prompt_template.format(parts=parts_text)

        final_summary = call_llm(
            prompt=reduce_prompt,
            system_prompt=self.system_prompt,
            provider=provider,
            max_tokens=SETTINGS.summary_max_tokens
        )

        return final_summary

    def _format_partials(self, summaries: List[str]) -> str:
        """Format partial summaries for reduce step."""
        parts = []
        for i, summary in enumerate(summaries):
            parts.append(f"### Part {i+1}\n{summary}")
        return "\n\n".join(parts)


class TemplateAwareStrategy:
    """Template-specific summarization strategy.

    Uses template prompts directly for structured output.
    """

    def __init__(self, template_config):
        """Initialize with template configuration.

        Args:
            template_config: Template configuration object with
                system_prompt, user_prompt_template, max_tokens, name
        """
        self.template_config = template_config

    def summarize(
        self,
        chunks: List[List[Dict]],
        provider: str,
        model: str
    ) -> str:
        """Execute template-aware summarization."""
        log.info(f"Template-aware: {self.template_config.name}")

        if len(chunks) == 1:
            return self._single_chunk(chunks[0], provider, model)
        else:
            return self._multi_chunk(chunks, provider, model)

    def _single_chunk(
        self,
        chunk: List[Dict],
        provider: str,
        model: str
    ) -> str:
        """Process single chunk with template."""
        transcript_text = sanitize_transcript_for_summary(self._format_transcript(chunk))
        formatted = f"MEETING TRANSCRIPT:\n\n{transcript_text}"

        prompt = self.template_config.user_prompt_template.format(
            transcript=formatted
        )

        enable_thinking = self._should_enable_thinking(model)

        return call_llm(
            prompt=prompt,
            system_prompt=self.template_config.system_prompt,
            provider=provider,
            max_tokens=self.template_config.max_tokens,
            enable_thinking=enable_thinking,
            thinking_budget=SETTINGS.thinking_budget_extended if enable_thinking else 0
        )

    def _multi_chunk(
        self,
        chunks: List[List[Dict]],
        provider: str,
        model: str
    ) -> str:
        """Process multiple chunks with template."""
        partial_summaries = []

        for i, chunk in enumerate(chunks):
            log.info(f"Processing chunk {i+1}/{len(chunks)}")

            transcript_text = sanitize_transcript_for_summary(self._format_transcript(chunk))
            prompt = (
                "Extract requirements from this transcript chunk using the same "
                f"structure as the full analysis:\n\n{transcript_text}"
            )

            enable_thinking = self._should_enable_thinking(model)
            chunk_max = SETTINGS.thinking_budget_default if enable_thinking else 800

            summary = call_llm(
                prompt=prompt,
                system_prompt=self.template_config.system_prompt,
                provider=provider,
                max_tokens=chunk_max,
                enable_thinking=enable_thinking,
                thinking_budget=(SETTINGS.thinking_budget_default - 1000) if enable_thinking else 0
            )
            partial_summaries.append(summary)

        # Combine partials
        combined_prompt = (
            "Combine these partial requirements extractions into a final structured analysis. "
            "Merge and deduplicate requirements while maintaining the structure:\n\n"
            "Partial extractions:\n" + "\n\n---\n\n".join(partial_summaries)
        )

        enable_thinking = self._should_enable_thinking(model)

        return call_llm(
            prompt=combined_prompt,
            system_prompt=self.template_config.system_prompt,
            provider=provider,
            max_tokens=self.template_config.max_tokens,
            enable_thinking=enable_thinking,
            thinking_budget=SETTINGS.thinking_budget_extended if enable_thinking else 0
        )

    def _format_transcript(self, chunk: List[Dict]) -> str:
        """Format transcript chunk for template processing."""
        lines = []
        for segment in chunk:
            speaker = segment.get('speaker', 'Unknown')
            text = segment.get('text', '').strip()
            if text:
                lines.append(f"[{speaker}]: {text}")
        return '\n'.join(lines)

    def _should_enable_thinking(self, model: str) -> bool:
        """Check if extended thinking should be enabled."""
        model_supports = "claude-3-7" in model or "claude-4" in model
        is_requirements = self.template_config.name == "Requirements Extraction v3"
        return model_supports and is_requirements
