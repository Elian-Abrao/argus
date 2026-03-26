"""Read-only endpoints to power dashboards and front-end experiences."""

from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from minio.error import S3Error

from .. import crud
from ..database import get_db
from ..storage import storage
from ..auth.dependencies import (
    get_current_user,
    get_accessible_automation_ids,
    require_permission,
    PERM_CONFIGURE_ARGS,
)
from .. import models
from ..schemas import (
    AutomationInstanceSummary,
    AutomationListResponse,
    AutomationSummary,
    ClientAutomationSummary,
    ClientListResponse,
    ClientSummary,
    HostAutomationSummary,
    HostListResponse,
    HostSummary,
    HostUpdateRequest,
    InstanceArgsUpdate,
    LogEntriesResponse,
    RunDetailResponse,
    RunListResponse,
    RunOverviewResponse,
    RunTimelineResponse,
    LogMetricsResponse,
    EmailAttachmentSummary,
    EmailEventListResponse,
    EmailEventSummary,
)


router = APIRouter()


def _check_host_access(host_id: UUID, accessible_automation_ids: list[UUID] | None, db: Session | None = None) -> None:
    """Raise 403 if the user does not have access to the given host via their allowed automations."""
    if accessible_automation_ids is None:
        return
    if not accessible_automation_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado a este host")
    if db is not None:
        from sqlalchemy import select as sa_select
        has = db.execute(
            sa_select(models.AutomationInstance.id)
            .where(
                models.AutomationInstance.host_id == host_id,
                models.AutomationInstance.automation_id.in_(accessible_automation_ids),
            )
            .limit(1)
        ).first()
        if not has:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado a este host")


