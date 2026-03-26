"""Testes unitários para o pacote ``logger``"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler

import logger.extras.logger_lifecycle as lifecycle_mod
import logger.extras.monitoring as monitoring_mod
from logger import start_logger, start_logger_from_config


def test_start_logger_creates_log_files(tmp_path):
    """Verifica se ``start_logger`` devolve um ``Logger`` configurado."""
    logger = start_logger(
        "Test",
        log_dir=str(tmp_path),
        console_level="CRITICAL",  # evita poluir a saída de testes
    )

    logger.info("hello")
    logger.end()

    assert Path(logger.log_path).is_file()
    assert Path(logger.debug_log_path).is_file()
    assert hasattr(logger, "progress")


def test_progress_bar_usage(tmp_path):
    """Garante o funcionamento da progress bar ao iterar sobre um gerador."""
    logger = start_logger(
        "Progress",
        log_dir=str(tmp_path),
        console_level="CRITICAL",
    )

    gen = logger.progress(range(3), desc="Iter")
    assert hasattr(gen, "__iter__")
    itens = list(gen)
    assert itens == [0, 1, 2]
    assert getattr(logger, "_active_pbar", None) is None

    logger.end()


def test_start_logger_from_config(tmp_path):
    """Permite carregar parâmetros a partir de um JSON externo."""
    config_path = tmp_path / "logger_cfg.json"
    config_data = {
        "name": "JsonLogger",
        "log_dir": str(tmp_path / "logs"),
        "console_level": "CRITICAL",
        "file_level": "DEBUG",
        "capture_prints": False,
        "verbose": 2,
        "show_all_leaks": True,
        "watch_objects": ["SampleObj"],
    }
    config_path.write_text(json.dumps(config_data), encoding="utf-8")

    logger = start_logger_from_config(
        config_path,
        overrides={"console_level": "ERROR"},
    )
    logger.info("config logger ativo")
    logger.end()

    assert Path(logger.log_path).exists()
    assert getattr(logger, "_leak_show_all") is True
    assert "SampleObj" in getattr(logger, "_leak_watch")


def test_cleanup_days_removes_old_logs(tmp_path, caplog):
    base = tmp_path / "logs"
    base.mkdir()
    debug_dir = base / "LogsDEBUG"
    debug_dir.mkdir()

    old_main = base / "old.log"
    old_debug = debug_dir / "old-debug.log"
    old_main.write_text("main", encoding="utf-8")
    old_debug.write_text("debug", encoding="utf-8")

    old_ts = (datetime.now() - timedelta(days=40)).timestamp()
    os.utime(old_main, (old_ts, old_ts))
    os.utime(old_debug, (old_ts, old_ts))

    with caplog.at_level(logging.INFO):
        logger = start_logger(
            "clean",
            log_dir=str(base),
            console_level="INFO",
            cleanup_days=30,
        )
        logger.info("novo log")
        logger.end()

    assert not old_main.exists()
    assert not old_debug.exists()
    assert any(base.glob("*.log"))
    messages = " ".join(rec.message for rec in caplog.records)
    assert "old.log" in messages and "old-debug.log" in messages


def test_server_mode_skips_snapshot_but_runs_start(tmp_path, monkeypatch):
    called = {"start": 0, "snapshot": 0}

    def fake_start(self, verbose: int = 1):
        called["start"] += 1

    def fake_snapshot(self):
        called["snapshot"] += 1

    monkeypatch.setattr(lifecycle_mod, "logger_log_start", fake_start)
    monkeypatch.setattr(monitoring_mod, "logger_memory_snapshot", fake_snapshot)

    logger = start_logger(
        "Srv",
        log_dir=str(tmp_path),
        console_level="CRITICAL",
        server_mode=True,
    )
    logger.end()

    assert called["start"] == 1
    assert called["snapshot"] == 0


def test_rotation_uses_timed_handler(tmp_path):
    logger = start_logger(
        "Rotate",
        log_dir=str(tmp_path),
        console_level="CRITICAL",
        rotation_interval=1,
        rotation_unit="hours",
    )
    timed_handlers = [
        h for h in logger.handlers if isinstance(h, TimedRotatingFileHandler)
    ]
    logger.end()
    assert len(timed_handlers) >= 2
    assert Path(logger.log_path).name.endswith(".log")


def test_remote_sink_sends_logs(monkeypatch, tmp_path):
    calls: list[tuple[str, str, dict]] = []

    class FakeResponse:
        status_code = 202

    class FakeSession:
        def __init__(self):
            self.headers = {}

        def post(self, url, json=None, timeout=5):
            calls.append(("POST", url, json))
            return FakeResponse()

        def patch(self, url, json=None, timeout=5):
            calls.append(("PATCH", url, json))
            return FakeResponse()

    monkeypatch.setattr("logger.extras.remote_sink.requests.Session", FakeSession)

    remote_cfg = {
        "enabled": True,
        "endpoint": "http://api.test",
        "automation": {"code": "Auto", "name": "Auto"},
        "client": {"name": "ClienteDemo"},
        "host": {"environment": "qa"},
        "deployment_tag": "qa-1",
        "batch_size": 1,
        "flush_interval": 0.01,
    }

    logger = start_logger(
        "Remote",
        log_dir=str(tmp_path),
        console_level="CRITICAL",
        remote_sink=remote_cfg,
    )
    logger.info("mensagem remota")
    logger.end()

    entries = [
        entry
        for _, url, payload in calls
        if "/logs/batch" in url
        for entry in payload["entries"]
    ]
    assert entries, "Logs não foram enviados"
    assert any(e["message"] == "mensagem remota" and e["level"] == "INFO" for e in entries)
