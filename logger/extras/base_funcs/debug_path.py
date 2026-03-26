"""debug_path.py - Recupera o caminho do log de depuração."""

from logging import Logger

__all__ = ["debug_path"]


def debug_path(self: Logger) -> str | None:
    """Retorna o caminho do log de depuração, se disponível."""
    return getattr(self, "debug_log_path", None)
