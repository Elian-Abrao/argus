"""WebSocket client with automatic reconnection."""

from __future__ import annotations

import asyncio
import json
import logging

import websockets
from websockets.exceptions import ConnectionClosed

from .config import AgentConfig
from .executor import Executor
from .scanner import scan_for_automations

logger = logging.getLogger("agent.connection")


class AgentConnection:
    """Persistent WebSocket connection to the Logger API."""

    def __init__(self, config: AgentConfig, host_id: str, executor: Executor) -> None:
        self._config = config
        self._host_id = host_id
        self._executor = executor
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._reconnect_delay = config.reconnect_base_delay
        self._heartbeat_task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    async def run_forever(self) -> None:
        url = f"{self._config.api_ws_url}/agent/ws/{self._host_id}"
        while True:
            try:
                async with websockets.connect(
                    url,
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=10,
                ) as ws:
                    self._ws = ws
                    self._reconnect_delay = self._config.reconnect_base_delay
                    logger.info("Conectado à API: %s", url)
                    await self._on_connected()
                    await self._message_loop(ws)
            except (ConnectionClosed, ConnectionRefusedError, OSError) as exc:
                logger.warning("Conexão perdida: %s", exc)
            except Exception:
                logger.exception("Erro inesperado na conexão")
            finally:
                self._ws = None
                if self._heartbeat_task:
                    self._heartbeat_task.cancel()
                    self._heartbeat_task = None

            logger.info(
                "Reconectando em %.1fs...", self._reconnect_delay
            )
            await asyncio.sleep(self._reconnect_delay)
            self._reconnect_delay = min(
                self._reconnect_delay * 2,
                self._config.reconnect_max_delay,
            )

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def _on_connected(self) -> None:
        # Start heartbeat
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        # Scan and send results
        scan_results = scan_for_automations(
            self._config.scan_dirs,
            max_depth=self._config.scan_depth,
        )
        if scan_results:
            await self._send({
                "type": "scan_result",
                "instances": [
                    {
                        "automation_instance_id": r.get("automation_code", ""),
                        "script": "main.py",
                        "available_args": r.get("available_args", []),
                    }
                    for r in scan_results
                ],
            })

    async def _message_loop(
        self, ws: websockets.WebSocketClientProtocol
    ) -> None:
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("Mensagem inválida recebida: %s", raw[:200])
                continue

            msg_type = msg.get("type")
            if msg_type == "execute":
                await self._handle_execute(msg)
            elif msg_type == "kill":
                await self._handle_kill(msg)
            elif msg_type == "scan_request":
                await self._on_connected()  # re-scan and send
            else:
                logger.debug("Mensagem não reconhecida: %s", msg_type)

    # ------------------------------------------------------------------
    # Command handling
    # ------------------------------------------------------------------

    async def _handle_kill(self, msg: dict) -> None:
        command_id = msg.get("command_id", "")
        if not command_id:
            return
        killed = self._executor.kill(command_id)
        if killed:
            logger.info("Kill enviado para comando %s", command_id)
        else:
            logger.warning("Comando %s nao encontrado para kill (ja terminou?)", command_id)

    async def _handle_execute(self, msg: dict) -> None:
        command_id = msg.get("command_id", "")
        script = msg.get("script", "main.py")
        args = msg.get("args", [])
        working_dir = msg.get("working_dir", ".")
        execution_mode = msg.get("execution_mode", "parallel")

        # Ack immediately
        await self._send({"type": "ack", "command_id": command_id})

        # Execute
        await self._executor.execute(
            command_id=command_id,
            script=script,
            args=args,
            working_dir=working_dir,
            execution_mode=execution_mode,
            on_started=self._on_started,
            on_completed=self._on_completed,
            on_failed=self._on_failed,
            on_cancelled=self._on_cancelled,
        )

    async def _on_started(self, command_id: str, pid: int) -> None:
        await self._send({
            "type": "started",
            "command_id": command_id,
            "pid": pid,
        })

    async def _on_completed(self, command_id: str, exit_code: int) -> None:
        await self._send({
            "type": "completed",
            "command_id": command_id,
            "exit_code": exit_code,
        })

    async def _on_failed(self, command_id: str, error: str) -> None:
        await self._send({
            "type": "failed",
            "command_id": command_id,
            "error": error,
        })

    async def _on_cancelled(self, command_id: str) -> None:
        await self._send({
            "type": "cancelled",
            "command_id": command_id,
        })

    # ------------------------------------------------------------------
    # Heartbeat
    # ------------------------------------------------------------------

    async def _heartbeat_loop(self) -> None:
        while self._ws:
            running = self._executor.get_running_command_ids()
            await self._send({
                "type": "heartbeat",
                "running_commands": running,
            })
            await asyncio.sleep(self._config.heartbeat_interval)

    # ------------------------------------------------------------------
    # Send helper
    # ------------------------------------------------------------------

    async def _send(self, msg: dict) -> None:
        if self._ws:
            try:
                await self._ws.send(json.dumps(msg, default=str))
            except Exception:
                logger.warning("Falha ao enviar mensagem: %s", msg.get("type"))
