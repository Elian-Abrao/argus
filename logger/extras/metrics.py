"""metrics.py - Suporte a métricas de execução do logger.

Este módulo provê a classe ``MetricsTracker`` para medir duração total de
execução e funções utilitárias vinculadas ao ``Logger``.
"""

from logging import Logger
import time


class MetricsTracker:
    """Tracker simples de tempo de execução."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        """Reinicia o contador de tempo."""
        self._start_time = time.time()

    def report(self) -> float:
        """Retorna o tempo decorrido desde o último ``reset``."""
        return time.time() - self._start_time


def logger_reset_metrics(self: Logger) -> None:
    """Reseta o temporizador de métricas ligado ao logger."""
    self._metrics.reset()  # type: ignore[attr-defined]


def logger_report_metrics(self: Logger, level: str = "INFO") -> None:
    """Registra o tempo decorrido no nível de log especificado."""
    duration = self._metrics.report()  # type: ignore[attr-defined]
    msg = f"⏱️ Duração total: {duration:.1f}s"
    getattr(self, level.lower())(msg)


def _setup_metrics(logger: Logger) -> None:
    """Liga o ``MetricsTracker`` à instância do logger."""
    metrics = MetricsTracker()
    setattr(logger, "_metrics", metrics)
    setattr(Logger, "reset_metrics", logger_reset_metrics)
    setattr(Logger, "report_metrics", logger_report_metrics)