@router.get("/hosts", response_model=HostListResponse, tags=["insights"])
def list_hosts(
    *,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
    accessible_automation_ids: list[UUID] | None = Depends(get_accessible_automation_ids),
    environment: str | None = Query(None, description="Filtra por ambiente da máquina"),
    hostname: str | None = Query(None, description="Filtra por hostname"),
    ip_address: str | None = Query(None, description="Filtra por IP"),
    search: str | None = Query(
        None, description="Busca por hostname, caminho raiz ou IP"
    ),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    total, items = crud.list_hosts(
        db,
        environment=environment,
        hostname=hostname,
        ip_address=ip_address,
        search=search,
        limit=limit,
        offset=offset,
        allowed_automation_ids=accessible_automation_ids,
    )
    return HostListResponse(total=total, limit=limit, offset=offset, items=items)


@router.get(
    "/hosts/{host_id}/instances",
    response_model=List[HostAutomationSummary],
    tags=["insights"],
)
def list_host_instances(
    host_id: UUID,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
    accessible_automation_ids: list[UUID] | None = Depends(get_accessible_automation_ids),
):
    _check_host_access(host_id, accessible_automation_ids, db)
    return crud.list_host_instances(db, host_id)


@router.get("/hosts/{host_id}", response_model=HostSummary, tags=["insights"])
def get_host(
    host_id: UUID,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
    accessible_automation_ids: list[UUID] | None = Depends(get_accessible_automation_ids),
):
    _check_host_access(host_id, accessible_automation_ids, db)
    host = crud.get_host_summary(db, host_id)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    return host


@router.patch("/hosts/{host_id}", response_model=HostSummary, tags=["insights"])
def update_host(
    host_id: UUID,
    body: HostUpdateRequest,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
    accessible_automation_ids: list[UUID] | None = Depends(get_accessible_automation_ids),
):
    _check_host_access(host_id, accessible_automation_ids, db)
    host = crud.update_host_display_name(db, host_id, body.display_name)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    db.commit()
    summary = crud.get_host_summary(db, host_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Host not found")
    return summary


@router.get("/automations", response_model=AutomationListResponse, tags=["insights"])
def list_automations(
    *,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
    accessible_automation_ids: list[UUID] | None = Depends(get_accessible_automation_ids),
    search: str | None = Query(None, description="Filtra por código ou nome"),
    client_id: UUID | None = Query(None, description="Limita para um cliente específico"),
    host_id: UUID | None = Query(None, description="Limita para uma máquina específica"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    # If user has restricted access and a specific host_id was requested, validate it
    if host_id and accessible_automation_ids is not None:
        _check_host_access(host_id, accessible_automation_ids, db)
    total, items = crud.list_automations(
        db,
        search=search,
        client_id=client_id,
        host_id=host_id,
        limit=limit,
        offset=offset,
        allowed_automation_ids=accessible_automation_ids,
    )
    return AutomationListResponse(total=total, limit=limit, offset=offset, items=items)


@router.get(
    "/automations/{automation_id}/instances",
    response_model=List[AutomationInstanceSummary],
    tags=["insights"],
)
def list_automation_instances(
    automation_id: UUID,
    *,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
    accessible_automation_ids: list[UUID] | None = Depends(get_accessible_automation_ids),
    client_id: UUID | None = Query(None),
    host_id: UUID | None = Query(None),
):
    if host_id and accessible_automation_ids is not None:
        _check_host_access(host_id, accessible_automation_ids, db)
    return crud.list_automation_instances(
        db, automation_id, client_id=client_id, host_id=host_id,
        allowed_automation_ids=accessible_automation_ids,
    )


@router.get("/automations/{automation_id}", response_model=AutomationSummary, tags=["insights"])
def get_automation(
    automation_id: UUID,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
):
    automation = crud.get_automation_summary(db, automation_id)
    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")
    return automation


@router.get(
    "/runs",
    response_model=RunListResponse,
    tags=["insights"],
)
def list_runs_global(
    *,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
    accessible_automation_ids: list[UUID] | None = Depends(get_accessible_automation_ids),
    search: str | None = Query(None, description="Busca por robo, cliente, maquina ou status"),
    client_id: UUID | None = Query(None, description="Filtra por cliente"),
    host_id: UUID | None = Query(None, description="Filtra por maquina agrupada"),
    status: str | None = Query(None, description="running, completed, failed, etc."),
    started_after: datetime | None = Query(None),
    started_before: datetime | None = Query(None),
    sort_by: str = Query("started_at", pattern="^(started_at|finished_at|log_entries)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    if host_id and accessible_automation_ids is not None:
        _check_host_access(host_id, accessible_automation_ids, db)
    total, items = crud.list_runs(
        db,
        client_id=client_id,
        host_id=host_id,
        search=search,
        status=status,
        started_after=started_after,
        started_before=started_before,
        sort_by=sort_by,
        order=order,
        limit=limit,
        offset=offset,
        allowed_automation_ids=accessible_automation_ids,
    )
    return RunListResponse(total=total, limit=limit, offset=offset, items=items)


@router.get(
    "/runs/overview",
    response_model=RunOverviewResponse,
    tags=["insights"],
)
def get_runs_overview(
    *,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
    accessible_automation_ids: list[UUID] | None = Depends(get_accessible_automation_ids),
    search: str | None = Query(None, description="Busca por robo, cliente, maquina ou status"),
    client_id: UUID | None = Query(None, description="Filtra por cliente"),
    host_id: UUID | None = Query(None, description="Filtra por maquina agrupada"),
    status: str | None = Query(None, description="running, completed, failed, etc."),
    started_after: datetime | None = Query(None),
    started_before: datetime | None = Query(None),
):
    if host_id and accessible_automation_ids is not None:
        _check_host_access(host_id, accessible_automation_ids, db)
    return crud.get_runs_overview(
        db,
        client_id=client_id,
        host_id=host_id,
        search=search,
        status=status,
        started_after=started_after,
        started_before=started_before,
        allowed_automation_ids=accessible_automation_ids,
    )


@router.get("/automations/{automation_id}/runs", response_model=RunListResponse, tags=["insights"])
def list_runs_for_automation(
    automation_id: UUID,
    *,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
    accessible_automation_ids: list[UUID] | None = Depends(get_accessible_automation_ids),
    status: str | None = Query(None, description="running, completed, failed, etc."),
    started_after: datetime | None = Query(None),
    started_before: datetime | None = Query(None),
    sort_by: str = Query("started_at", pattern="^(started_at|finished_at|log_entries)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    total, items = crud.list_runs(
        db,
        automation_id=automation_id,
        status=status,
        started_after=started_after,
        started_before=started_before,
        sort_by=sort_by,
        order=order,
        limit=limit,
        offset=offset,
        allowed_automation_ids=accessible_automation_ids,
    )
    return RunListResponse(total=total, limit=limit, offset=offset, items=items)


@router.get(
    "/instances/{instance_id}/runs",
    response_model=RunListResponse,
    tags=["insights"],
)
def list_runs_for_instance(
    instance_id: UUID,
    *,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
    accessible_automation_ids: list[UUID] | None = Depends(get_accessible_automation_ids),
    status: str | None = Query(None),
    started_after: datetime | None = Query(None),
    started_before: datetime | None = Query(None),
    sort_by: str = Query("started_at", pattern="^(started_at|finished_at|log_entries)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    total, items = crud.list_runs(
        db,
        instance_id=instance_id,
        status=status,
        started_after=started_after,
        started_before=started_before,
        sort_by=sort_by,
        order=order,
        limit=limit,
        offset=offset,
        allowed_automation_ids=accessible_automation_ids,
    )
    return RunListResponse(total=total, limit=limit, offset=offset, items=items)


@router.get("/runs/timeline", response_model=RunTimelineResponse, tags=["insights"])
def list_runs_timeline(
    *,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
    accessible_automation_ids: list[UUID] | None = Depends(get_accessible_automation_ids),
    started_after: datetime | None = Query(None),
    started_before: datetime | None = Query(None),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    total, items = crud.list_runs_timeline(
        db,
        started_after=started_after,
        started_before=started_before,
        limit=limit,
        offset=offset,
        allowed_automation_ids=accessible_automation_ids,
    )
    return RunTimelineResponse(total=total, limit=limit, offset=offset, items=items)


@router.get("/runs/{run_id}", response_model=RunDetailResponse, tags=["insights"])
def get_run(
    run_id: UUID,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
    accessible_automation_ids: list[UUID] | None = Depends(get_accessible_automation_ids),
):
    result = crud.get_run_detail(db, run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Run not found")
    run = result["run"]
    automation = result["automation"]
    instance = result["instance"]
    client = result["client"]
    host = result["host"]
    if host and accessible_automation_ids is not None:
        _check_host_access(host.id, accessible_automation_ids, db)
    return RunDetailResponse(
        id=run.id,
        automation_instance_id=run.automation_instance_id,
        started_at=run.started_at,
        finished_at=run.finished_at,
        status=run.status,
        server_mode=run.server_mode,
        host_ip=str(run.host_ip) if run.host_ip else None,
        root_folder=run.root_folder,
        config_version=run.config_version,
        log_entries=result["log_entries"],
        automation_id=automation.id,
        automation_code=automation.code,
        automation_name=automation.name,
        client_id=client.id if client else None,
        client_name=client.name if client else None,
        host_id=host.id if host else None,
        host_hostname=host.hostname if host else None,
        host_display_name=host.display_name if host else None,
    )


@router.get("/runs/{run_id}/logs", response_model=LogEntriesResponse, tags=["insights"])
def list_run_logs(
    run_id: UUID,
    *,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
    level: str | None = Query(None),
    search: str | None = Query(None, description="Busca textual na mensagem"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    order: str = Query("asc", pattern="^(asc|desc)$"),
):
    total, items = crud.list_run_logs(
        db,
        run_id,
        level=level,
        search=search,
        limit=limit,
        offset=offset,
        order=order,
    )
    return LogEntriesResponse(total=total, limit=limit, offset=offset, items=items)


@router.get("/runs/{run_id}/logs/metrics", response_model=LogMetricsResponse, tags=["insights"])
def get_run_logs_metrics_endpoint(
    run_id: UUID,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
):
    total, counts, timeline = crud.get_run_logs_metrics(db, run_id)
    return LogMetricsResponse(
        total=total,
        counts=counts,
        timeline=timeline,
    )


@router.get("/runs/{run_id}/emails", response_model=EmailEventListResponse, tags=["insights"])
def list_run_email_events(
    run_id: UUID,
    *,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    total, items = crud.list_run_email_events(db, run_id=run_id, limit=limit, offset=offset)
    event_ids = [item.id for item in items]
    attachments = crud.list_email_attachments(db, event_ids)
    grouped: dict[UUID, list[EmailAttachmentSummary]] = {}
    for attachment in attachments:
        grouped.setdefault(attachment.email_event_id, []).append(
            EmailAttachmentSummary(
                id=attachment.id,
                filename=attachment.filename,
                mime_type=attachment.mime_type,
                size_bytes=int(attachment.size_bytes),
                source_path=attachment.source_path,
                preview_supported=bool(attachment.preview_supported),
                created_at=attachment.created_at,
            )
        )

    payload_items: list[EmailEventSummary] = []
    for item in items:
        payload_items.append(
            EmailEventSummary(
                id=item.id,
                run_id=item.run_id,
                subject=item.subject,
                body_text=item.body_text,
                body_html=item.body_html,
                recipients=item.recipients or [],
                bcc_recipients=item.bcc_recipients or [],
                source_paths=item.source_paths or [],
                status=item.status,
                error=item.error,
                retention_days=int(item.retention_days),
                sent_at=item.sent_at,
                expires_at=item.expires_at,
                attachments=grouped.get(item.id, []),
            )
        )

    return EmailEventListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=payload_items,
    )


def _build_attachment_response(
    *,
    db: Session,
    email_id: UUID,
    attachment_id: UUID,
    inline: bool,
):
    attachment = crud.get_email_attachment(db, email_id, attachment_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    if inline and not attachment.preview_supported:
        raise HTTPException(status_code=422, detail="Attachment preview not supported")

    try:
        obj = storage.get_stream(attachment.storage_key)
    except S3Error as exc:
        raise HTTPException(status_code=404, detail=f"Attachment object not found: {exc.code}") from exc
    disposition = "inline" if inline else "attachment"
    filename = attachment.filename.replace('"', "")
    headers = {"Content-Disposition": f'{disposition}; filename="{filename}"'}
    def _iter():
        try:
            for chunk in obj.stream(amt=1024 * 1024):
                yield chunk
        finally:
            obj.close()
            obj.release_conn()

    return StreamingResponse(
        _iter(),
        media_type=attachment.mime_type or "application/octet-stream",
        headers=headers,
    )


@router.get(
    "/emails/{email_id}/attachments/{attachment_id}/download",
    tags=["insights"],
)
def download_email_attachment(
    email_id: UUID,
    attachment_id: UUID,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
):
    return _build_attachment_response(
        db=db,
        email_id=email_id,
        attachment_id=attachment_id,
        inline=False,
    )


@router.get(
    "/emails/{email_id}/attachments/{attachment_id}/preview",
    tags=["insights"],
)
def preview_email_attachment(
    email_id: UUID,
    attachment_id: UUID,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
):
    return _build_attachment_response(
        db=db,
        email_id=email_id,
        attachment_id=attachment_id,
        inline=True,
    )


@router.get("/clients", response_model=ClientListResponse, tags=["insights"])
def list_clients(
    *,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
    accessible_automation_ids: list[UUID] | None = Depends(get_accessible_automation_ids),
    search: str | None = Query(None, description="Filtra por nome/código externo"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    total, items = crud.list_clients(
        db, search=search, limit=limit, offset=offset,
        allowed_automation_ids=accessible_automation_ids,
    )
    return ClientListResponse(total=total, limit=limit, offset=offset, items=items)


@router.get("/clients/{client_id}", response_model=ClientSummary, tags=["insights"])
def get_client(
    client_id: UUID,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
    accessible_automation_ids: list[UUID] | None = Depends(get_accessible_automation_ids),
):
    if accessible_automation_ids is not None:
        from sqlalchemy import select as sa_select
        has = db.execute(
            sa_select(models.AutomationInstance.id)
            .where(
                models.AutomationInstance.client_id == client_id,
                models.AutomationInstance.automation_id.in_(accessible_automation_ids) if accessible_automation_ids else False,
            )
            .limit(1)
        ).first()
        if not has:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado a este cliente")
    client = crud.get_client_summary(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.get(
    "/clients/{client_id}/automations",
    response_model=List[ClientAutomationSummary],
    tags=["insights"],
)
def list_client_automations(
    client_id: UUID,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
    accessible_automation_ids: list[UUID] | None = Depends(get_accessible_automation_ids),
):
    return crud.list_client_automations(db, client_id, allowed_automation_ids=accessible_automation_ids)


@router.patch("/instances/{instance_id}/args", tags=["insights"])
def update_instance_args_route(
    instance_id: UUID,
    payload: InstanceArgsUpdate,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_permission(PERM_CONFIGURE_ARGS)),
):
    """Manually update available_args and default_args for an automation instance."""
    crud.update_instance_args(
        db,
        instance_id,
        available_args=payload.available_args,
        default_args=payload.default_args,
    )
    return {"ok": True}
