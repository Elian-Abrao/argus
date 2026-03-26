"""Routes for command management (run-now, listing)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from .. import crud, models
from ..ws_manager import manager
from ..auth.dependencies import get_current_user, get_accessible_automation_ids, require_permission, PERM_RUN_AUTOMATIONS
from ..schemas import (
    RunNowRequest,
    CommandSummary,
    CommandListResponse,
    AgentStatusItem,
)

router = APIRouter()


@router.post("/commands/run-now", response_model=CommandSummary, status_code=201, tags=["commands"])
async def run_now(
    *,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission(PERM_RUN_AUTOMATIONS)),
    payload: RunNowRequest,
):
    # Resolve automation instance to get host + working_dir
    instance = db.get(models.AutomationInstance, payload.automation_instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Instância de automação não encontrada")

    host = instance.host
    if not host:
        raise HTTPException(status_code=400, detail="Instância sem host associado")

    working_dir = host.root_folder

    cmd = crud.create_command(
        db,
        host_id=host.id,
        automation_instance_id=instance.id,
        script=payload.script,
        args=payload.args,
        working_dir=working_dir,
        execution_mode=payload.execution_mode,
        created_by=current_user.email,
    )

    # Push to agent if connected
    from .agent_ws import _serialize_command

    sent = await manager.send_command(host.id, _serialize_command(cmd))
    if not sent:
        pass  # Command stays pending, agent will pick it up on reconnect

    return crud._build_command_summary(cmd)


@router.get("/commands", response_model=CommandListResponse, tags=["commands"])
def list_commands_route(
    *,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
    accessible_automation_ids: list = Depends(get_accessible_automation_ids),
    host_id: Optional[UUID] = Query(None),
    automation_instance_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    created_after: Optional[datetime] = Query(None),
    created_before: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    total, items = crud.list_commands(
        db,
        host_id=host_id,
        automation_instance_id=automation_instance_id,
        status=status,
        created_after=created_after,
        created_before=created_before,
        limit=limit,
        offset=offset,
        allowed_automation_ids=accessible_automation_ids,
    )
    return {"total": total, "limit": limit, "offset": offset, "items": items}


@router.post("/commands/{command_id}/cancel", response_model=CommandSummary, tags=["commands"])
async def cancel_command(
    command_id: UUID,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_permission(PERM_RUN_AUTOMATIONS)),
):
    """Send a kill signal to the agent running this command."""
    cmd = crud.get_command(db, command_id)
    if not cmd:
        raise HTTPException(status_code=404, detail="Comando não encontrado")
    if cmd.status not in ("acked", "running"):
        raise HTTPException(status_code=409, detail=f"Comando não pode ser cancelado no status '{cmd.status}'")

    sent = await manager.send_command(cmd.host_id, {"type": "kill", "command_id": str(command_id)})
    if not sent:
        raise HTTPException(status_code=503, detail="Agente não está conectado")

    return crud._build_command_summary(cmd)


@router.get("/commands/{command_id}", response_model=CommandSummary, tags=["commands"])
def get_command_route(
    command_id: UUID,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
):
    cmd = crud.get_command(db, command_id)
    if not cmd:
        raise HTTPException(status_code=404, detail="Comando não encontrado")
    return crud._build_command_summary(cmd)


@router.get("/agent/identify", tags=["agent"])
def agent_identify(
    *,
    db: Session = Depends(get_db),
    hostname: Optional[str] = Query(None),
    ip_address: Optional[str] = Query(None),
):
    """Resolve a host by hostname or IP address, returning its UUID.

    The agent calls this at startup to auto-discover its host_id.
    """
    from sqlalchemy import select, func, or_

    if not hostname and not ip_address:
        raise HTTPException(status_code=422, detail="Informe hostname ou ip_address")

    conditions = []
    if hostname:
        conditions.append(func.lower(models.Host.hostname) == hostname.lower())
    if ip_address:
        conditions.append(models.Host.ip_address == ip_address)

    stmt = select(models.Host).where(or_(*conditions)).order_by(models.Host.created_at)
    host = db.execute(stmt).scalars().first()
    if not host:
        raise HTTPException(status_code=404, detail="Host não encontrado no sistema")

    return {
        "host_id": str(host.id),
        "hostname": host.hostname,
        "ip_address": str(host.ip_address) if host.ip_address else None,
    }


@router.get("/agent/status", tags=["agent"])
def get_agent_status(db: Session = Depends(get_db)):
    """Return connectivity status for all hosts."""
    from sqlalchemy import select

    connected_ids = set(manager.get_connected_hosts())
    hosts = db.execute(select(models.Host)).scalars().all()

    items = []
    for host in hosts:
        items.append(
            AgentStatusItem(
                host_id=host.id,
                hostname=host.hostname,
                connected=host.id in connected_ids,
                last_ping=host.last_agent_ping,
            ).model_dump()
        )
    return {"items": items}
