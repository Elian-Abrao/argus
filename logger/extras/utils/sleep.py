"""sleep.py - Função utilitária de espera para o logger."""

from logging import Logger
import time

__all__ = ["logger_sleep"]


def logger_sleep(self: Logger, duration: float, unit: str = "s", level: str = "DEBUG", message: str | None = None) -> None:
    """Suspende a execução por determinado tempo com registro opcional.

    Parameters
    ----------
    duration : float
        Quantidade de tempo.
    unit : str, default "s"
        Unidade de medida: ``"s"`` segundos, ``"ms"`` milissegundos,
        ``"min"`` minutos ou ``"h"`` horas.
    level : str, default "DEBUG"
        Nível de log utilizado para a mensagem.
    message : str, opcional
        Mensagem customizada para exibição.
    """
    units = {"s": 1, "ms": 0.001, "min": 60, "h": 3600}
    seconds = duration * units.get(unit, 1)
    unit_name = {"s": "segundo(s)", "ms": "milissegundo(s)", "min": "minuto(s)", "h": "hora(s)"}.get(unit, "segundo(s)")
    msg = message or f"Aguardando {duration} {unit_name}"
    getattr(self, level.lower())(f"⏳ {msg}")
    time.sleep(seconds)
