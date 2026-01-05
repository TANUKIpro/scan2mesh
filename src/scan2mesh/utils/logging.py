"""Logging configuration utilities."""

import logging
import sys
from pathlib import Path


def setup_logging(
    level: int = logging.INFO,
    log_file: Path | None = None,
    use_rich: bool = True,
) -> logging.Logger:
    """Set up logging for scan2mesh.

    Configures console output (optionally with rich formatting) and
    optional file output for debugging.

    Args:
        level: Logging level (default: INFO)
        log_file: Optional path to log file for DEBUG output
        use_rich: Whether to use rich formatting for console (default: True)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("scan2mesh")
    logger.setLevel(logging.DEBUG)  # Capture all levels, filter in handlers

    # Clear existing handlers
    logger.handlers.clear()

    # Console handler
    console_handler: logging.Handler
    if use_rich:
        try:
            from rich.logging import RichHandler

            console_handler = RichHandler(
                level=level,
                rich_tracebacks=True,
                show_path=False,
            )
            console_handler.setFormatter(logging.Formatter("%(message)s"))
        except ImportError:
            # Fall back to standard handler if rich is not available
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_handler.setFormatter(
                logging.Formatter("%(levelname)s - %(message)s")
            )
    else:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))

    logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "scan2mesh") -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Logger name (default: scan2mesh)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
