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
from src.utils.exceptions import ValidationError, ConfigurationError
from src.utils.startup import check_startup_requirements
from src.utils.shutdown import install_signal_handlers
from src.workflow import WorkflowConfig, execute_workflow

app = typer.Typer(add_completion=False, help="Summeets - Transcribe and summarize meetings")
console = Console()

@app.callback()
def _init(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
    log_file: bool = typer.Option(True, "--log-file/--no-log-file", help="Write logs to file")
) -> None:
    """Initialize logging and signal handlers for all commands."""
    setup_logging(logging.DEBUG if verbose else logging.INFO, log_file=log_file)
    # Install signal handlers for graceful shutdown
    install_signal_handlers()


@app.command("transcribe")
def cmd_transcribe(
    input_file: Optional[Path] = typer.Argument(None, help="Video or audio file"),
    output_dir: Path = typer.Option(Path("out"), "--output", "-o", help="Output directory")
) -> None:
    """Transcribe video/audio using Whisper + diarization."""
    try:
        # Validate API keys on startup
        try:
            check_startup_requirements(require_transcription=True)
        except ConfigurationError as e:
            console.print(f"[red]Configuration Error: {e.message}[/red]")
            if e.details and 'errors' in e.details:
                for err in e.details['errors']:
                    console.print(f"  [dim]- {err}[/dim]")
            raise typer.Exit(1)

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
        # Validate API keys on startup
        try:
            check_startup_requirements(require_summarization=True, provider=provider)
        except ConfigurationError as e:
            console.print(f"[red]Configuration Error: {e.message}[/red]")
            if e.details and 'errors' in e.details:
                for err in e.details['errors']:
                    console.print(f"  [dim]- {err}[/dim]")
            raise typer.Exit(1)

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
        # Validate API keys on startup (need both transcription and summarization)
        try:
            check_startup_requirements(
                require_transcription=True,
                require_summarization=True,
                provider=provider
            )
        except ConfigurationError as e:
            console.print(f"[red]Configuration Error: {e.message}[/red]")
            if e.details and 'errors' in e.details:
                for err in e.details['errors']:
                    console.print(f"  [dim]- {err}[/dim]")
            raise typer.Exit(1)

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


@app.command("health")
def cmd_health() -> None:
    """Check system health and configuration status."""
    from src.utils.startup import (
        validate_ffmpeg_availability,
        validate_disk_space,
        validate_openai_api_key,
        validate_anthropic_api_key,
        validate_replicate_api_token,
        ValidationLevel
    )

    console.print("[bold]Summeets Health Check[/bold]\n")

    all_passed = True

    # Check FFmpeg
    ffmpeg_result = validate_ffmpeg_availability()
    if ffmpeg_result.passed:
        console.print("[green]OK[/green] FFmpeg available")
        if ffmpeg_result.details:
            console.print(f"    [dim]ffmpeg: {ffmpeg_result.details.get('ffmpeg_path', 'N/A')}[/dim]")
            console.print(f"    [dim]ffprobe: {ffmpeg_result.details.get('ffprobe_path', 'N/A')}[/dim]")
    else:
        icon = "[yellow]WARN[/yellow]" if ffmpeg_result.level == ValidationLevel.WARN else "[red]FAIL[/red]"
        console.print(f"{icon} {ffmpeg_result.message}")
        if ffmpeg_result.level == ValidationLevel.ERROR:
            all_passed = False

    # Check disk space
    disk_result = validate_disk_space(min_gb=1.0)
    if disk_result.passed:
        free_gb = disk_result.details.get('free_gb', 0) if disk_result.details else 0
        console.print(f"[green]OK[/green] Disk space: {free_gb:.1f}GB available")
    else:
        console.print(f"[yellow]WARN[/yellow] {disk_result.message}")

    # Check API keys
    console.print("\n[bold]API Keys:[/bold]")

    # OpenAI
    openai_result = validate_openai_api_key(SETTINGS.openai_api_key)
    if openai_result.passed:
        console.print("[green]OK[/green] OpenAI API key configured")
    elif openai_result.level == ValidationLevel.WARN:
        console.print("[yellow]--[/yellow] OpenAI API key not configured")
    else:
        console.print(f"[red]FAIL[/red] {openai_result.message}")
        all_passed = False

    # Anthropic
    anthropic_result = validate_anthropic_api_key(SETTINGS.anthropic_api_key)
    if anthropic_result.passed:
        console.print("[green]OK[/green] Anthropic API key configured")
    elif anthropic_result.level == ValidationLevel.WARN:
        console.print("[yellow]--[/yellow] Anthropic API key not configured")
    else:
        console.print(f"[red]FAIL[/red] {anthropic_result.message}")
        all_passed = False

    # Replicate
    replicate_result = validate_replicate_api_token(SETTINGS.replicate_api_token)
    if replicate_result.passed:
        console.print("[green]OK[/green] Replicate API token configured")
    elif replicate_result.level == ValidationLevel.WARN:
        console.print("[yellow]--[/yellow] Replicate API token not configured")
    else:
        console.print(f"[red]FAIL[/red] {replicate_result.message}")
        all_passed = False

    # Check capabilities
    console.print("\n[bold]Capabilities:[/bold]")

    can_transcribe = replicate_result.passed
    can_summarize_openai = openai_result.passed
    can_summarize_anthropic = anthropic_result.passed

    if can_transcribe:
        console.print("[green]OK[/green] Transcription available (Replicate)")
    else:
        console.print("[yellow]--[/yellow] Transcription unavailable (need Replicate token)")

    if can_summarize_openai:
        console.print("[green]OK[/green] Summarization available (OpenAI)")
    else:
        console.print("[yellow]--[/yellow] OpenAI summarization unavailable")

    if can_summarize_anthropic:
        console.print("[green]OK[/green] Summarization available (Anthropic)")
    else:
        console.print("[yellow]--[/yellow] Anthropic summarization unavailable")

    # Summary
    console.print()
    if all_passed and (can_summarize_openai or can_summarize_anthropic):
        console.print("[bold green]System is healthy and ready to process meetings.[/bold green]")
    elif all_passed:
        console.print("[bold yellow]System is functional but missing API keys for some operations.[/bold yellow]")
    else:
        console.print("[bold red]System has configuration issues that need to be resolved.[/bold red]")
        raise typer.Exit(1)

