"""Agent configuration loading."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AgentConfig:
    api_url: str  # HTTP base, e.g. "http://localhost:8100/api"
    scan_dirs: list[str] = field(default_factory=list)
    scan_depth: int = 3
    heartbeat_interval: int = 30
    reconnect_base_delay: float = 1.0
    reconnect_max_delay: float = 60.0

    @property
    def api_ws_url(self) -> str:
        """Derive WebSocket URL from HTTP URL."""
        url = self.api_url.rstrip("/")
        if url.startswith("https://"):
            return "wss://" + url[len("https://"):]
        if url.startswith("http://"):
            return "ws://" + url[len("http://"):]
        return url


def _discover_sibling_dirs() -> list[str]:
    """Return all sibling directories of the agent folder, excluding agent itself."""
    agent_dir = Path(__file__).resolve().parent
    parent = agent_dir.parent
    siblings = []
    for entry in sorted(parent.iterdir()):
        if entry.is_dir() and entry != agent_dir and not entry.name.startswith("."):
            siblings.append(str(entry))
    return siblings


def load_config() -> AgentConfig:
    """Load config from agent_config.json or environment variables.

    The only required field is ``api_url`` — the HTTP endpoint of the
    Logger API (same ``endpoint`` used in ``logger_config.json``).
    Scan directories default to all sibling folders of the agent directory.
    """
    config_path = Path(__file__).resolve().parent / "agent_config.json"
    if not config_path.exists():
        config_path = Path.cwd() / "agent_config.json"

    if config_path.exists():
        with open(config_path) as f:
            data = json.load(f)

        api_url = data.get("api_url", "")
        if not api_url:
            print(
                "Erro: agent_config.json deve conter 'api_url'.",
                file=sys.stderr,
            )
            sys.exit(1)

        return AgentConfig(
            api_url=api_url,
            scan_dirs=data.get("scan_dirs") or _discover_sibling_dirs(),
            scan_depth=data.get("scan_depth", 3),
            heartbeat_interval=data.get("heartbeat_interval", 30),
            reconnect_base_delay=data.get("reconnect_base_delay", 1.0),
            reconnect_max_delay=data.get("reconnect_max_delay", 60.0),
        )

    # Fallback to env vars
    api_url = os.environ.get("AGENT_API_URL")
    if not api_url:
        print(
            "Erro: forneça agent_config.json com 'api_url' ou variável AGENT_API_URL",
            file=sys.stderr,
        )
        sys.exit(1)

    scan_dirs_env = os.environ.get("AGENT_SCAN_DIRS")
    return AgentConfig(
        api_url=api_url,
        scan_depth=int(os.environ.get("AGENT_SCAN_DEPTH", "3")),
        heartbeat_interval=int(os.environ.get("AGENT_HEARTBEAT_INTERVAL", "30")),
        scan_dirs=scan_dirs_env.split(os.pathsep) if scan_dirs_env else _discover_sibling_dirs(),
    )
