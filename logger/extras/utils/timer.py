"""timer.py - Utilitário de contagem de tempo para o logger."""

from logging import Logger
import time

__all__ = ["Timer", "logger_timer"]


class Timer:
    """Context manager simples para medir duração de blocos de código."""

    def __init__(self, logger: Logger, name: str = "Tarefa", level: str = "INFO") -> None:
        self.logger = logger
        self.name = name
        self.level = level
        self._start = 0.0

    def __enter__(self):
        self._start = time.time()
        getattr(self.logger, self.level.lower())(f"⏱️ Iniciando {self.name} ...")
        return self

    def __exit__(self, exc_type, exc, tb):
        duration = time.time() - self._start
        getattr(self.logger, self.level.lower())(f"⏱️ {self.name} concluída em {duration:.1f}s")


def logger_timer(self: Logger, name: str = "Tarefa", level: str = "INFO") -> Timer:
    """Retorna um ``Timer`` ligado ao logger."""
    return Timer(self, name=name, level=level)

