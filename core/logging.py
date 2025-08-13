from rich.logging import RichHandler
import logging
from pathlib import Path
from datetime import datetime

def setup_logging(level: int = logging.INFO, log_file: bool = True) -> None:
    handlers = [RichHandler(rich_tracebacks=True)]
    
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
            logging.Formatter(
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