from logging import Logger
from typing import Iterable, Any, ContextManager, Callable, Dict
from pathlib import Path

from .extras.progress import LoggerProgressBar
from .extras.utils.timer import Timer

class StructuredLogger(Logger):
    def screen(self, msg: str, *args, webdriver=None, **kwargs) -> None:
        """Registra mensagem e captura de tela se possível."""
        ...

    def cleanup(self) -> None:
        """Limpa o terminal da plataforma atual."""
        ...

    def path(self) -> str | None:
        """Retorna o caminho do arquivo de log, se definido."""
        ...

    def debug_path(self) -> str | None:
        """Retorna o caminho do log de depuração, se disponível."""
        ...

    def pause(self, msg: str = ...) -> str:
        """Exibe mensagem e aguarda entrada do usuário."""
        ...

    def sleep(
        self,
        duration: float,
        unit: str = "s",
        level: str = "DEBUG",
        message: str | None = None,
    ) -> None:
        """Suspende a execução por determinado tempo com registro opcional."""
        ...

    def timer(self, name: str = "Tarefa", level: str = "INFO") -> Timer:
        """Retorna um ``Timer`` ligado ao logger."""
        ...

    def progress(
        self,
        iterable: Iterable[Any] | None = ...,
        total: int | None = ...,
        desc: str = ...,
        leave: bool = ...,
        unit: str = ...,
        log_interval: float = ...,
        log_level: str = ...,
    ) -> LoggerProgressBar | Iterable[Any]: ...

    def capture_prints(self, active: bool = True, level: str = "INFO", prefix: str = ...) -> None: ...
    def capture_emails(
        self,
        active: bool = True,
        *,
        include_body: bool = True,
        max_body_chars: int = 12000,
    ) -> None: ...

    def start(self, verbose: int = 1) -> None:
        """Exibe informações de início de execução."""
        ...

    def end(self, verbose: int = 1) -> None:
        """Exibe informações de encerramento de execução."""
        ...

    def log_environment(self, level: str = "INFO", return_block: bool = False) -> str | None: ...

    def check_connectivity(
        self,
        urls: str | Iterable[str] | None = None,
        level: str = "INFO",
        timeout: float = 1.0,
        return_block: bool = False,
    ) -> str | None: ...

    def get_network_metrics(self, domain: str | None = None) -> Dict[str, Any]: ...

    def log_system_status(self, level: str = "INFO", return_block: bool = False) -> str | None:
        """Loga o status atual de CPU e memória."""
        ...

    def memory_snapshot(self) -> None:
        """Armazena um snapshot de memória para comparação futura."""
        ...

    def check_memory_leak(
        self,
        level: str = "WARNING",
        return_block: bool = False,
        *,
        show_all: bool | None = None,
        watch: Iterable[str] | None = None,
        mem_threshold: float | None = None,

    ) -> str | None:
        """Verifica diferenças de uso de memória indicando possível vazamento."""
        ...

    def reset_metrics(self) -> None:
        """Reseta o temporizador de métricas ligado ao logger."""
        ...

    def report_metrics(self, level: str = "INFO") -> None:
        """Registra o tempo decorrido no nível de log especificado."""
        ...

    def success(self, msg: str, *args, **kwargs) -> None: ...

    def context(self, name: str) -> ContextManager[Any]:
        """Adiciona contexto temporario aos logs."""
        ...

    def profile(self, func: Callable | None = ..., *, name: str | None = ...) -> Any: ...

    def profile_cm(self, name: str | None = ...) -> ContextManager[Any]: ...

    def profile_report(
        self,
        *,
        limit: int = ...,
        level: str = ...,
        return_block: bool = ...,
    ) -> str | None: ...

    # dynamically added attributes
    _screen_dir: Path
    _screen_name: str
    log_path: str
    debug_log_path: str
    _active_pbar: LoggerProgressBar | None
    _context_manager: Any
    _profiler: Any
    _metrics: Any
    _monitor: Any
    _dep_manager: Any
    _net_monitor: Any


def start_logger(
    name: str | None = ...,
    log_dir: str = "Logs",
    console_level: str = "INFO",
    file_level: str = "DEBUG",
    capture_prints: bool = True,
    verbose: int = 0,
    *,
    capture_emails: bool = True,
    email_retention_days: int | None = None,
    show_all_leaks: bool = False,
    watch_objects: Iterable[str] | None = None,
) -> StructuredLogger:
    """Cria e devolve um Logger configurado.

    verbose:
        0 → sem detalhes extras no log INFO;
        1 → só call_chain;
        2 → + pathname:lineno;
        3+ → pathname:lineno + thread_disp (máx).
    """
    ...
