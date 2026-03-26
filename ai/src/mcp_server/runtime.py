from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from urllib import error, request
from urllib.parse import urlparse

from ..config import get_dbhub_settings


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DBHUB_LOG_PATH = PROJECT_ROOT / ".dbhub.log"


def _healthcheck(url: str, timeout: float = 1.5) -> bool:
    try:
        with request.urlopen(url, timeout=timeout) as response:
            return response.status == 200
    except (error.URLError, TimeoutError):
        return False


def _healthcheck_url(mcp_url: str) -> str:
    parsed = urlparse(mcp_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    return f"{base}/healthz"


def ensure_dbhub_running(wait_seconds: float = 12.0) -> bool:
    settings = get_dbhub_settings()
    health_url = _healthcheck_url(settings.url)

    if _healthcheck(health_url):
        return False

    with DBHUB_LOG_PATH.open("ab") as log_file:
        subprocess.Popen(
            ["./scripts/start_dbhub.sh"],
            cwd=str(PROJECT_ROOT),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env=os.environ.copy(),
        )

    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        if _healthcheck(health_url):
            return True
        time.sleep(0.25)

    raise RuntimeError(f"Failed to start DBHub automatically. Check the log at {DBHUB_LOG_PATH}.")


__all__ = ["DBHUB_LOG_PATH", "ensure_dbhub_running"]
