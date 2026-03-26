from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from urllib import error, request

from ..config import get_bridge_settings


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BROKER_LOG_PATH = PROJECT_ROOT / ".codex-bridge.log"


def _healthcheck(url: str, timeout: float = 1.5) -> bool:
    try:
        with request.urlopen(f"{url.rstrip('/')}/v1/health", timeout=timeout) as response:
            return response.status == 200
    except (error.URLError, TimeoutError):
        return False


def ensure_broker_running(wait_seconds: float = 8.0) -> bool:
    settings = get_bridge_settings()
    if _healthcheck(settings.url):
        return False

    with BROKER_LOG_PATH.open("ab") as log_file:
        subprocess.Popen(
            [sys.executable, "-m", "codex_bridge", "serve"],
            cwd=str(PROJECT_ROOT),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env=os.environ.copy(),
        )

    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        if _healthcheck(settings.url):
            return True
        time.sleep(0.25)

    raise RuntimeError(
        "Failed to start codex-bridge automatically. "
        f"Check the broker log at {BROKER_LOG_PATH}."
    )


__all__ = ["BROKER_LOG_PATH", "ensure_broker_running"]
