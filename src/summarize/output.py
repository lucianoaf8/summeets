"""Output writing utilities for summarization pipeline."""
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Tuple, Optional

from ..models import SummaryTemplate

log = logging.getLogger(__name__)


def get_output_directory(
    transcript_path: Path,
    template: SummaryTemplate
) -> Path:
    """Get output directory for summary files.

    Creates directory structure: data/summary/<filename>/<template>/

    Args:
        transcript_path: Source transcript path
        template: Summary template used

    Returns:
        Output directory path (created if needed)
    """
    from ..utils.fsio import get_data_manager

    data_mgr = get_data_manager()
    summary_base = data_mgr.base_dir / "summary"
    output_dir = summary_base / transcript_path.stem / template.value
    output_dir.mkdir(parents=True, exist_ok=True)

    log.debug(f"Output directory: {output_dir}")
    return output_dir


def save_json_output(
    output_dir: Path,
    base_name: str,
    json_content: str,
    fallback_data: Optional[dict] = None
) -> Path:
    """Save JSON summary output with validation.

    Args:
        output_dir: Output directory
        base_name: Base filename
        json_content: JSON string to save
        fallback_data: Fallback data if JSON is invalid

    Returns:
        Path to saved JSON file
    """
    json_path = output_dir / f"{base_name}.summary.json"

    try:
        # Validate JSON structure
        json.loads(json_content)
        with open(json_path, 'w', encoding='utf-8') as f:
            f.write(json_content)
        log.info("Saved validated structured JSON")

    except json.JSONDecodeError as e:
        log.warning(f"JSON validation failed: {e}, saving best-effort")
        with open(json_path, 'w', encoding='utf-8') as f:
            f.write(json_content)

    except Exception as e:
        log.error(f"Failed to save JSON: {e}")
        if fallback_data:
            fallback_data["json_extraction_error"] = str(e)
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(fallback_data, f, indent=2, ensure_ascii=False)

    return json_path


def save_markdown_output(
    output_dir: Path,
    base_name: str,
    summary: str,
    template_config,
    transcript_path: Path,
    provider: str,
    model: str,
    auto_detected: bool = False
) -> Path:
    """Save Markdown summary output.

    Args:
        output_dir: Output directory
        base_name: Base filename
        summary: Summary text
        template_config: Template configuration
        transcript_path: Source transcript path
        provider: LLM provider used
        model: Model used
        auto_detected: Whether template was auto-detected

    Returns:
        Path to saved Markdown file
    """
    md_path = output_dir / f"{base_name}.summary.md"

    with open(md_path, 'w', encoding='utf-8') as f:
        if template_config.name == "SOP":
            # SOP gets special timestamp replacement
            formatted = summary.replace(
                "{timestamp}",
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
            f.write(formatted)
        else:
            # Standard format
            f.write(f"# {template_config.name}\n\n")
            f.write(f"**Transcript:** {transcript_path.name}\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Model:** {provider}/{model}\n")
            f.write(f"**Template:** {template_config.name}")
            if auto_detected:
                f.write(" (auto-detected)")
            f.write("\n\n")
            f.write(f"{summary}\n")

    log.info(f"Saved summary: {md_path}")
    return md_path


def create_requirements_json(
    transcript_path: Path,
    provider: str,
    model: str,
    template: SummaryTemplate,
    template_config,
    summary: str
) -> str:
    """Create JSON structure for requirements template.

    Args:
        transcript_path: Source transcript
        provider: LLM provider
        model: Model used
        template: Template enum
        template_config: Template configuration
        summary: Summary content

    Returns:
        JSON string
    """
    data = {
        "transcript": str(transcript_path),
        "provider": provider,
        "model": model,
        "template": template.value,
        "template_name": template_config.name,
        "timestamp": datetime.now().isoformat(),
        "requirements_summary": summary
    }
    return json.dumps(data, indent=2)


def save_summary_outputs(
    transcript_path: Path,
    summary: str,
    json_content: str,
    template: SummaryTemplate,
    template_config,
    provider: str,
    model: str,
    chunk_seconds: int,
    cod_passes: int,
    auto_detected: bool
) -> Tuple[Path, Path]:
    """Save all summary outputs.

    Args:
        transcript_path: Source transcript
        summary: Summary text
        json_content: Structured JSON
        template: Template used
        template_config: Template configuration
        provider: LLM provider
        model: Model used
        chunk_seconds: Chunking setting
        cod_passes: CoD passes used
        auto_detected: Whether template was auto-detected

    Returns:
        Tuple of (json_path, md_path)
    """
    base_name = transcript_path.stem
    output_dir = get_output_directory(transcript_path, template)

    # Fallback data for JSON errors
    fallback_data = {
        "transcript": str(transcript_path),
        "provider": provider,
        "model": model,
        "chunk_seconds": chunk_seconds,
        "cod_passes": cod_passes,
        "template": template.value,
        "template_name": template_config.name,
        "auto_detected": auto_detected,
        "timestamp": datetime.now().isoformat(),
        "summary": summary
    }

    json_path = save_json_output(output_dir, base_name, json_content, fallback_data)

    md_path = save_markdown_output(
        output_dir=output_dir,
        base_name=base_name,
        summary=summary,
        template_config=template_config,
        transcript_path=transcript_path,
        provider=provider,
        model=model,
        auto_detected=auto_detected
    )

    return json_path, md_path
