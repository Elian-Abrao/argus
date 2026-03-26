"""In-memory WebSocket connection manager for remote agents."""

from __future__ import annotations

import json
import logging
from uuid import UUID

from fastapi import WebSocket

logger = logging.getLogger("remote_api.ws_manager")


class ConnectionManager:
    """Tracks active WebSocket connections by host_id (one per VM)."""

    def __init__(self) -> None:
        self._connections: dict[UUID, WebSocket] = {}

    async def connect(self, host_id: UUID, ws: WebSocket) -> None:
        old = self._connections.get(host_id)
        if old is not None:
            try:
                await old.close(code=1012, reason="nova conexão do mesmo host")
            except Exception:
                pass
        self._connections[host_id] = ws
        logger.info("Agente conectado: host_id=%s", host_id)

    def disconnect(self, host_id: UUID) -> None:
        self._connections.pop(host_id, None)
        logger.info("Agente desconectado: host_id=%s", host_id)

    def is_connected(self, host_id: UUID) -> bool:
        return host_id in self._connections

    async def send_command(self, host_id: UUID, command: dict) -> bool:
        ws = self._connections.get(host_id)
        if ws is None:
            return False
        try:
            await ws.send_json(command)
            return True
        except Exception:
            logger.warning("Falha ao enviar comando para host_id=%s", host_id)
            self.disconnect(host_id)
            return False

    def get_connected_hosts(self) -> list[UUID]:
        return list(self._connections.keys())


manager = ConnectionManager()
