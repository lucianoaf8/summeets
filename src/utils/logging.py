from rich.logging import RichHandler
import logging
import os
from pathlib import Path
from datetime import datetime

from .exceptions import sanitize_log_message


def get_log_level() -> int:
    """Get logging level from environment or config."""
    # Import here to avoid circular imports
    try:
        from .config import SETTINGS
        level_str = SETTINGS.log_level.upper()
    except Exception:
        level_str = os.environ.get("LOG_LEVEL", "INFO").upper()

    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    return level_map.get(level_str, logging.INFO)


def is_production() -> bool:
    """Check if running in production environment."""
    try:
        from .config import SETTINGS
        return SETTINGS.environment.lower() == "production"
    except Exception:
        return os.environ.get("ENVIRONMENT", "development").lower() == "production"


class SanitizingFormatter(logging.Formatter):
    """
    A logging formatter that sanitizes log messages to prevent log injection.

    Applies sanitization to the message content while preserving the format.
    """

    def format(self, record: logging.LogRecord) -> str:
        # Sanitize the message before formatting
        if record.msg:
            record.msg = sanitize_log_message(str(record.msg))
        # Sanitize any arguments that will be interpolated
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: sanitize_log_message(str(v)) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(sanitize_log_message(str(arg)) for arg in record.args)
        return super().format(record)


def setup_logging(level: int = None, log_file: bool = True) -> None:
    """
    Setup logging with environment-aware defaults.

    Args:
        level: Override log level. If None, uses environment config.
        log_file: Whether to create log file.
    """
    # Use environment-configured level if not specified
    if level is None:
        level = get_log_level()

    # In production, reduce console verbosity
    console_level = logging.WARNING if is_production() else level

    handlers = [RichHandler(rich_tracebacks=True, level=console_level)]

    if log_file:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_handler = logging.FileHandler(
            log_dir / f"summeets_{timestamp}.log",
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(
            SanitizingFormatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        )
        handlers.append(file_handler)
    
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=handlers,
    )