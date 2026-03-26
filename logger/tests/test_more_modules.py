import logging
from pathlib import Path


from logger import start_logger
from logger.extras import network as network_mod
from logger.extras import monitoring as monitoring_mod
from logger.extras.dependency import DependencyManager
from logger.core.logger_core import _configure_base_logger


def _no_profiler_start(self):
    pass


# ----------------------- Network module tests -----------------------

def test_check_connection_success_and_failure(monkeypatch):
    nm = network_mod.NetworkMonitor()

    t = [0.0]
    monkeypatch.setattr(network_mod.time, "time", lambda: t[0])

    def ok_conn(addr, timeout=1.0):
        t[0] = 0.05
        class Dummy:
            pass
        return Dummy()

    monkeypatch.setattr(network_mod.socket, "create_connection", ok_conn)
    success, lat = nm.check_connection(timeout=1.0)
    assert success is True
    assert abs(lat - 50.0) < 1e-6

    def bad_conn(*args, **kwargs):
        raise OSError

    monkeypatch.setattr(network_mod.socket, "create_connection", bad_conn)
    success, lat = nm.check_connection()
    assert success is False
    assert lat is None


def test_logger_get_network_metrics_average(tmp_path, monkeypatch):
    monkeypatch.setattr('logger.core.context.Profiler.start', _no_profiler_start)
    logger = start_logger("avg", log_dir=str(tmp_path), console_level="CRITICAL")
    nm = network_mod.NetworkMonitor()
    metrics = nm.metrics["site.com"]
    metrics["latencies"] = [10.0, 20.0, 30.0]
    metrics["total_requests"] = 3
    setattr(logger, "_net_monitor", nm)
    data = logger.get_network_metrics("site.com")
    assert data["average_latency"] == 20.0
    assert data["total_requests"] == 3
    logger.end()


def test_setup_dependencies_and_network():
    logger = logging.getLogger("setup_test")
    network_mod._setup_dependencies_and_network(logger)
    assert isinstance(logger._net_monitor, network_mod.NetworkMonitor)
    assert isinstance(logger._dep_manager, DependencyManager)
    assert hasattr(logging.Logger, "check_connectivity")
    assert hasattr(logging.Logger, "get_network_metrics")


# ----------------------- Monitoring module tests --------------------

def test_system_monitor_snapshot_and_diff(monkeypatch):
    sm = monitoring_mod.SystemMonitor()
    monkeypatch.setattr(sm, "get_memory_usage", lambda: (100.0, 40.0))
    monkeypatch.setattr(sm, "_count_objects", lambda: {"A": 1})
    sm.take_memory_snapshot()

    monkeypatch.setattr(sm, "get_memory_usage", lambda: (105.0, 40.0))
    monkeypatch.setattr(sm, "_count_objects", lambda: {"A": 2, "B": 3})
    diff, obj = sm.get_memory_diff()
    assert diff == 5.0
    assert obj == {"A": 1, "B": 3}


def test_system_monitor_diff_without_snapshot(monkeypatch):
    sm = monitoring_mod.SystemMonitor()
    monkeypatch.setattr(sm, "get_memory_usage", lambda: (50.0, 20.0))
    monkeypatch.setattr(sm, "_count_objects", lambda: {"X": 1})
    diff, obj = sm.get_memory_diff()
    assert diff == 0.0
    assert obj == {}


# ----------------------- Logger core tests --------------------------

def _info_fmt(logger: logging.Logger) -> str:
    for h in logger.handlers:
        if isinstance(h, logging.FileHandler) and h.level == logging.INFO:
            return str(h.formatter._fmt)  # type: ignore[attr-defined, union-attr]
    raise AssertionError("info handler not found")


def test_configure_base_logger_formats(tmp_path):
    base = Path(tmp_path)
    logger0 = _configure_base_logger("f0", str(base / "0"), verbose=0)
    fmt0 = _info_fmt(logger0)
    assert "Cadeia de Funcoes" not in fmt0

    logger1 = _configure_base_logger("f1", str(base / "1"), verbose=1)
    fmt1 = _info_fmt(logger1)
    assert "Cadeia de Funcoes" in fmt1 and "{pathname}" not in fmt1

    logger2 = _configure_base_logger("f2", str(base / "2"), verbose=2)
    fmt2 = _info_fmt(logger2)
    assert "{pathname}" in fmt2 and "{thread_disp}" not in fmt2

    logger3 = _configure_base_logger("f3", str(base / "3"), verbose=3)
    fmt3 = _info_fmt(logger3)
    assert "{thread_disp}" in fmt3

    assert hasattr(logging.Logger, "progress")
    assert len(logger0.handlers) == 3
    assert Path(logger0.log_path).is_file()
