"""logger_core.py - Configuração principal do logger.

Este módulo orquestra a criação do logger estruturado, delegando
funcionalidades específicas para módulos em ``logger.extras``.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timedelta
from logging import Logger, FileHandler
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Iterable, Mapping, Any

from logger.formatters.custom import (
    CustomFormatter,
    AutomaticTracebackLogger,
    _define_custom_levels,
)
from logger.handlers import ProgressStreamHandler, FileOnlyFilter
from logger.core.context import _setup_context_and_profiling
from logger.extras import (
    _init_colorama,
    _setup_directories,
    _get_log_filename,
    logger_sleep,
    logger_timer,
    logger_progress,
    logger_capture_prints,
    logger_capture_emails,
    _setup_metrics,
    _setup_monitoring,
    _setup_dependencies_and_network,
    _setup_lifecycle,
    screen,
    cleanup,
    path,
    debug_path,
    pause,
    setup_remote_sink,
)


_ROTATION_UNITS = {
    "minute": "M",
    "minutes": "M",
    "hour": "H",
    "hours": "H",
    "day": "D",
    "days": "D",
}


# ---------------------------------------------------------------------------
# Logger configuration
# ---------------------------------------------------------------------------

# ----- Função principal -----------------------------------------------------
def start_logger(
    name: str | None = None,
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
    cleanup_days: int | None = None,
    server_mode: bool = False,
    rotation_interval: int | None = None,
    rotation_unit: str = "hours",
    remote_sink: Mapping[str, Any] | None = None,
) -> Logger:
    """
    Cria e devolve um Logger configurado.

    verbose:
        0 → sem detalhes extras no log INFO;
        1 → só call_chain;
        2 → + pathname:lineno;
        3+ → pathname:lineno + thread_disp (máx).

    show_all_leaks:
        Se ``True`` exibe todas as diferenças de objetos na verificação de
        memória. Caso ``False`` (padrão) apenas diferenças relevantes são
        mostradas.

    watch_objects:
        Lista de tipos de objetos para acompanhar sempre na verificação de
        vazamento de memória.

    cleanup_days:
        Remove arquivos ``.log`` mais antigos que ``n`` dias em ``log_dir`` e
        ``LogsDEBUG``.

    server_mode:
        Se ``True``, não executa automaticamente ``logger.start()`` nem o
        snapshot de memória, ideal para serviços que iniciam e permanecem em
        execução indefinida. O ``logger.end`` ainda será emitido quando o
        processo finalizar.

    rotation_interval / rotation_unit:
        Controla a rotação automática dos arquivos de log quando o processo
        permanece ativo. ``rotation_unit`` aceita ``minutes``, ``hours`` ou
        ``days``.

    remote_sink:
        Configuração opcional para envio dos logs via API remota. Consulte
        ``docs/remote_api.md`` para os campos aceitos. Se ``None`` ou
        ``enabled=False`` o recurso não é ativado.

    capture_emails:
        Se ``True`` (padrão), intercepta envios via ``smtplib`` e registra
        metadados dos e-mails no logger.

    email_retention_days:
        Retenção dos registros de e-mail para esta automação quando houver
        ``remote_sink`` ativo. Se ``None``, a API aplica o padrão global.
    """
    logger = _configure_base_logger(
        name,
        log_dir,
        console_level,
        file_level,
        verbose,
        cleanup_days=cleanup_days,
        rotation_interval=rotation_interval,
        rotation_unit=rotation_unit,
    )
    _setup_metrics(logger)
    _setup_monitoring(logger)
    _setup_context_and_profiling(logger)
    _setup_dependencies_and_network(logger)
    _setup_lifecycle(logger)
    _setup_exception_hook(logger)
    setattr(logger, "_leak_show_all", show_all_leaks)
    setattr(logger, "_leak_watch", set(watch_objects or []))
    setattr(logger, "_leak_threshold_mb", 5.0)
    setattr(logger, "_server_mode", server_mode)
    if remote_sink and remote_sink.get("enabled"):
        remote_sink_cfg = dict(remote_sink)
        if email_retention_days is not None and "email_retention_days" not in remote_sink_cfg:
            remote_sink_cfg["email_retention_days"] = int(email_retention_days)
        try:
            setup_remote_sink(logger, remote_sink_cfg)
        except Exception:  # pragma: no cover - melhor esforço
            logger.warning(
                "Falha ao iniciar remote_sink",
                extra={"plain": True, "file_only": True},
            )
    if capture_prints:
        logger.capture_prints(True)  # type: ignore[attr-defined]
    if capture_emails:
        logger.capture_emails(True)  # type: ignore[attr-defined]
    if not server_mode:
        logger.memory_snapshot()  # type: ignore[attr-defined]
    else:
        logger.debug(
            "Modo servidor ativo: snapshot inicial ignorado.",
            extra={"plain": True, "file_only": True},
        )
    logger.start()  # type: ignore[attr-defined]
    return logger


# ----------------------- _configure_base_logger -----------------------------
def _configure_base_logger(
    name: str | None,
    log_dir: str,
    console_level: str = "INFO",
    file_level: str = "DEBUG",
    verbose: int = 0,
    *,
    cleanup_days: int | None = None,
    rotation_interval: int | None = None,
    rotation_unit: str = "hours",
) -> Logger:
    """
    Monta toda a estrutura de logging (cores, arquivos, níveis).

    Retorna:
        Logger já configurado com handlers de console e arquivo.
    """
    # 🎨 Cores & níveis customizados
    _init_colorama()
    _define_custom_levels()

    console_level_value = getattr(logging, console_level)
    file_level_value    = getattr(logging, file_level)

    # 📂 Diretórios
    base = Path(log_dir)
    screen_dir, debug_dir = _setup_directories(base)
    removed_logs: list[Path] = []
    if cleanup_days and cleanup_days > 0:
        removed_logs = _cleanup_old_logs(base, debug_dir, cleanup_days)

    rotation_enabled = (
        rotation_interval is not None and rotation_interval > 0
    )
    rotation_code: str | None = None
    if rotation_enabled:
        unit_key = rotation_unit.lower()
        rotation_code = _ROTATION_UNITS.get(unit_key)
        if rotation_code is None:
            allowed = ", ".join(sorted({k for k in _ROTATION_UNITS}))
            raise ValueError(
                f"rotation_unit inválida: '{rotation_unit}'. Opções: {allowed}"
            )

    filename = _get_log_filename(name, use_timestamp=not rotation_enabled)

    # 🪄 Subclasse que adiciona traceback automático
    logging.setLoggerClass(AutomaticTracebackLogger)
    logger = logging.getLogger(name)
    logger.setLevel(min(console_level_value, file_level_value))
    logger.handlers.clear()

    # --------------------- FORMATAÇÃO ---------------------------------------
    datefmt = "%Y-%m-%d %H:%M:%S"
    console_fmt = (
        "{asctime} {emoji} {levelname_color}{levelpad}- {message} {thread_disp}"
    )

    # Função helper que devolve o formato conforme verbose
    def _select_file_fmt(level: int) -> str:
        base_fmt   = "{asctime} {emoji} {levelname}{levelpad}- {message}"
        chain      = " [Cadeia de Funcoes: {call_chain}📍]"
        path_line  = " [{pathname}:{lineno}] -"
        thread     = " {thread_disp}"
        if level <= 0:
            return base_fmt
        elif level == 1:
            return f"{base_fmt} <>{chain}"
        elif level == 2:
            return f"{base_fmt} <>{path_line}{chain}"
        else:  # 3 ou mais
            return f"{base_fmt} <>{path_line}{chain}{thread}"

    file_fmt_info  = _select_file_fmt(verbose)   # ← para handler INFO
    file_fmt_debug = _select_file_fmt(3)         # ← verbosidade máxima

    # --------------------- HANDLERS -----------------------------------------
    # Console
    ch = ProgressStreamHandler()
    ch.setLevel(console_level_value)
    ch.setFormatter(CustomFormatter(fmt=console_fmt, datefmt=datefmt, style="{"))
    ch.addFilter(FileOnlyFilter())
    logger.addHandler(ch)

    # Arquivo DEBUG – sempre no formato máximo
    formatter_dbg = CustomFormatter(
        fmt=file_fmt_debug, datefmt=datefmt, style="{", use_color=False
    )
    def _make_file_handler(target: Path, level: int, formatter: CustomFormatter):
        if rotation_code:
            handler = TimedRotatingFileHandler(
                target,
                when=rotation_code,
                interval=rotation_interval or 1,
                backupCount=0,
                encoding="utf-8",
            )
            handler.suffix = "%Y-%m-%d_%H-%M-%S"
            handler.namer = _build_rotation_namer(target)
        else:
            handler = FileHandler(target, encoding="utf-8")
        handler.setLevel(level)
        handler.setFormatter(formatter)
        return handler

    fh_dbg = _make_file_handler(debug_dir / filename, logging.DEBUG, formatter_dbg)
    logger.addHandler(fh_dbg)

    # Arquivo INFO – formato depende de verbose
    formatter_info = CustomFormatter(
        fmt=file_fmt_info, datefmt=datefmt, style="{", use_color=False
    )
    fh_info = _make_file_handler(base / filename, logging.INFO, formatter_info)
    logger.addHandler(fh_info)

    # --------------------- METADADOS & AZÚCAR -------------------------------
    setattr(logger, "_screen_dir", screen_dir)
    setattr(logger, "_screen_name", name or "log")
    setattr(logger, "log_path",   str(base / filename))
    setattr(logger, "debug_log_path", str(debug_dir / filename))

    # Métodos utilitários
    setattr(Logger, "screen",          screen)
    setattr(Logger, "cleanup",         cleanup)
    setattr(Logger, "path",            path)
    setattr(Logger, "debug_path",      debug_path)
    setattr(Logger, "pause",           pause)
    setattr(Logger, "sleep",           logger_sleep)
    setattr(Logger, "timer",           logger_timer)
    setattr(Logger, "progress",        logger_progress)
    if removed_logs:
        removed_str = ", ".join(str(path.name) for path in removed_logs)
        logger.info(
            "Arquivos de log antigos removidos (%s dias): %s",
            cleanup_days,
            removed_str,
        )

    setattr(Logger, "capture_prints",  logger_capture_prints)
    setattr(Logger, "capture_emails",  logger_capture_emails)

    return logger


def _cleanup_old_logs(base_dir: Path, debug_dir: Path, days: int) -> list[Path]:
    """Remove arquivos .log mais antigos que ``days`` dias."""
    cutoff = datetime.now() - timedelta(days=days)
    removed: list[Path] = []

    def _purge(directory: Path) -> None:
        if not directory.exists():
            return
        for file_path in directory.glob("*.log"):
            try:
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            except OSError:
                continue
            if mtime < cutoff:
                try:
                    file_path.unlink()
                    removed.append(file_path)
                except OSError:
                    continue

    _purge(base_dir)
    _purge(debug_dir)
    return removed


def _build_rotation_namer(base_file: Path):
    """Cria funÇõÇœ ``namer`` que move o timestamp para antes da extensÇõÇœ."""
    stem = base_file.stem
    parent = base_file.parent
    suffix = base_file.suffix or ".log"
    base_name = base_file.name

    def _namer(default_name: str) -> str:
        default_path = Path(default_name)
        rotated = default_path.name
        prefix = f"{base_name}."
        if rotated.startswith(prefix):
            timestamp = rotated[len(prefix):]
        else:
            timestamp = rotated
        try:
            dt = datetime.strptime(timestamp, "%Y-%m-%d_%H-%M-%S")
            formatted = dt.strftime("%d-%m-%Y %H-%M-%S")
        except ValueError:
            formatted = timestamp.replace("_", " ")
        new_name = f"{stem} - {formatted}{suffix}"
        return str(parent / new_name)

    return _namer


def _setup_exception_hook(logger: Logger) -> None:
    """Registra excepthook global para registrar falhas não tratadas."""
    if getattr(logger, "_excepthook_installed", False):
        return
    original_hook = sys.excepthook

    def _handle_exception(exc_type, exc_value, exc_tb):
        try:
            logger.critical(
                "Exceção não tratada",
                exc_info=(exc_type, exc_value, exc_tb),
            )
        except Exception:
            pass
        if original_hook and original_hook is not _handle_exception:
            original_hook(exc_type, exc_value, exc_tb)

    sys.excepthook = _handle_exception
    setattr(logger, "_excepthook_installed", True)


# ----------------------- External configuration ----------------------------
_CONFIG_KEYS = {
    "name",
    "log_dir",
    "console_level",
    "file_level",
    "capture_prints",
    "capture_emails",
    "email_retention_days",
    "verbose",
    "show_all_leaks",
    "watch_objects",
    "cleanup_days",
    "server_mode",
    "rotation_interval",
    "rotation_unit",
    "remote_sink",
}


def _load_config_payload(
    config: str | Path | Mapping[str, Any],
) -> dict[str, Any]:
    """Normaliza dados de configuração lidos de JSON ou dict."""
    if isinstance(config, (str, Path)):
        path = Path(config)
        data: Any = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = dict(config)
    if not isinstance(data, dict):
        raise ValueError("O arquivo de configuração precisa conter um objeto JSON.")
    if "start_logger" in data and isinstance(data["start_logger"], dict):
        data = data["start_logger"]
    unknown = set(data) - _CONFIG_KEYS
    if unknown:
        extras = ", ".join(sorted(unknown))
        raise ValueError(f"Parâmetros desconhecidos em configuração externa: {extras}")
    return {key: data[key] for key in data if key in _CONFIG_KEYS}


def start_logger_from_config(
    config: str | Path | Mapping[str, Any],
    *,
    overrides: Mapping[str, Any] | None = None,
) -> Logger:
    """Instancia um logger usando um arquivo JSON com parÇ½metros."""
    settings = _load_config_payload(config)
    if overrides:
        override_data = {
            key: overrides[key]
            for key in overrides
            if key in _CONFIG_KEYS
        }
        settings.update(override_data)
    name = settings.pop("name", None)
    remote_sink = settings.pop("remote_sink", None)
    return start_logger(name=name, remote_sink=remote_sink, **settings)
