"""logger_lifecycle.py - Funções de início e término do logger."""

from logging import Logger
import atexit
from pathlib import Path
from datetime import datetime
import os
import sys

from .progress import format_block, combine_blocks

__all__ = ["logger_log_start", "logger_log_end", "_setup_lifecycle"]


def logger_log_start(self: Logger, verbose: int = 1) -> None:
    """Exibe informações de início de execução."""
    folder = Path(os.getcwd()).name
    script = Path(sys.argv[0]).name
    now = datetime.now()
    data = now.strftime("%d/%m/%Y")
    hora = now.strftime("%H:%M:%S")

    lines = [
        "PROCESSO INICIADO",
        f"Data: {data} • Hora: {hora}",
        f"Script: {script} • Pasta: {folder}",
    ]
    banner = format_block("INÍCIO", lines)
    blocks = [banner]

    if verbose >= 1:
        self.reset_metrics()  # type: ignore[attr-defined]
        self._profiler.start()  # type: ignore[attr-defined]
        status = self.log_system_status(return_block=True)  # type: ignore[attr-defined]
        env = self.log_environment(return_block=True)  # type: ignore[attr-defined]
        conn = self.check_connectivity(return_block=True)  # type: ignore[attr-defined]
        blocks.extend([status, env, conn])

    if verbose >= 2:
        self.debug("Registrando snapshot inicial de memória...")
        self.memory_snapshot()  # type: ignore[attr-defined]

    banner_final = combine_blocks(blocks)
    extra = {"plain": True, "_remote_sink_skip": True}
    self.success(f"\n{banner_final}", extra=extra)  # type: ignore[attr-defined]


def logger_log_end(self: Logger, verbose: int = 1) -> None:
    """Exibe informações de encerramento de execução."""
    folder = Path(os.getcwd()).name
    script = Path(sys.argv[0]).name
    now = datetime.now()
    data = now.strftime("%d/%m/%Y")
    hora = now.strftime("%H:%M:%S")

    leak_block: str | None = None
    if verbose >= 2:
        self.report_metrics()  # type: ignore[attr-defined]
        self.debug("Verificando possíveis vazamentos de memória...")
    leak_block = self.check_memory_leak(return_block=True)  # type: ignore[attr-defined]
    profile_summary: str | None = None
    if verbose >= 1:
        self.profile_report()  # type: ignore[attr-defined]
        summary_lines = self._profiler.get_report_lines(3)  # type: ignore[attr-defined]
        if summary_lines:
            profile_summary = format_block("PROFILING", summary_lines[:1])

    blocks: list[str] = []
    if verbose >= 1:
        blocks.append(self.log_system_status(return_block=True))  # type: ignore[attr-defined]
        blocks.append(self.check_connectivity(return_block=True))  # type: ignore[attr-defined]
    if leak_block:
        blocks.append(leak_block)

    if profile_summary:
        blocks.append(profile_summary)

    lines = [
        "PROCESSO FINALIZADO",
        f"Data: {data} • Hora: {hora}",
        f"Script: {script} • Pasta: {folder}",
    ]
    banner = format_block("FIM", lines)
    blocks.insert(0, banner)
    banner_final = combine_blocks(blocks)
    extra = {"plain": True, "_remote_sink_skip": True}
    self.success(f"\n{banner_final}", extra=extra)  # type: ignore[attr-defined]

    setattr(self, "_end_called", True)

    remote_sink = getattr(self, "_remote_sink", None)
    if remote_sink:
        try:
            remote_sink.finalize(status="completed")
        except Exception:  # pragma: no cover - best effort
            self.warning("Falha ao finalizar envio remoto", extra={"plain": True})
        finally:
            setattr(self, "_remote_sink", None)


def _setup_lifecycle(logger: Logger) -> None:
    """Acopla funções de ciclo de vida ao ``Logger``."""
    setattr(Logger, "start", logger_log_start)
    setattr(Logger, "end", logger_log_end)

    # Flag para evitar múltiplas execuções de ``end``
    setattr(logger, "_end_called", False)

    def _auto_end() -> None:
        if not getattr(logger, "_end_called", False):
            try:
                logger.end()  # type: ignore[attr-defined]
            except Exception:
                pass

    atexit.register(_auto_end)
