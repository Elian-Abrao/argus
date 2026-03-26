"""path.py - Recupera o caminho do arquivo de log principal."""

from logging import Logger

__all__ = ["path"]


def path(self: Logger) -> str | None:
    """Retorna o caminho do arquivo de log, se definido."""
    return getattr(self, "log_path", None)
