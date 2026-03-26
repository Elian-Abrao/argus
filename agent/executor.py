"""Subprocess executor for automation commands."""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import subprocess
import threading
from typing import Callable, Awaitable

from .venv_resolver import resolve_venv_python

logger = logging.getLogger("agent.executor")


class Executor:
    """Manages running automation subprocesses."""

    def __init__(self) -> None:
        self._processes: dict[str, subprocess.Popen] = {}
        self._killed: set[str] = set()
        self._lock = threading.Lock()

    async def execute(
        self,
        command_id: str,
        script: str,
        args: list[str],
        working_dir: str,
        execution_mode: str,
        on_started: Callable[[str, int], Awaitable[None]],
        on_completed: Callable[[str, int], Awaitable[None]],
        on_failed: Callable[[str, str], Awaitable[None]],
        on_cancelled: Callable[[str], Awaitable[None]] | None = None,
    ) -> None:
        """Execute a command as a subprocess.

        For ``sequential`` mode, waits until all running processes finish.
        """
        if execution_mode == "sequential":
            await self._wait_all_finished()

        python = resolve_venv_python(working_dir)
        cmd = [python, script] + args
        logger.info("Executando: %s (cwd=%s)", " ".join(cmd), working_dir)

        try:
            proc = await asyncio.to_thread(
                subprocess.Popen,
                cmd,
                cwd=working_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                start_new_session=True,  # novo grupo de processos para kill em cascata
            )
        except Exception as exc:
            await on_failed(command_id, str(exc))
            return

        with self._lock:
            self._processes[command_id] = proc

        await on_started(command_id, proc.pid)

        # Drena stderr em background para evitar que o buffer do pipe encha
        # (~64KB no Linux) e bloqueie o subprocess em anon_pipe_write.
        stderr_chunks: list[bytes] = []

        def _drain_stderr() -> None:
            try:
                for line in proc.stderr:
                    stderr_chunks.append(line)
            except Exception:
                pass

        drain_thread = threading.Thread(target=_drain_stderr, daemon=True)
        drain_thread.start()

        # Wait for completion in background
        asyncio.create_task(
            self._wait_for_completion(
                command_id, proc, drain_thread, stderr_chunks,
                on_completed, on_failed, on_cancelled or self._noop_cancelled,
            )
        )

    def kill(self, command_id: str) -> bool:
        """Kill the process group for command_id (inclui chromedriver e filhos)."""
        with self._lock:
            proc = self._processes.get(command_id)
            if proc:
                self._killed.add(command_id)
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                except Exception:
                    try:
                        proc.terminate()
                    except Exception:
                        pass
                return True
        return False

    async def _wait_for_completion(
        self,
        command_id: str,
        proc: subprocess.Popen,
        drain_thread: threading.Thread,
        stderr_chunks: list[bytes],
        on_completed: Callable[[str, int], Awaitable[None]],
        on_failed: Callable[[str, str], Awaitable[None]],
        on_cancelled: Callable[[str], Awaitable[None]],
    ) -> None:
        exit_code = await asyncio.to_thread(proc.wait)

        # Aguarda a thread de drenagem terminar (stderr já foi fechado pelo proc.wait)
        await asyncio.to_thread(drain_thread.join, 5.0)

        with self._lock:
            self._processes.pop(command_id, None)
            was_killed = command_id in self._killed
            self._killed.discard(command_id)

        if was_killed:
            await on_cancelled(command_id)
        elif exit_code == 0:
            await on_completed(command_id, exit_code)
        else:
            stderr_output = b"".join(stderr_chunks).decode(errors="replace")[:2000]
            await on_failed(command_id, f"exit_code={exit_code}: {stderr_output}")

    async def _wait_all_finished(self) -> None:
        """Block until all running processes complete."""
        while True:
            with self._lock:
                if not self._processes:
                    return
            await asyncio.sleep(1)

    @staticmethod
    async def _noop_cancelled(command_id: str) -> None:
        pass

    def get_running_command_ids(self) -> list[str]:
        with self._lock:
            return list(self._processes.keys())

    def has_running(self) -> bool:
        with self._lock:
            return bool(self._processes)
