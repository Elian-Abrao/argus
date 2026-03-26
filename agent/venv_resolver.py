"""Resolve the Python executable from the nearest .venv."""

from __future__ import annotations

import os
import sys


def resolve_venv_python(working_dir: str, root_limit: str | None = None) -> str:
    """Walk upward from *working_dir* looking for a ``.venv`` directory.

    Returns the path to the Python executable inside the first ``.venv``
    found, or falls back to the system Python.  If *root_limit* is given,
    stop searching at that directory (inclusive).
    """
    is_windows = sys.platform == "win32"
    current = os.path.abspath(working_dir)

    while True:
        venv_dir = os.path.join(current, ".venv")
        if os.path.isdir(venv_dir):
            if is_windows:
                python = os.path.join(venv_dir, "Scripts", "python.exe")
            else:
                python = os.path.join(venv_dir, "bin", "python")
            if os.path.isfile(python):
                return python

        if root_limit and os.path.abspath(current) == os.path.abspath(root_limit):
            break

        parent = os.path.dirname(current)
        if parent == current:  # filesystem root
            break
        current = parent

    return "python" if is_windows else "python3"
