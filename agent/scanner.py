"""Scan directories for automation projects (logger_config.json)."""

from __future__ import annotations

import json
import os

_SKIP_DIRS = frozenset({
    ".venv", "venv", "__pycache__", "node_modules", ".git",
    ".tox", ".mypy_cache", ".pytest_cache", "dist", "build",
})


def scan_for_automations(scan_dirs: list[str], max_depth: int = 3) -> list[dict]:
    """Recursively scan *scan_dirs* for folders containing ``logger_config.json``.

    Returns a list of dicts with keys:
      - working_dir: absolute path to the project directory
      - available_args: list of argument descriptors (if present in config)
      - automation_code: code from the start_logger block (if present)
    """
    results: list[dict] = []
    for base_dir in scan_dirs:
        base_dir = os.path.abspath(base_dir)
        if os.path.isdir(base_dir):
            _scan_recursive(base_dir, max_depth, 0, results)
    return results


def _scan_recursive(
    directory: str,
    max_depth: int,
    current_depth: int,
    results: list[dict],
) -> None:
    if current_depth > max_depth:
        return

    try:
        entries = os.listdir(directory)
    except PermissionError:
        return

    if "logger_config.json" in entries:
        config_path = os.path.join(directory, "logger_config.json")
        try:
            with open(config_path, encoding="utf-8") as f:
                config = json.load(f)
        except (json.JSONDecodeError, OSError):
            config = {}

        available_args = config.get("available_args", [])
        # remote_sink can be at root level or nested inside start_logger
        remote_sink = config.get("remote_sink", {})
        if not remote_sink:
            remote_sink = config.get("start_logger", {}).get("remote_sink", {})
        automation = remote_sink.get("automation", {})

        results.append({
            "working_dir": directory,
            "available_args": available_args,
            "automation_code": automation.get("code", ""),
        })

    for entry in entries:
        if entry.startswith(".") or entry in _SKIP_DIRS:
            continue
        full_path = os.path.join(directory, entry)
        if os.path.isdir(full_path):
            _scan_recursive(full_path, max_depth, current_depth + 1, results)
