import typer
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from rich.console import Console
from rich.table import Table

from src.utils.logging import setup_logging
from src.utils.config import SETTINGS, get_configuration_summary
from src.transcribe import transcribe_audio
from src.summarize.pipeline import run as summarize_transcript
from src.summarize.templates import SummaryTemplates
from src.models import SummaryTemplate
from src.utils.fsio import get_data_manager
from src.utils.validation import (
    sanitize_path_input, validate_transcript_file, validate_output_dir,
    validate_model_name, detect_file_type, validate_llm_provider, validate_summary_template
)
from src.utils.exceptions import ValidationError
from src.workflow import WorkflowConfig, execute_workflow

app = typer.Typer(add_completion=False, help="Summeets - Transcribe and summarize meetings")
console = Console()

@app.callback()
def _init(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
    log_file: bool = typer.Option(True, "--log-file/--no-log-file", help="Write logs to file")
) -> None:
    """Initialize logging for all commands."""
    setup_logging(logging.DEBUG if verbose else logging.INFO, log_file=log_file)


@app.command("transcribe")
def cmd_transcribe(
    input_file: Optional[Path] = typer.Argument(None, help="Video or audio file"),
    output_dir: Path = typer.Option(Path("out"), "--output", "-o", help="Output directory")
) -> None:
    """Transcribe video/audio using Whisper + diarization."""
    try:
        # Input validation
        if not input_file:
            input_file_str = typer.prompt("Enter video or audio file path")
            input_file = Path(sanitize_path_input(input_file_str))
        else:
            input_file_str = sanitize_path_input(str(input_file))
            input_file = Path(input_file_str)

        if not input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")

        output_str = sanitize_path_input(str(output_dir))
        output_dir = Path(output_str)
        validate_output_dir(output_dir)

        # Detect file type
        file_type = detect_file_type(input_file)
        console.print(f"[cyan]Detected file type:[/cyan] {file_type}")

        if file_type == "transcript":
            console.print("[yellow]Warning:[/yellow] File is already a transcript")
            raise typer.Exit(0)

        # Use workflow for video files, direct transcribe for audio
        if file_type == "video":
            console.print("[yellow]Video file detected - extracting audio first...[/yellow]")

            # Create workflow configuration for video transcription
            config = WorkflowConfig(
                input_file=input_file,
                output_dir=output_dir,
                extract_audio=True,
                process_audio=True,
                transcribe=True,
                summarize=False,  # Only transcribe, don't summarize
                audio_format="m4a",
                audio_quality="high",
                normalize_audio=True
            )

            # Execute workflow
            def progress_callback(step: int, total: int, step_name: str, status: str) -> None:
                console.print(f"[yellow]Step {step}/{total}:[/yellow] {status}")

            results = execute_workflow(config, progress_callback)

            # Extract transcript file path from results
            for step_name, step_results in results.items():
                if step_name == "transcribe" and isinstance(step_results, dict):
                    if "transcript_file" in step_results:
                        json_path = Path(step_results["transcript_file"])
                        srt_path = json_path.with_suffix('.srt')
                        audit_path = json_path.with_suffix('.audit.json')

                        console.print(f"[green]✓[/green] Transcription complete:")
                        console.print(f"  JSON: [cyan]{json_path}[/cyan]")
                        if srt_path.exists():
                            console.print(f"  SRT: [cyan]{srt_path}[/cyan]")
                        if audit_path.exists():
                            console.print(f"  Audit: [cyan]{audit_path}[/cyan]")
                        break
        else:
            # Direct transcription for audio files
            json_path, srt_path, audit_path = transcribe_audio(
                audio_path=input_file,
                output_dir=output_dir
            )
            console.print(f"[green]✓[/green] Transcription complete:")
            console.print(f"  JSON: [cyan]{json_path}[/cyan]")
            console.print(f"  SRT: [cyan]{srt_path}[/cyan]")
            console.print(f"  Audit: [cyan]{audit_path}[/cyan]")

    except ValidationError as e:
        console.print(f"[red]Validation Error: {e}[/red]")
        raise typer.Exit(1)
    except FileNotFoundError as e:
        console.print(f"[red]File Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

@app.command("summarize")
def cmd_summarize(
    transcript: Path = typer.Argument(..., help="Transcript JSON or SRT file"),
    provider: str = typer.Option(SETTINGS.provider, "--provider", "-p", help="LLM provider: openai|anthropic"),
    model: str = typer.Option(SETTINGS.model, "--model", "-m", help="Model name"),
    chunk_seconds: int = typer.Option(1800, "--chunk-seconds", help="Chunk size in seconds"),
    cod_passes: int = typer.Option(2, "--cod-passes", help="Chain-of-Density passes"),
    max_tokens: int = typer.Option(3000, "--max-tokens", help="Max output tokens"),
    template: str = typer.Option("default", "--template", "-t", help="Summary template: default|sop|decision|brainstorm|requirements"),
    auto_detect: bool = typer.Option(True, "--auto-detect/--no-auto-detect", help="Auto-detect template type")
) -> None:
    """Summarize meeting transcript using LLM."""
    try:
        # Input validation
        transcript_str = sanitize_path_input(str(transcript))
        transcript = Path(transcript_str)
        validate_transcript_file(transcript)
        
        # Validate provider, model, and template using centralized validators
        provider = validate_llm_provider(provider)
        model = validate_model_name(model)
        template = validate_summary_template(template)
        template_enum = SummaryTemplate(template)
        
        # Validate numeric parameters
        if chunk_seconds <= 0:
            raise ValidationError("Chunk seconds must be positive")
        if cod_passes <= 0:
            raise ValidationError("CoD passes must be positive")
        if max_tokens <= 0:
            raise ValidationError("Max tokens must be positive")
        
        json_path, md_path = summarize_transcript(
            transcript_path=transcript,
            provider=provider,
            model=model,
            chunk_seconds=chunk_seconds,
            cod_passes=cod_passes,
            template=template_enum,
            auto_detect_template=auto_detect
        )
        
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
def cmd_templates() -> None:
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
        "brainstorm": "Creative sessions, idea generation, planning",
        "requirements": "Requirements review, criteria analysis, project specifications"
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
    input_file: Optional[Path] = typer.Argument(None, help="Video, audio, or transcript file"),
    provider: str = typer.Option("openai", "--provider", "-p", help="LLM provider"),
    model: str = typer.Option("gpt-4o-mini", "--model", "-m", help="Model name"),
    output_dir: Path = typer.Option(Path("out"), "--output", "-o", help="Output directory"),
    template: str = typer.Option("default", "--template", "-t", help="Summary template: default|sop|decision|brainstorm|requirements"),
    auto_detect: bool = typer.Option(True, "--auto-detect/--no-auto-detect", help="Auto-detect template type")
) -> None:
    """Complete pipeline: process video/audio/transcript files."""
    console.print("[bold]Starting complete processing pipeline[/bold]")

    try:
        # Input validation
        if not input_file:
            input_file_str = typer.prompt("Enter video, audio, or transcript file path")
            input_file = Path(sanitize_path_input(input_file_str))
        else:
            input_file_str = sanitize_path_input(str(input_file))
            input_file = Path(input_file_str)

        if not input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")

        output_str = sanitize_path_input(str(output_dir))
        output_dir = Path(output_str)
        validate_output_dir(output_dir)

        # Validate provider, model, and template using centralized validators
        provider = validate_llm_provider(provider)
        model = validate_model_name(model)
        template = validate_summary_template(template)

        # Detect file type
        file_type = detect_file_type(input_file)
        console.print(f"[cyan]Detected file type:[/cyan] {file_type}")

        # Create workflow configuration
        config = WorkflowConfig(
            input_file=input_file,
            output_dir=output_dir,
            # Enable appropriate steps based on file type
            extract_audio=(file_type == "video"),
            process_audio=(file_type in ["video", "audio"]),
            transcribe=(file_type in ["video", "audio"]),
            summarize=True,
            # Audio settings
            audio_format="m4a",
            audio_quality="high",
            normalize_audio=True,
            # Summarization settings
            summary_template=template,
            provider=provider,
            model=model,
            auto_detect_template=auto_detect
        )

        # Define progress callback
        def progress_callback(step: int, total: int, step_name: str, status: str) -> None:
            console.print(f"[yellow]Step {step}/{total}:[/yellow] {status}")

        # Execute workflow
        results = execute_workflow(config, progress_callback)

        # Display results
        console.print("\n[bold green]✓ Pipeline complete![/bold green]")
        console.print("\n[cyan]Results:[/cyan]")

        for step_name, step_results in results.items():
            if isinstance(step_results, dict) and not step_results.get("skipped"):
                console.print(f"  [bold]{step_name}:[/bold]")
                if "output_file" in step_results:
                    console.print(f"    Output: {step_results['output_file']}")
                if "transcript_file" in step_results:
                    console.print(f"    Transcript: {step_results['transcript_file']}")
                if "summary_file" in step_results:
                    console.print(f"    Summary: {step_results['summary_file']}")

    except ValidationError as e:
        console.print(f"[red]Validation Error: {e}[/red]")
        raise typer.Exit(1)
    except FileNotFoundError as e:
        console.print(f"[red]File Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Pipeline failed: {e}[/red]")
        raise typer.Exit(1)

@app.command("config")
def cmd_config() -> None:
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

@app.command("tui")
def cmd_tui() -> None:
    """Launch the Textual-based TUI for running workflows."""
    try:
        from .tui import run as start_tui
        start_tui()
    except Exception as e:
        console.print(f"[red]Failed to launch TUI: {e}[/red]")
        raise typer.Exit(1)

def main() -> None:
    app()

if __name__ == "__main__":
    main()
