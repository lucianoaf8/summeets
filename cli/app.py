import typer
import logging
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table

from core.utils.logging import setup_logging
from core.utils.config_manager import get_configuration_summary
from core.transcribe import transcribe_audio
from core.summarize.pipeline import run as summarize_transcript
from core.summarize.templates import SummaryTemplates
from core.models import SummaryTemplate
from core.utils.fsio import get_data_manager
from core.utils.validation import sanitize_path_input, validate_transcript_file, validate_output_dir, validate_model_name
from core.utils.exceptions import ValidationError

app = typer.Typer(add_completion=False, help="Summeets - Transcribe and summarize meetings")
console = Console()

@app.callback()
def _init(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
    log_file: bool = typer.Option(True, "--log-file/--no-log-file", help="Write logs to file")
):
    """Initialize logging for all commands."""
    setup_logging(logging.DEBUG if verbose else logging.INFO, log_file=log_file)


@app.command("transcribe")
def cmd_transcribe(
    audio: Optional[Path] = typer.Argument(None, help="Audio file or directory"),
    output_dir: Path = typer.Option(Path("out"), "--output", "-o", help="Output directory")
):
    """Transcribe audio using Whisper + diarization."""
    try:
        # Input validation
        if audio:
            audio_str = sanitize_path_input(str(audio))
            audio = Path(audio_str)
        
        output_str = sanitize_path_input(str(output_dir))
        output_dir = Path(output_str)
        validate_output_dir(output_dir)
        
        json_path, srt_path, audit_path = transcribe_audio(
            audio_path=audio,
            output_dir=output_dir
        )
        console.print(f"[green]✓[/green] Transcription complete:")
        console.print(f"  JSON: [cyan]{json_path}[/cyan]")
        console.print(f"  SRT: [cyan]{srt_path}[/cyan]")
        console.print(f"  Audit: [cyan]{audit_path}[/cyan]")
    except ValidationError as e:
        console.print(f"[red]Validation Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

@app.command("summarize")
def cmd_summarize(
    transcript: Path = typer.Argument(..., help="Transcript JSON or SRT file"),
    provider: str = typer.Option("openai", "--provider", "-p", help="LLM provider: openai|anthropic"),
    model: str = typer.Option("gpt-4o-mini", "--model", "-m", help="Model name"),
    chunk_seconds: int = typer.Option(1800, "--chunk-seconds", help="Chunk size in seconds"),
    cod_passes: int = typer.Option(2, "--cod-passes", help="Chain-of-Density passes"),
    max_tokens: int = typer.Option(3000, "--max-tokens", help="Max output tokens"),
    template: str = typer.Option("default", "--template", "-t", help="Summary template: default|sop|decision|brainstorm"),
    auto_detect: bool = typer.Option(True, "--auto-detect/--no-auto-detect", help="Auto-detect template type")
):
    """Summarize meeting transcript using LLM."""
    try:
        # Input validation
        transcript_str = sanitize_path_input(str(transcript))
        transcript = Path(transcript_str)
        validate_transcript_file(transcript)
        
        # Validate provider options
        if provider not in ["openai", "anthropic"]:
            raise ValidationError(f"Invalid provider '{provider}'. Must be 'openai' or 'anthropic'")
        
        # Validate model name
        model = validate_model_name(model)
        
        # Validate template
        if template not in ["default", "sop", "decision", "brainstorm"]:
            raise ValidationError(f"Invalid template '{template}'. Must be one of: default, sop, decision, brainstorm")
        template_enum = SummaryTemplate(template)
        
        # Validate numeric parameters
        if chunk_seconds <= 0:
            raise ValidationError("Chunk seconds must be positive")
        if cod_passes <= 0:
            raise ValidationError("CoD passes must be positive")
        if max_tokens <= 0:
            raise ValidationError("Max tokens must be positive")
        
        json_path = summarize_transcript(
            transcript_path=transcript,
            provider=provider,
            model=model,
            chunk_seconds=chunk_seconds,
            cod_passes=cod_passes,
            template=template_enum,
            auto_detect_template=auto_detect
        )
        # Get output paths for display
        output_dir = json_path.parent
        base_name = transcript.stem
        md_path = output_dir / f"{base_name}.summary.md"
        
        console.print(f"[green]✓[/green] Summary complete:")
        console.print(f"  Markdown: [cyan]{md_path}[/cyan]")
        console.print(f"  JSON: [cyan]{json_path}[/cyan]")
        
        # Show template info
        if auto_detect:
            console.print(f"  Template: [yellow]{template}[/yellow] (auto-detected: {auto_detect})")
    except ValidationError as e:
        console.print(f"[red]Validation Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command("templates")
def cmd_templates():
    """List available summary templates."""
    console.print("\n[bold]Available Summary Templates:[/bold]\n")
    
    templates = SummaryTemplates.list_templates()
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Template", style="cyan", no_wrap=True)
    table.add_column("Description", style="white")
    table.add_column("Use Case", style="dim")
    
    template_use_cases = {
        "default": "General meetings, discussions, status updates",
        "sop": "Training sessions, process documentation, tutorials",
        "decision": "Decision-making meetings, strategy sessions",
        "brainstorm": "Creative sessions, idea generation, planning"
    }
    
    for template_key, description in templates.items():
        table.add_row(
            template_key,
            description,
            template_use_cases.get(template_key, "")
        )
    
    console.print(table)
    console.print("\n[dim]Use with: summeets summarize --template <template_name>[/dim]")
    console.print("[dim]Auto-detection is enabled by default (--auto-detect)[/dim]")

@app.command("process")
def cmd_process(
    audio: Optional[Path] = typer.Argument(None, help="Audio file or directory"),
    provider: str = typer.Option("openai", "--provider", "-p", help="LLM provider"),
    model: str = typer.Option("gpt-4o-mini", "--model", "-m", help="Model name"),
    output_dir: Path = typer.Option(Path("out"), "--output", "-o", help="Output directory"),
    template: str = typer.Option("default", "--template", "-t", help="Summary template: default|sop|decision|brainstorm"),
    auto_detect: bool = typer.Option(True, "--auto-detect/--no-auto-detect", help="Auto-detect template type")
):
    """Complete pipeline: transcribe and summarize audio."""
    console.print("[bold]Starting complete processing pipeline[/bold]")
    
    try:
        # Input validation
        if audio:
            audio_str = sanitize_path_input(str(audio))
            audio = Path(audio_str)
        
        output_str = sanitize_path_input(str(output_dir))
        output_dir = Path(output_str)
        validate_output_dir(output_dir)
        
        # Validate provider options
        if provider not in ["openai", "anthropic"]:
            raise ValidationError(f"Invalid provider '{provider}'. Must be 'openai' or 'anthropic'")
        
        # Validate model name
        model = validate_model_name(model)
        
        # Validate template
        if template not in ["default", "sop", "decision", "brainstorm"]:
            raise ValidationError(f"Invalid template '{template}'. Must be one of: default, sop, decision, brainstorm")
        template_enum = SummaryTemplate(template)
        
        # Transcribe
        console.print("\n[yellow]Step 1/2:[/yellow] Transcribing audio...")
        json_path, srt_path, audit_path = transcribe_audio(
            audio_path=audio,
            output_dir=output_dir
        )
        console.print(f"[green]✓[/green] Transcription complete")
        console.print(f"  JSON: [cyan]{json_path}[/cyan]")
        
        # Summarize
        console.print("\n[yellow]Step 2/2:[/yellow] Summarizing transcript...")
        summary_json = summarize_transcript(
            transcript_path=json_path,
            provider=provider,
            model=model,
            template=template_enum,
            auto_detect_template=auto_detect
        )
        # Get output paths for display
        output_base = json_path.stem
        md_path = output_dir / f"{output_base}.summary.md"
        
        console.print(f"[green]✓[/green] Summary complete:")
        console.print(f"  Markdown: [cyan]{md_path}[/cyan]")
        console.print(f"  JSON: [cyan]{summary_json}[/cyan]")
        
        console.print("\n[bold green]✓ Pipeline complete![/bold green]")
        
    except ValidationError as e:
        console.print(f"[red]Validation Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Pipeline failed: {e}[/red]")
        raise typer.Exit(1)

@app.command("config")
def cmd_config():
    """Show current configuration."""
    table = Table(title="Summeets Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="yellow")
    
    config = get_configuration_summary()
    
    # Add configuration rows in a logical order
    table.add_row("Provider", config['provider'])
    table.add_row("Model", config['model'])
    table.add_row("Output Directory", config['output_directory'])
    table.add_row("Data Directory", config['data_directory'])
    table.add_row("Temp Directory", config['temp_directory'])
    table.add_row("Summary Max Tokens", str(config['summary_max_tokens']))
    table.add_row("Chunk Seconds", str(config['summary_chunk_seconds']))
    table.add_row("CoD Passes", str(config['summary_cod_passes']))
    table.add_row("Transcription Model", config['transcription_model'])
    table.add_row("FFmpeg Binary", config['ffmpeg_binary'])
    table.add_row("FFprobe Binary", config['ffprobe_binary'])
    table.add_row("OpenAI API Key", config['openai_api_key'])
    table.add_row("Anthropic API Key", config['anthropic_api_key'])
    table.add_row("Replicate Token", config['replicate_api_token'])
    
    console.print(table)

def main():
    app()

if __name__ == "__main__":
    main()