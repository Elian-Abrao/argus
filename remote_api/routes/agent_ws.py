"""WebSocket endpoint for VM agents."""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db, session_scope
from ..ws_manager import manager
from .. import crud

logger = logging.getLogger("remote_api.agent_ws")

router = APIRouter()


def _serialize_command(cmd) -> dict:
    """Build the execute message payload from a Command model."""
    return {
        "type": "execute",
        "command_id": str(cmd.id),
        "script": cmd.script,
        "args": cmd.args or [],
        "working_dir": cmd.working_dir,
        "execution_mode": cmd.execution_mode,
    }


async def _send_pending_commands(host_id: UUID) -> None:
    """Send all pending commands to the agent upon connection."""
    with session_scope() as session:
        pending = crud.get_pending_commands_for_host(session, host_id)
        for cmd in pending:
            payload = _serialize_command(cmd)
            await manager.send_command(host_id, payload)


async def _handle_agent_message(host_id: UUID, data: dict) -> None:
    """Dispatch an incoming message from the agent."""
    msg_type = data.get("type")

    if msg_type == "heartbeat":
        await asyncio.to_thread(_on_heartbeat, host_id, data)

    elif msg_type == "ack":
        command_id = data.get("command_id")
        if command_id:
            await asyncio.to_thread(_on_ack, UUID(command_id))

    elif msg_type == "started":
        command_id = data.get("command_id")
        run_id = data.get("run_id")
        if command_id:
            await asyncio.to_thread(
                _on_started,
                UUID(command_id),
                UUID(run_id) if run_id else None,
            )

    elif msg_type == "completed":
        command_id = data.get("command_id")
        if command_id:
            await asyncio.to_thread(
                _on_completed,
                UUID(command_id),
                data.get("exit_code", 0),
            )

    elif msg_type == "failed":
        command_id = data.get("command_id")
        if command_id:
            await asyncio.to_thread(
                _on_failed,
                UUID(command_id),
                data.get("error", ""),
            )

    elif msg_type == "cancelled":
        command_id = data.get("command_id")
        if command_id:
            await asyncio.to_thread(_on_cancelled, UUID(command_id))

    elif msg_type == "scan_result":
        instances = data.get("instances", [])
        await asyncio.to_thread(_on_scan_result, host_id, instances)

    else:
        logger.warning("Mensagem desconhecida do agente %s: %s", host_id, msg_type)


def _on_heartbeat(host_id: UUID, data: dict) -> None:
    with session_scope() as session:
        crud.update_host_agent_ping(session, host_id)


def _on_ack(command_id: UUID) -> None:
    with session_scope() as session:
        crud.update_command_status(session, command_id, status="acked")


def _on_started(command_id: UUID, run_id: UUID | None) -> None:
    with session_scope() as session:
        crud.update_command_status(session, command_id, status="running", run_id=run_id)


def _on_completed(command_id: UUID, exit_code: int) -> None:
    with session_scope() as session:
        status = "completed" if exit_code == 0 else "failed"
        cmd = crud.update_command_status(
            session,
            command_id,
            status=status,
            result_message=f"exit_code={exit_code}",
        )
        if cmd:
            _close_orphan_run(session, cmd, run_status="stopped")


def _on_failed(command_id: UUID, error: str) -> None:
    with session_scope() as session:
        cmd = crud.update_command_status(
            session,
            command_id,
            status="failed",
            result_message=error[:2000],
        )
        if cmd:
            _close_orphan_run(session, cmd, run_status="stopped")


def _on_cancelled(command_id: UUID) -> None:
    with session_scope() as session:
        cmd = crud.update_command_status(
            session,
            command_id,
            status="cancelled",
            result_message="Cancelado pelo usuario",
        )
        if cmd:
            _close_orphan_run(session, cmd, run_status="stopped")


def _close_orphan_run(session, cmd, run_status: str = "stopped") -> None:
    """Fecha a run aberta mais recente da mesma instância criada após o comando.

    Como o agente não conhece o run_id (a lib cria a run de forma independente),
    inferimos qual run fechar pela automation_instance_id e pelo tempo:
    buscamos a run mais recente com finished_at NULL que iniciou depois que
    o comando foi criado.
    """
    from datetime import datetime, timezone
    from sqlalchemy import select
    from .. import models

    if not cmd.automation_instance_id or not cmd.created_at:
        return

    run = session.execute(
        select(models.Run)
        .where(
            models.Run.automation_instance_id == cmd.automation_instance_id,
            models.Run.finished_at.is_(None),
            models.Run.started_at >= cmd.created_at,
        )
        .order_by(models.Run.started_at.desc())
        .limit(1)
    ).scalars().first()

    if run:
        run.finished_at = datetime.now(timezone.utc)
        run.status = run_status
        session.flush()
        logger.info(
            "Run %s fechada automaticamente como '%s' (processo encerrado pelo agente, command=%s)",
            run.id, run_status, cmd.id,
        )


def _on_scan_result(host_id: UUID, instances: list[dict]) -> None:
    from sqlalchemy import select
    from .. import models

    with session_scope() as session:
        for item in instances:
            automation_code = item.get("automation_instance_id")
            if not automation_code:
                continue

            # Resolve automation by code
            automation = session.execute(
                select(models.Automation).where(models.Automation.code == automation_code)
            ).scalars().first()
            if not automation:
                logger.debug("Automacao nao encontrada para code=%s", automation_code)
                continue

            # Find the instance for this automation on this host
            instance = session.execute(
                select(models.AutomationInstance).where(
                    models.AutomationInstance.automation_id == automation.id,
                    models.AutomationInstance.host_id == host_id,
                )
            ).scalars().first()
            if not instance:
                logger.debug("Instancia nao encontrada para automation=%s host=%s", automation_code, host_id)
                continue

            # Só sobrescreve available_args se o agente encontrou algo no logger_config.json.
            # Lista vazia = config sem available_args → preserva o cadastro manual.
            agent_args = item.get("available_args") or None
            crud.update_instance_args(
                session,
                instance.id,
                available_args=agent_args,
            )


@router.websocket("/agent/ws/{host_id}")
async def agent_websocket(websocket: WebSocket, host_id: UUID):
    await websocket.accept()
    await manager.connect(host_id, websocket)

    # Update host ping and send pending commands
    await asyncio.to_thread(_on_heartbeat, host_id, {})
    await _send_pending_commands(host_id)

    try:
        while True:
            data = await websocket.receive_json()
            await _handle_agent_message(host_id, data)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Erro no WebSocket do agente %s", host_id)
    finally:
        manager.disconnect(host_id)
