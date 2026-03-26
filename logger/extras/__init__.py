"""Extras utilities for the logger package."""

from .dependency import (
    DependencyManager as DependencyManager,
    logger_log_environment as logger_log_environment,
)
from .network import (
    NetworkMonitor as NetworkMonitor,
    logger_check_connectivity as logger_check_connectivity,
    logger_get_network_metrics as logger_get_network_metrics,
    _setup_dependencies_and_network as _setup_dependencies_and_network,
)
from .progress import (
    LoggerProgressBar as LoggerProgressBar,
    logger_progress as logger_progress,
    format_block as format_block,
    combine_blocks as combine_blocks,
)
from .printing import (
    logger_capture_prints as logger_capture_prints,
    capture_prints as capture_prints,
)
from .email_capture import (
    logger_capture_emails as logger_capture_emails,
    capture_emails as capture_emails,
)
from .helpers import (
    _init_colorama as _init_colorama,
    _setup_directories as _setup_directories,
    _get_log_filename as _get_log_filename,
    _attach_screenshot as _attach_screenshot,
)
from .metrics import (
    MetricsTracker as MetricsTracker,
    logger_reset_metrics as logger_reset_metrics,
    logger_report_metrics as logger_report_metrics,
    _setup_metrics as _setup_metrics,
)
from .monitoring import (
    SystemMonitor as SystemMonitor,
    logger_log_system_status as logger_log_system_status,
    logger_memory_snapshot as logger_memory_snapshot,
    logger_check_memory_leak as logger_check_memory_leak,
    _setup_monitoring as _setup_monitoring,
)
from .utils.sleep import logger_sleep as logger_sleep
from .utils.timer import Timer as Timer, logger_timer as logger_timer
from .logger_lifecycle import (
    logger_log_start as logger_log_start,
    logger_log_end as logger_log_end,
    _setup_lifecycle as _setup_lifecycle,
)
from .remote_sink import (
    setup_remote_sink as setup_remote_sink,
)
from .base_funcs import *  # noqa: F401,F403

__all__ = [
    "DependencyManager",
    "logger_log_environment",
    "NetworkMonitor",
    "logger_check_connectivity",
    "logger_get_network_metrics",
    "_setup_dependencies_and_network",
    "LoggerProgressBar",
    "logger_progress",
    "format_block",
    "combine_blocks",
    "logger_capture_prints",
    "capture_prints",
    "logger_capture_emails",
    "capture_emails",
    "_init_colorama",
    "_setup_directories",
    "_get_log_filename",
    "_attach_screenshot",
    "MetricsTracker",
    "logger_reset_metrics",
    "logger_report_metrics",
    "_setup_metrics",
    "SystemMonitor",
    "logger_log_system_status",
    "logger_memory_snapshot",
    "logger_check_memory_leak",
    "_setup_monitoring",
    "logger_sleep",
    "Timer",
    "logger_timer",
    "logger_log_start",
    "logger_log_end",
    "_setup_lifecycle",
    "setup_remote_sink",
]
