import logging
from .progress_handler import ProgressStreamHandler


class FileOnlyFilter(logging.Filter):
    """Filter that skips records marked as ``file_only`` on console."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
        """Return ``False`` for messages flagged as file only."""
        return not getattr(record, "file_only", False)

__all__ = ["ProgressStreamHandler", "FileOnlyFilter"]