@app.command("tui")
def cmd_tui() -> None:
    """Launch the Textual-based TUI for running workflows."""
    try:
        from .tui import run as start_tui
        start_tui()
    except Exception as e:
        console.print(f"[red]Failed to launch TUI: {e}[/red]")
        raise typer.Exit(1)

@app.command("migrate-data")
def cmd_migrate_data(
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be migrated without making changes"),
    move: bool = typer.Option(False, "--move", "-m", help="Move files instead of copying"),
    legacy_input: Path = typer.Option(Path("input"), "--legacy-input", help="Legacy input directory"),
    legacy_output: Path = typer.Option(Path("out"), "--legacy-output", help="Legacy output directory"),
    target_dir: Path = typer.Option(Path("data"), "--target", "-t", help="Target data directory")
) -> None:
    """Migrate from legacy to new data directory structure."""
    from src.utils.migration import migrate_to_new_structure, cleanup_legacy_directories

    if dry_run:
        console.print("[yellow]DRY RUN - No files will be modified[/yellow]\n")

    console.print("[bold]Migrating data structure...[/bold]")
    console.print(f"  Legacy input: {legacy_input}")
    console.print(f"  Legacy output: {legacy_output}")
    console.print(f"  Target: {target_dir}\n")

    result = migrate_to_new_structure(
        legacy_input=legacy_input,
        legacy_output=legacy_output,
        new_base=target_dir,
        dry_run=dry_run,
        move=move
    )

    # Display results
    console.print(f"\n[green]✓ Migrated:[/green] {result.success_count} files")
    console.print(f"[yellow]⊘ Skipped:[/yellow] {result.skip_count} files")
    console.print(f"[red]✗ Errors:[/red] {result.error_count} files")

    if result.migrated and not dry_run:
        console.print("\n[dim]Migrated files:[/dim]")
        for item in result.migrated[:10]:  # Show first 10
            console.print(f"  {item['source']} -> {item['target']}")
        if len(result.migrated) > 10:
            console.print(f"  ... and {len(result.migrated) - 10} more")

    if result.errors:
        console.print("\n[red]Errors:[/red]")
        for error in result.errors:
            console.print(f"  {error['file']}: {error['error']}")

    # Cleanup empty directories
    if not dry_run and result.success_count > 0:
        cleanup = cleanup_legacy_directories(legacy_input, legacy_output, dry_run=False)
        if cleanup.get("input_removed"):
            console.print(f"\n[dim]Removed empty legacy directory: {legacy_input}[/dim]")
        if cleanup.get("output_removed"):
            console.print(f"[dim]Removed empty legacy directory: {legacy_output}[/dim]")


@app.command("jobs")
def cmd_jobs(
    limit: int = typer.Option(10, "--limit", "-l", help="Number of jobs to show"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output")
) -> None:
    """List recent processing jobs."""
    from src.utils.job_history import get_job_store

    store = get_job_store()
    jobs = store.list_jobs(limit=limit, status=status)

    if not jobs:
        console.print("[yellow]No jobs found[/yellow]")
        return

    table = Table(title=f"Recent Jobs (showing {len(jobs)} of {limit})")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Status", style="white")
    table.add_column("Type", style="dim")
    table.add_column("Input File", style="white", max_width=40)
    table.add_column("Started", style="dim")

    for job in jobs:
        job_id = job.get('job_id', 'unknown')[:8]
        job_status = job.get('status', 'unknown')
        job_type = job.get('job_type', '-')
        input_file = job.get('input_file', '-')
        if len(input_file) > 40:
            input_file = "..." + input_file[-37:]
        started = job.get('started_at', job.get('created_at', '-'))
        if started and len(started) > 16:
            started = started[:16]

        # Color status
        if job_status == 'completed':
            status_display = f"[green]{job_status}[/green]"
        elif job_status == 'failed':
            status_display = f"[red]{job_status}[/red]"
        elif job_status == 'started':
            status_display = f"[yellow]{job_status}[/yellow]"
        else:
            status_display = job_status

        table.add_row(job_id, status_display, job_type, input_file, started)

    console.print(table)

    if verbose:
        stats = store.get_stats()
        console.print(f"\n[dim]Total jobs: {stats['total']}[/dim]")
        for s, count in stats.get('by_status', {}).items():
            console.print(f"[dim]  {s}: {count}[/dim]")


@app.command("job-cleanup")
def cmd_job_cleanup(
    days: int = typer.Option(30, "--days", "-d", help="Remove jobs older than N days"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be removed")
) -> None:
    """Clean up old job history files."""
    from src.utils.job_history import get_job_store

    store = get_job_store()

    if dry_run:
        # Count files that would be removed
        from datetime import datetime
        cutoff = datetime.now().timestamp() - (days * 86400)
        count = sum(1 for f in store.storage_path.glob("*.json") if f.stat().st_mtime < cutoff)
        console.print(f"[yellow]DRY RUN: Would remove {count} job files older than {days} days[/yellow]")
    else:
        removed = store.cleanup_old_jobs(days=days)
        console.print(f"[green]✓ Removed {removed} old job files[/green]")


def main() -> None:
    app()

if __name__ == "__main__":
    main()
