"""
Logging configuration for ServerForge.

This module sets up comprehensive logging with file rotation,
colored console output, and configurable log levels.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler

from .settings import config

# Global console for rich output
console = Console()


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color coding for different log levels."""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        if record.levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[record.levelname]}"
                f"{record.levelname}"
                f"{self.RESET}"
            )
        return super().format(record)


def setup_logging(
    log_level: Optional[str] = None,
    enable_file_logging: Optional[bool] = None,
    enable_rich_logging: Optional[bool] = None,
) -> None:
    """Setup logging configuration."""
    
    # Get configuration values
    log_level = log_level or config.get("logging.level", "INFO")
    enable_file_logging = enable_file_logging if enable_file_logging is not None else config.get("logging.file_logging", True)
    enable_rich_logging = enable_rich_logging if enable_rich_logging is not None else config.get("ui.colored_output", True)
    
    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Clear any existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Set root logger level
    root_logger.setLevel(numeric_level)
    
    # Console handler
    if enable_rich_logging and sys.stdout.isatty():
        # Use Rich handler for colored output
        console_handler = RichHandler(
            console=console,
            show_time=False,
            show_path=False,
            markup=True,
            rich_tracebacks=True,
        )
        console_formatter = logging.Formatter(
            "%(message)s"
        )
    else:
        # Use standard console handler
        console_handler = logging.StreamHandler(sys.stdout)
        if config.get("ui.colored_output", True) and sys.stdout.isatty():
            console_formatter = ColoredFormatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%H:%M:%S"
            )
        else:
            console_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%H:%M:%S"
            )
    
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(numeric_level)
    root_logger.addHandler(console_handler)
    
    # File handler (if enabled)
    if enable_file_logging:
        try:
            log_file = Path(config.get("logging.log_file"))
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            max_bytes = _parse_size(config.get("logging.max_log_size", "10MB"))
            backup_count = config.get("logging.backup_count", 5)
            
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(logging.DEBUG)  # File logs everything
            root_logger.addHandler(file_handler)
            
        except Exception as e:
            # If file logging fails, log to console
            logging.getLogger(__name__).warning(f"Failed to setup file logging: {e}")
    
    # Set specific logger levels
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    # Log the setup
    logger = logging.getLogger(__name__)
    logger.debug(f"Logging setup complete. Level: {log_level}, File: {enable_file_logging}")


def _parse_size(size_str: str) -> int:
    """Parse size string like '10MB' to bytes."""
    size_str = size_str.upper()
    
    multipliers = {
        'B': 1,
        'KB': 1024,
        'MB': 1024 ** 2,
        'GB': 1024 ** 3,
    }
    
    for suffix, multiplier in multipliers.items():
        if size_str.endswith(suffix):
            try:
                number = float(size_str[:-len(suffix)])
                return int(number * multiplier)
            except ValueError:
                break
    
    # Default to 10MB if parsing fails
    return 10 * 1024 ** 2


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(name)