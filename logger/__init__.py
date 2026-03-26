"""Logger package

Use `start_logger` to create a configured logger instance.
"""

from .core.logger_core import (
    start_logger as start_logger,
    start_logger_from_config as start_logger_from_config,
)

__all__ = ["start_logger", "start_logger_from_config"]
