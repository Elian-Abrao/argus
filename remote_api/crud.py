"""CRUD helpers for the remote API."""

from datetime import datetime, timezone, timedelta
from typing import Optional, Iterable
from uuid import UUID
import uuid

from sqlalchemy.orm import Session, aliased
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, func, or_, cast, String, desc, exists, case, asc, literal

from . import models
from .config import get_settings
from .schemas import (
    AutomationInstanceRequest,
    RunCreateRequest,
    RunUpdateRequest,
    LogEntryPayload,
    SnapshotRequest,
)

settings = get_settings()


_INLINE_PREVIEW_EXTENSIONS = {
    ".txt",
    ".log",
    ".csv",
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
}

# Maps file extension to the canonical MIME type.
# Used to override incorrect Content-Types sent by HTTP clients
# (e.g. .xlsx being detected as application/zip).
_EXTENSION_MIME_MAP: dict[str, str] = {
    # Microsoft Office Open XML
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".ppt": "application/vnd.ms-powerpoint",
    # Archives
    ".zip": "application/zip",
    ".rar": "application/vnd.rar",
    ".7z": "application/x-7z-compressed",
    ".tar": "application/x-tar",
    ".gz": "application/gzip",
    # Documents
    ".pdf": "application/pdf",
    ".csv": "text/csv",
    ".txt": "text/plain",
    ".log": "text/plain",
    ".html": "text/html",
    ".json": "application/json",
    ".xml": "application/xml",
    # Images
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}


def normalize_mime_type(filename: str, provided_mime: str | None) -> str:
    """Returns the canonical MIME type for a file.

    Prefers the extension-based MIME when the provided one is generic
    (octet-stream, zip, etc.) that could be a misdetection.
    """
    ext = ""
    if "." in filename:
        ext = f".{filename.rsplit('.', 1)[1].lower()}"

    canonical = _EXTENSION_MIME_MAP.get(ext)
    if canonical:
        # Use canonical MIME if: no mime provided, or client sent a vague/wrong type
        _vague = {"application/octet-stream", "application/zip", "binary/octet-stream", ""}
        if not provided_mime or provided_mime.strip() in _vague:
            return canonical
        # Additionally force-correct known misdetections (xlsx detected as zip)
        if ext in (".xlsx", ".docx", ".pptx") and provided_mime in ("application/zip", "application/octet-stream"):
            return canonical
        return provided_mime

    return provided_mime or "application/octet-stream"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _build_grouped_host_filters(
    host_model,
    *,
    hostname: str | None,
    ip_address,
    environment: str | None,
):
    filters = []
    filters.append(host_model.hostname.is_(None) if hostname is None else host_model.hostname == hostname)
    filters.append(host_model.ip_address.is_(None) if ip_address is None else host_model.ip_address == ip_address)
    filters.append(
        host_model.environment.is_(None)
        if environment is None
        else host_model.environment == environment
    )
    return filters


def _resolve_grouped_host_filters(session: Session, host_id: UUID, *, host_model=models.Host):
    host = session.get(models.Host, host_id)
    if not host:
        return None, None
    return host, _build_grouped_host_filters(
        host_model,
        hostname=host.hostname,
        ip_address=host.ip_address,
        environment=host.environment,
    )


def _build_run_filters(
    session: Session,
    *,
    run_model=models.Run,
    instance_model=models.AutomationInstance,
    automation_model=models.Automation,
    client_model=models.Client,
    host_model=models.Host,
    automation_id: UUID | None = None,
    instance_id: UUID | None = None,
    client_id: UUID | None = None,
    host_id: UUID | None = None,
    search: str | None = None,
    status: str | None = None,
    started_after: datetime | None = None,
    started_before: datetime | None = None,
    allowed_automation_ids: list | None = None,
):
    filters = []
    if instance_id:
        filters.append(run_model.automation_instance_id == instance_id)
    if automation_id:
        filters.append(instance_model.automation_id == automation_id)
    if client_id:
        filters.append(instance_model.client_id == client_id)
    if host_id:
        _, host_filters = _resolve_grouped_host_filters(session, host_id, host_model=host_model)
        if host_filters is None:
            return None
        filters.extend(host_filters)
    if status:
        filters.append(func.lower(run_model.status) == str(status).lower())
    if started_after:
        filters.append(run_model.started_at >= started_after)
    if started_before:
        filters.append(run_model.started_at <= started_before)
    if search:
        term = f"%{search.lower()}%"
        filters.append(
            or_(
                func.lower(automation_model.name).like(term),
                func.lower(automation_model.code).like(term),
                func.lower(client_model.name).like(term),
                func.lower(client_model.external_code).like(term),
                func.lower(host_model.hostname).like(term),
                cast(host_model.ip_address, String).like(term),
                func.lower(run_model.root_folder).like(term),
                func.lower(run_model.status).like(term),
            )
        )
    if allowed_automation_ids is not None:
        if not allowed_automation_ids:
            return None
        filters.append(instance_model.automation_id.in_(allowed_automation_ids))
    return filters


def _get_run_order_clauses(sort_by: str | None, order: str | None, log_entries_expr):
    order_fn = asc if str(order or "desc").lower() == "asc" else desc
    field = str(sort_by or "started_at").lower()
    if field == "finished_at":
        finished_expr = func.coalesce(models.Run.finished_at, models.Run.started_at)
        return [order_fn(finished_expr), order_fn(models.Run.started_at)]
    if field == "log_entries":
        return [order_fn(log_entries_expr), order_fn(models.Run.started_at)]
    return [order_fn(models.Run.started_at)]


def get_or_create_client(session: Session, data) -> Optional[models.Client]:
    if data is None:
        return None
    stmt = select(models.Client)
    if data.external_code:
        stmt = stmt.where(models.Client.external_code == data.external_code)
    elif data.name:
        stmt = stmt.where(models.Client.name == data.name)
    else:
        return None
    client = session.scalars(stmt).first()
    if client:
        return client
    client = models.Client(
        name=data.name or data.external_code,
        external_code=data.external_code,
        contact_email=data.contact_email,
    )
    session.add(client)
    try:
        session.flush()
        return client
    except IntegrityError:
        session.rollback()
        return session.scalars(stmt).first()


def get_or_create_host(session: Session, data) -> models.Host:
    stmt = select(models.Host).where(
        models.Host.root_folder == data.root_folder
    )
    if data.ip_address:
        stmt = stmt.where(models.Host.ip_address == str(data.ip_address))
    host = session.scalars(stmt).first()
    if host:
        return host
    host = models.Host(
        hostname=data.hostname,
        ip_address=str(data.ip_address) if data.ip_address else None,
        root_folder=data.root_folder,
        environment=data.environment,
        tags=data.tags,
    )
    session.add(host)
    try:
        session.flush()
        return host
    except IntegrityError:
        session.rollback()
        return session.scalars(stmt).first()


def get_or_create_automation(session: Session, data) -> models.Automation:
    stmt = select(models.Automation).where(models.Automation.code == data.code)
    automation = session.scalars(stmt).first()
    if automation:
        return automation
    automation = models.Automation(
        code=data.code,
        name=data.name,
        description=data.description,
        owner_team=data.owner_team,
    )
    session.add(automation)
    try:
        session.flush()
        return automation
    except IntegrityError:
        session.rollback()
        return session.scalars(stmt).first()


def get_or_create_instance(
    session: Session, payload: AutomationInstanceRequest
) -> models.AutomationInstance:
    automation = get_or_create_automation(session, payload.automation)
    client = get_or_create_client(session, payload.client)
    host = get_or_create_host(session, payload.host)

    instance: models.AutomationInstance | None = None
    stmt = None
    if payload.instance_id:
        instance = session.get(models.AutomationInstance, payload.instance_id)
    if instance is None:
        stmt = select(models.AutomationInstance).where(
            models.AutomationInstance.automation_id == automation.id,
            models.AutomationInstance.deployment_tag == payload.deployment_tag,
        )
        if client:
            stmt = stmt.where(models.AutomationInstance.client_id == client.id)
        else:
            stmt = stmt.where(models.AutomationInstance.client_id.is_(None))
        if host:
            stmt = stmt.where(models.AutomationInstance.host_id == host.id)
        else:
            stmt = stmt.where(models.AutomationInstance.host_id.is_(None))
        instance = session.scalars(stmt).first()
    if instance:
        instance.last_seen_at = _utcnow()
        if payload.metadata:
            instance.attributes.update(payload.metadata)
        session.flush()
        return instance

    instance = models.AutomationInstance(
        id=payload.instance_id or uuid.uuid4(),
        automation_id=automation.id,
        client_id=client.id if client else None,
        host_id=host.id if host else None,
        deployment_tag=payload.deployment_tag,
        config_signature=payload.config_signature,
        attributes=payload.metadata,
        first_seen_at=_utcnow(),
        last_seen_at=_utcnow(),
    )
    session.add(instance)
    try:
        session.flush()
        return instance
    except IntegrityError:
        session.rollback()
        if payload.instance_id:
            instance = session.get(models.AutomationInstance, payload.instance_id)
            if instance:
                return instance
        if stmt is not None:
            instance = session.scalars(stmt).first()
            if instance:
                return instance
        raise


def create_run(
    session: Session,
    payload: RunCreateRequest,
    automation_instance_id: UUID | None = None,
) -> models.Run:
    instance_id = automation_instance_id or payload.automation_instance_id
    if instance_id is None:
        raise ValueError("automation_instance_id is required")
    existing = session.get(models.Run, payload.run_id)
    if existing:
        return existing
    run = models.Run(
        id=payload.run_id,
        automation_instance_id=instance_id,
        started_at=payload.started_at or _utcnow(),
        status=payload.status or "running",
        pid=payload.pid,
        user_name=payload.user_name,
        server_mode=payload.server_mode,
        host_ip=str(payload.host_ip) if payload.host_ip else None,
        root_folder=payload.root_folder,
        config_version=payload.config_version,
        attributes=payload.metadata,
    )
    session.add(run)
    session.flush()
    return run


def update_run(session: Session, run_id: UUID, payload: RunUpdateRequest) -> models.Run:
    run = session.get(models.Run, run_id)
    if not run:
        raise ValueError("Run not found")
    if payload.status:
        run.status = payload.status
    if payload.finished_at:
        run.finished_at = payload.finished_at
    if payload.metadata:
        run.attributes.update(payload.metadata)
    session.flush()
    return run


def insert_log_entries(session: Session, run_id: UUID, entries: Iterable[LogEntryPayload]) -> int:
    run = session.get(models.Run, run_id)
    if not run:
        raise ValueError("Run not found")
    objects = []
    for entry in entries:
        objects.append(
            models.LogEntry(
                run_id=run_id,
                sequence=entry.sequence,
                ts=entry.ts,
                level=entry.level,
                message=entry.message,
                logger_name=entry.logger_name,
                context=entry.context,
                extra=entry.extra,
            )
        )
    session.bulk_save_objects(objects)
    return len(objects)


def create_snapshot(session: Session, run_id: UUID, payload: SnapshotRequest) -> models.RunSnapshot:
    run = session.get(models.Run, run_id)
    if not run:
        raise ValueError("Run not found")
    snapshot = models.RunSnapshot(
        run_id=run_id,
        snapshot_type=payload.snapshot_type,
        taken_at=payload.taken_at or _utcnow(),
        payload=payload.payload,
    )
    session.add(snapshot)
    session.flush()
    return snapshot


def create_email_event(
    session: Session,
    *,
    run_id: UUID,
    subject: str | None,
    body_text: str | None,
    body_html: str | None,
    recipients: list[str],
    bcc_recipients: list[str],
    source_paths: list[str],
    status: str,
    error: str | None,
    sent_at: datetime | None = None,
    retention_days: int | None = None,
) -> models.EmailEvent:
    run = session.get(models.Run, run_id)
    if not run:
        raise ValueError("Run not found")

    if retention_days is None:
        run_retention = (run.attributes or {}).get("email_retention_days")
        if isinstance(run_retention, int) and run_retention > 0:
            retention_days = run_retention
        else:
            retention_days = settings.email_retention_days_default
    retention_days = max(1, int(retention_days))

    sent_at_value = sent_at or _utcnow()
    expires_at = sent_at_value + timedelta(days=retention_days)

    event = models.EmailEvent(
        id=uuid.uuid4(),
        run_id=run_id,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        recipients=recipients,
        bcc_recipients=bcc_recipients,
        source_paths=source_paths,
        status=status or "enviado",
        error=error,
        retention_days=retention_days,
        sent_at=sent_at_value,
        expires_at=expires_at,
    )
    session.add(event)
    session.flush()
    return event


def create_email_attachment(
    session: Session,
    *,
    email_event_id: UUID,
    filename: str,
    mime_type: str | None,
    size_bytes: int,
    storage_key: str,
    source_path: str | None = None,
) -> models.EmailAttachment:
    event = session.get(models.EmailEvent, email_event_id)
    if not event:
        raise ValueError("Email event not found")
    ext = ""
    if "." in filename:
        ext = f".{filename.rsplit('.', 1)[1].lower()}"
    preview_supported = ext in _INLINE_PREVIEW_EXTENSIONS

    attachment = models.EmailAttachment(
        id=uuid.uuid4(),
        email_event_id=email_event_id,
        filename=filename,
        mime_type=mime_type,
        size_bytes=size_bytes,
        storage_key=storage_key,
        source_path=source_path,
        preview_supported=preview_supported,
    )
    session.add(attachment)
    session.flush()
    return attachment


def list_run_email_events(
    session: Session,
    *,
    run_id: UUID,
    limit: int = 50,
    offset: int = 0,
):
    total = session.execute(
        select(func.count()).select_from(models.EmailEvent).where(models.EmailEvent.run_id == run_id)
    ).scalar_one()
    items = session.execute(
        select(models.EmailEvent)
        .where(models.EmailEvent.run_id == run_id)
        .order_by(desc(models.EmailEvent.sent_at), desc(models.EmailEvent.created_at))
        .limit(limit)
        .offset(offset)
    ).scalars().all()
    return total, items


def list_email_attachments(session: Session, email_event_ids: list[UUID]):
    if not email_event_ids:
        return []
    return session.execute(
        select(models.EmailAttachment)
        .where(models.EmailAttachment.email_event_id.in_(email_event_ids))
        .order_by(models.EmailAttachment.created_at.asc())
    ).scalars().all()


def get_email_attachment(session: Session, email_id: UUID, attachment_id: UUID) -> models.EmailAttachment | None:
    stmt = (
        select(models.EmailAttachment)
        .join(models.EmailEvent, models.EmailEvent.id == models.EmailAttachment.email_event_id)
        .where(
            models.EmailEvent.id == email_id,
            models.EmailAttachment.id == attachment_id,
        )
    )
    return session.execute(stmt).scalars().first()


# ---------------------------------------------------------------------------
# Read endpoints helpers
# ---------------------------------------------------------------------------


def list_hosts(
    session: Session,
    *,
    environment: str | None = None,
    hostname: str | None = None,
    ip_address: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    allowed_automation_ids: list | None = None,
):
    if allowed_automation_ids is not None and not allowed_automation_ids:
        return 0, []
    filters = []
    if allowed_automation_ids is not None:
        host_ids_sub = (
            select(models.AutomationInstance.host_id)
            .where(models.AutomationInstance.automation_id.in_(allowed_automation_ids))
            .distinct()
        )
        filters.append(models.Host.id.in_(host_ids_sub))
    if environment:
        filters.append(models.Host.environment == environment)
    if hostname:
        term = f"%{hostname.lower()}%"
        filters.append(func.lower(models.Host.hostname).like(term))
    if ip_address:
        filters.append(cast(models.Host.ip_address, String).like(f"%{ip_address}%"))
    if search:
        term = f"%{search.lower()}%"
        search_filter = or_(
            func.lower(models.Host.hostname).like(term),
            func.lower(models.Host.display_name).like(term),
            func.lower(models.Host.root_folder).like(term),
            cast(models.Host.ip_address, String).like(term),
        )
        filters.append(search_filter)

    grouped_hosts = (
        select(
            models.Host.hostname,
            models.Host.ip_address,
            models.Host.environment,
        )
        .where(*filters) if filters else select(
            models.Host.hostname,
            models.Host.ip_address,
            models.Host.environment,
        )
    ).group_by(
        models.Host.hostname,
        models.Host.ip_address,
        models.Host.environment,
    ).subquery()

    total = session.execute(select(func.count()).select_from(grouped_hosts)).scalar_one()

    stmt = (
        select(
            func.min(cast(models.Host.id, String)).label("id"),
            models.Host.hostname,
            func.max(models.Host.display_name).label("display_name"),
            models.Host.ip_address,
            models.Host.environment,
            func.count(func.distinct(models.Host.root_folder)).label("root_folder_count"),
            func.min(models.Host.root_folder).label("root_folder"),
            func.count(func.distinct(models.AutomationInstance.id)).label("automation_count"),
            func.max(models.AutomationInstance.last_seen_at).label("last_seen_at"),
        )
        .outerjoin(models.AutomationInstance, models.AutomationInstance.host_id == models.Host.id)
        .group_by(
            models.Host.hostname,
            models.Host.ip_address,
            models.Host.environment,
        )
        .order_by(func.lower(models.Host.hostname), models.Host.ip_address)
        .offset(offset)
        .limit(limit)
    )
    if filters:
        stmt = stmt.where(*filters)
    rows = session.execute(stmt).all()
    items = []
    for host_id, hostname_value, display_name_value, ip_value, environment_value, root_folder_count, root_folder, automation_count, last_seen in rows:
        if root_folder_count and root_folder_count > 1:
            root_folder_display = f"Varias pastas ({root_folder_count})"
        else:
            root_folder_display = root_folder
        items.append(
            {
                "id": host_id,
                "hostname": hostname_value,
                "display_name": display_name_value,
                "ip_address": str(ip_value) if ip_value else None,
                "root_folder": root_folder_display,
                "environment": environment_value,
                "tags": {},
                "automation_count": automation_count or 0,
                "last_seen_at": last_seen,
            }
        )
    return total, items


def list_host_instances(session: Session, host_id: UUID):
    host, host_filters = _resolve_grouped_host_filters(session, host_id)
    if not host:
        return []

    stmt = (
        select(
            models.AutomationInstance,
            models.Automation,
            models.Client,
            models.Host,
            func.count(models.Run.id).label("runs_count"),
            func.max(models.Run.started_at).label("last_run_started_at"),
        )
        .join(models.Automation, models.Automation.id == models.AutomationInstance.automation_id)
        .outerjoin(models.Client, models.Client.id == models.AutomationInstance.client_id)
        .join(models.Host, models.Host.id == models.AutomationInstance.host_id)
        .outerjoin(models.Run, models.Run.automation_instance_id == models.AutomationInstance.id)
        .where(*host_filters)
        .group_by(
            models.AutomationInstance.id,
            models.Automation.id,
            models.Client.id,
            models.Host.id,
        )
        .order_by(func.lower(models.Automation.name), func.lower(models.Host.root_folder))
    )
    rows = session.execute(stmt).all()
    items = []
    for instance, automation, client, grouped_host, runs_count, last_run in rows:
        items.append(
            {
                "instance_id": instance.id,
                "automation_id": automation.id,
                "automation_code": automation.code,
                "automation_name": automation.name,
                "client_id": client.id if client else None,
                "client_name": client.name if client else None,
                "root_folder": grouped_host.root_folder if grouped_host else None,
                "deployment_tag": instance.deployment_tag,
                "config_signature": instance.config_signature,
                "last_seen_at": instance.last_seen_at,
                "runs_count": runs_count or 0,
                "last_run_started_at": last_run,
            }
        )
    return items


def list_automations(
    session: Session,
    *,
    search: str | None = None,
    client_id: UUID | None = None,
    host_id: UUID | None = None,
    limit: int = 50,
    offset: int = 0,
    allowed_automation_ids: list | None = None,
):
    if allowed_automation_ids is not None and not allowed_automation_ids:
        return 0, []
    filters = []
    if allowed_automation_ids is not None:
        filters.append(models.AutomationInstance.automation_id.in_(allowed_automation_ids))
    if search:
        term = f"%{search.lower()}%"
        filters.append(
            or_(
                func.lower(models.Automation.name).like(term),
                func.lower(models.Automation.code).like(term),
            )
        )
    if client_id:
        filters.append(models.AutomationInstance.client_id == client_id)
    if host_id:
        filters.append(models.AutomationInstance.host_id == host_id)

    stmt = (
        select(models.Automation.id)
        .outerjoin(
            models.AutomationInstance,
            models.AutomationInstance.automation_id == models.Automation.id,
        )
    )
    if filters:
        stmt = stmt.where(*filters)
    total = session.execute(
        select(func.count()).select_from(stmt.group_by(models.Automation.id).subquery())
    ).scalar_one()

    data_stmt = (
        select(
            models.Automation,
            func.count(models.AutomationInstance.id).label("instances_count"),
            func.count(func.distinct(models.AutomationInstance.host_id)).label("hosts_count"),
            func.count(func.distinct(models.AutomationInstance.client_id)).label("clients_count"),
            func.max(models.AutomationInstance.last_seen_at).label("last_seen_at"),
            func.max(models.Run.started_at).label("last_run_started_at"),
        )
        .outerjoin(
            models.AutomationInstance,
            models.AutomationInstance.automation_id == models.Automation.id,
        )
        .outerjoin(models.Run, models.Run.automation_instance_id == models.AutomationInstance.id)
    )
    if filters:
        data_stmt = data_stmt.where(*filters)
    data_stmt = (
        data_stmt.group_by(models.Automation.id)
        .order_by(models.Automation.name)
        .offset(offset)
        .limit(limit)
    )
    rows = session.execute(data_stmt).all()
    automation_ids = [row[0].id for row in rows]

    # Collect host_ids per automation in a single query
    host_ids_map: dict = {}
    if automation_ids:
        host_q = (
            select(
                models.AutomationInstance.automation_id,
                models.AutomationInstance.host_id,
            )
            .where(
                models.AutomationInstance.automation_id.in_(automation_ids),
                models.AutomationInstance.host_id.isnot(None),
            )
            .distinct()
        )
        for aid, hid in session.execute(host_q).all():
            host_ids_map.setdefault(aid, []).append(hid)

    items = []
    for automation, instances_count, hosts_count, clients_count, last_seen, last_run in rows:
        items.append(
            {
                "id": automation.id,
                "code": automation.code,
                "name": automation.name,
                "description": automation.description,
                "owner_team": automation.owner_team,
                "instances_count": instances_count or 0,
                "hosts_count": hosts_count or 0,
                "clients_count": clients_count or 0,
                "host_ids": host_ids_map.get(automation.id, []),
                "last_seen_at": last_seen,
                "last_run_started_at": last_run,
            }
        )
    return total, items


def list_automation_instances(
    session: Session,
    automation_id: UUID,
    *,
    client_id: UUID | None = None,
    host_id: UUID | None = None,
    allowed_automation_ids: list | None = None,
):
    if allowed_automation_ids is not None and not allowed_automation_ids:
        return []
    filters = [models.AutomationInstance.automation_id == automation_id]
    if allowed_automation_ids is not None:
        filters.append(models.AutomationInstance.automation_id.in_(allowed_automation_ids))
    if client_id:
        filters.append(models.AutomationInstance.client_id == client_id)
    if host_id:
        filters.append(models.AutomationInstance.host_id == host_id)
    stmt = (
        select(
            models.AutomationInstance,
            models.Automation,
            models.Client,
            models.Host,
            func.count(models.Run.id).label("total_runs"),
            func.max(models.Run.started_at).label("last_run_started_at"),
        )
        .join(models.Automation, models.Automation.id == models.AutomationInstance.automation_id)
        .outerjoin(models.Client, models.Client.id == models.AutomationInstance.client_id)
        .outerjoin(models.Host, models.Host.id == models.AutomationInstance.host_id)
        .outerjoin(models.Run, models.Run.automation_instance_id == models.AutomationInstance.id)
        .where(*filters)
        .group_by(
            models.AutomationInstance.id,
            models.Automation.id,
            models.Client.id,
            models.Host.id,
        )
        .order_by(models.Host.hostname, models.AutomationInstance.deployment_tag)
    )
    rows = session.execute(stmt).all()
    items = []
    for instance, automation, client, host, run_count, last_run in rows:
        items.append(
            {
                "id": instance.id,
                "automation_id": automation.id,
                "automation_code": automation.code,
                "automation_name": automation.name,
                "client_id": client.id if client else None,
                "client_name": client.name if client else None,
                "host_id": host.id if host else None,
                "host_hostname": host.hostname if host else None,
                "host_display_name": host.display_name if host else None,
                "host_ip": str(host.ip_address) if host and host.ip_address else None,
                "root_folder": host.root_folder if host else None,
                "deployment_tag": instance.deployment_tag,
                "config_signature": instance.config_signature,
                "last_seen_at": instance.last_seen_at,
                "total_runs": run_count or 0,
                "last_run_started_at": last_run,
                "available_args": instance.available_args or [],
                "default_args": instance.default_args or [],
            }
        )
    return items


def list_runs(
    session: Session,
    *,
    automation_id: UUID | None = None,
    instance_id: UUID | None = None,
    client_id: UUID | None = None,
    host_id: UUID | None = None,
    search: str | None = None,
    status: str | None = None,
    started_after: datetime | None = None,
    started_before: datetime | None = None,
    sort_by: str | None = None,
    order: str | None = None,
    limit: int = 50,
    offset: int = 0,
    allowed_automation_ids: list | None = None,
):
    filters = _build_run_filters(
        session,
        automation_id=automation_id,
        instance_id=instance_id,
        client_id=client_id,
        host_id=host_id,
        search=search,
        status=status,
        started_after=started_after,
        started_before=started_before,
        allowed_automation_ids=allowed_automation_ids,
    )
    if filters is None:
        return 0, []

    count_stmt = (
        select(func.count())
        .select_from(models.Run)
        .join(
            models.AutomationInstance,
            models.AutomationInstance.id == models.Run.automation_instance_id,
        )
        .join(models.Automation, models.Automation.id == models.AutomationInstance.automation_id)
        .outerjoin(models.Client, models.Client.id == models.AutomationInstance.client_id)
        .outerjoin(models.Host, models.Host.id == models.AutomationInstance.host_id)
    )
    log_entries_expr = func.count(models.LogEntry.id).label("log_entries")
    # Detecta runs agendadas: tem Command com scheduled_job_id OU
    # não tem Command mas existe um ScheduledJob para a instância (agente que dispara sem Command)
    has_schedule_sub = (
        select(models.ScheduledJob.id)
        .where(models.ScheduledJob.automation_instance_id == models.Run.automation_instance_id)
        .correlate(models.Run)
        .exists()
    )
    origin_expr = case(
        (models.Command.id.isnot(None) & models.Command.scheduled_job_id.isnot(None), literal("scheduler")),
        (models.Command.id.isnot(None), literal("manual")),
        (has_schedule_sub, literal("scheduler")),
        else_=literal("manual"),
    ).label("origin")
    data_stmt = select(
        models.Run,
        models.Automation,
        models.Client,
        models.Host,
        log_entries_expr,
        origin_expr,
    ).outerjoin(models.LogEntry, models.LogEntry.run_id == models.Run.id)
    data_stmt = (
        data_stmt.join(
            models.AutomationInstance,
            models.AutomationInstance.id == models.Run.automation_instance_id,
        )
        .join(models.Automation, models.Automation.id == models.AutomationInstance.automation_id)
        .outerjoin(models.Client, models.Client.id == models.AutomationInstance.client_id)
        .outerjoin(models.Host, models.Host.id == models.AutomationInstance.host_id)
        .outerjoin(models.Command, models.Command.run_id == models.Run.id)
    )
    if filters:
        count_stmt = count_stmt.where(*filters)
        data_stmt = data_stmt.where(*filters)

    total = session.execute(count_stmt).scalar_one()

    data_stmt = (
        data_stmt.group_by(
            models.Run.id,
            models.Automation.id,
            models.Client.id,
            models.Host.id,
            models.Command.id,
            models.Command.scheduled_job_id,
        )
        .order_by(*_get_run_order_clauses(sort_by, order, log_entries_expr))
        .offset(offset)
        .limit(limit)
    )
    rows = session.execute(data_stmt).all()
    items = []
    for run, automation, client, host, log_entries, origin in rows:
        items.append(
            {
                "id": run.id,
                "automation_instance_id": run.automation_instance_id,
                "automation_id": automation.id if automation else None,
                "automation_code": automation.code if automation else None,
                "automation_name": automation.name if automation else None,
                "client_id": client.id if client else None,
                "client_name": client.name if client else None,
                "host_id": host.id if host else None,
                "host_hostname": host.hostname if host else None,
                "host_display_name": host.display_name if host else None,
                "started_at": run.started_at,
                "finished_at": run.finished_at,
                "status": run.status,
                "server_mode": run.server_mode,
                "host_ip": str(run.host_ip) if run.host_ip else None,
                "root_folder": run.root_folder,
                "config_version": run.config_version,
                "log_entries": log_entries or 0,
                "origin": origin,
            }
        )
    return total, items


def get_runs_overview(
    session: Session,
    *,
    automation_id: UUID | None = None,
    instance_id: UUID | None = None,
    client_id: UUID | None = None,
    host_id: UUID | None = None,
    search: str | None = None,
    status: str | None = None,
    started_after: datetime | None = None,
    started_before: datetime | None = None,
    allowed_automation_ids: list | None = None,
):
    filters = _build_run_filters(
        session,
        automation_id=automation_id,
        instance_id=instance_id,
        client_id=client_id,
        host_id=host_id,
        search=search,
        status=status,
        started_after=started_after,
        started_before=started_before,
        allowed_automation_ids=allowed_automation_ids,
    )
    if filters is None:
        return {
            "total_runs": 0,
            "total_logs": 0,
            "status_counts": {},
            "runs_by_day": [],
            "runs_by_hour": [],
        }

    base_stmt = (
        select(models.Run)
        .join(
            models.AutomationInstance,
            models.AutomationInstance.id == models.Run.automation_instance_id,
        )
        .join(models.Automation, models.Automation.id == models.AutomationInstance.automation_id)
        .outerjoin(models.Client, models.Client.id == models.AutomationInstance.client_id)
        .outerjoin(models.Host, models.Host.id == models.AutomationInstance.host_id)
    )
    total_runs_stmt = select(func.count()).select_from(base_stmt.where(*filters).subquery())
    total_runs = session.execute(total_runs_stmt).scalar_one()

    total_logs_stmt = (
        select(func.count(models.LogEntry.id))
        .select_from(models.Run)
        .join(
            models.AutomationInstance,
            models.AutomationInstance.id == models.Run.automation_instance_id,
        )
        .join(models.Automation, models.Automation.id == models.AutomationInstance.automation_id)
        .outerjoin(models.Client, models.Client.id == models.AutomationInstance.client_id)
        .outerjoin(models.Host, models.Host.id == models.AutomationInstance.host_id)
        .outerjoin(models.LogEntry, models.LogEntry.run_id == models.Run.id)
        .where(*filters)
    )
    total_logs = session.execute(total_logs_stmt).scalar_one() or 0

    status_stmt = (
        select(models.Run.status, func.count(models.Run.id))
        .select_from(models.Run)
        .join(
            models.AutomationInstance,
            models.AutomationInstance.id == models.Run.automation_instance_id,
        )
        .join(models.Automation, models.Automation.id == models.AutomationInstance.automation_id)
        .outerjoin(models.Client, models.Client.id == models.AutomationInstance.client_id)
        .outerjoin(models.Host, models.Host.id == models.AutomationInstance.host_id)
        .where(*filters)
        .group_by(models.Run.status)
    )
    status_rows = session.execute(status_stmt).all()
    status_counts = {str(status_value or "unknown"): count for status_value, count in status_rows}

    day_bucket = func.date_trunc("day", models.Run.started_at)
    runs_by_day_stmt = (
        select(day_bucket.label("bucket"), func.count(models.Run.id))
        .select_from(models.Run)
        .join(
            models.AutomationInstance,
            models.AutomationInstance.id == models.Run.automation_instance_id,
        )
        .join(models.Automation, models.Automation.id == models.AutomationInstance.automation_id)
        .outerjoin(models.Client, models.Client.id == models.AutomationInstance.client_id)
        .outerjoin(models.Host, models.Host.id == models.AutomationInstance.host_id)
        .where(*filters)
        .group_by(day_bucket)
        .order_by(day_bucket)
    )
    day_rows = session.execute(runs_by_day_stmt).all()
    runs_by_day = [
        {
            "bucket": bucket.isoformat(),
            "label": bucket.strftime("%d/%m"),
            "total": total,
        }
        for bucket, total in day_rows
        if bucket is not None
    ]

    hour_bucket = cast(func.extract("hour", models.Run.started_at), String)
    runs_by_hour_stmt = (
        select(hour_bucket.label("bucket"), func.count(models.Run.id))
        .select_from(models.Run)
        .join(
            models.AutomationInstance,
            models.AutomationInstance.id == models.Run.automation_instance_id,
        )
        .join(models.Automation, models.Automation.id == models.AutomationInstance.automation_id)
        .outerjoin(models.Client, models.Client.id == models.AutomationInstance.client_id)
        .outerjoin(models.Host, models.Host.id == models.AutomationInstance.host_id)
        .where(*filters)
        .group_by(hour_bucket)
        .order_by(hour_bucket)
    )
    hour_rows = session.execute(runs_by_hour_stmt).all()
    runs_by_hour = []
    for hour_value, total in hour_rows:
        if hour_value is None:
            continue
        hour = str(hour_value).split(".")[0].zfill(2)
        runs_by_hour.append(
            {
                "bucket": hour,
                "label": f"{hour}h",
                "total": total,
            }
        )

    return {
        "total_runs": total_runs,
        "total_logs": int(total_logs),
        "status_counts": status_counts,
        "runs_by_day": runs_by_day,
        "runs_by_hour": runs_by_hour,
    }


def get_run_detail(session: Session, run_id: UUID):
    stmt = (
        select(
            models.Run,
            models.AutomationInstance,
            models.Automation,
            models.Client,
            models.Host,
            func.count(models.LogEntry.id).label("log_entries"),
        )
        .join(
            models.AutomationInstance,
            models.AutomationInstance.id == models.Run.automation_instance_id,
        )
        .join(models.Automation, models.Automation.id == models.AutomationInstance.automation_id)
        .outerjoin(models.Client, models.Client.id == models.AutomationInstance.client_id)
        .outerjoin(models.Host, models.Host.id == models.AutomationInstance.host_id)
        .outerjoin(models.LogEntry, models.LogEntry.run_id == models.Run.id)
        .where(models.Run.id == run_id)
        .group_by(
            models.Run.id,
            models.AutomationInstance.id,
            models.Automation.id,
            models.Client.id,
            models.Host.id,
        )
    )
    result = session.execute(stmt).first()
    if not result:
        return None
    run, instance, automation, client, host, log_entries = result
    return {
        "run": run,
        "instance": instance,
        "automation": automation,
        "client": client,
        "host": host,
        "log_entries": log_entries or 0,
    }


def list_run_logs(
    session: Session,
    run_id: UUID,
    *,
    level: str | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
    order: str = "asc",
):
    filters = [models.LogEntry.run_id == run_id]
    if level:
        filters.append(func.upper(models.LogEntry.level) == level.upper())
    if search:
        term = f"%{search.lower()}%"
        filters.append(func.lower(models.LogEntry.message).like(term))

    count_stmt = select(func.count()).select_from(models.LogEntry).where(*filters)
    total = session.execute(count_stmt).scalar_one()

    order_fn = desc if str(order).lower() == "desc" else lambda col: col
    stmt = (
        select(models.LogEntry)
        .where(*filters)
        .order_by(order_fn(models.LogEntry.sequence))
        .offset(offset)
        .limit(limit)
    )
    rows = session.execute(stmt).scalars().all()
    items = []
    for entry in rows:
        items.append(
            {
                "sequence": entry.sequence,
                "ts": entry.ts,
                "level": entry.level,
                "message": entry.message,
                "logger_name": entry.logger_name,
                "context": entry.context or {},
                "extra": entry.extra or {},
            }
        )
    return total, items

def get_run_logs_metrics(session: Session, run_id: UUID):
    # Exclude SPAN-level entries (internal tracer events) from all metrics
    _base = [
        models.LogEntry.run_id == run_id,
        models.LogEntry.level != "SPAN",
    ]

    count_stmt = select(func.count()).select_from(models.LogEntry).where(*_base)
    total = session.execute(count_stmt).scalar_one()

    # Aggregate total counts by log level
    counts_stmt = (
        select(models.LogEntry.level, func.count())
        .where(*_base)
        .group_by(models.LogEntry.level)
    )
    counts_raw = session.execute(counts_stmt).all()
    counts = {level.upper(): count for level, count in counts_raw}

    # Fetch ordered timeline of events (level and ts only)
    timeline_stmt = (
        select(models.LogEntry.ts, models.LogEntry.level)
        .where(*_base)
        .order_by(models.LogEntry.ts)
    )
    timeline_raw = session.execute(timeline_stmt).all()
    timeline = [{"ts": ts, "level": level.upper()} for ts, level in timeline_raw]

    return total, counts, timeline


def list_runs_timeline(
    session: Session,
    *,
    started_after: datetime | None = None,
    started_before: datetime | None = None,
    limit: int = 200,
    offset: int = 0,
    allowed_automation_ids: list | None = None,
):
    log_max_subq = (
        select(
            models.LogEntry.run_id.label("run_id"),
            func.max(models.LogEntry.ts).label("last_log_at"),
        )
        .group_by(models.LogEntry.run_id)
        .subquery()
    )

    filters = []
    if started_before:
        filters.append(models.Run.started_at <= started_before)

    if started_after:
        # Closed runs are shown if they finished during/after the window.
        closed_in_window = models.Run.finished_at >= started_after

        # Open runs are shown only when they had activity in the window.
        # This prevents old stale runs (finished_at NULL and no logs for days)
        # from polluting the timeline forever.
        open_with_recent_activity = (
            models.Run.finished_at.is_(None)
            & (
                (models.Run.started_at >= started_after)
                | (log_max_subq.c.last_log_at >= started_after)
            )
        )

        filters.append(or_(closed_in_window, open_with_recent_activity))

    if allowed_automation_ids is not None:
        if not allowed_automation_ids:
            return 0, []
        filters.append(models.AutomationInstance.automation_id.in_(allowed_automation_ids))

    run_alias = aliased(models.Run)
    instance_alias = aliased(models.AutomationInstance)
    automation_alias = aliased(models.Automation)
    overlap_expr = case(
        (
            models.Run.finished_at.is_(None)
            & exists(
                select(1).where(
                    run_alias.automation_instance_id == models.Run.automation_instance_id,
                    run_alias.started_at > models.Run.started_at,
                )
            ),
            True,
        ),
        else_=False,
    ).label("has_overlap")
    code_overlap_expr = case(
        (
            models.Run.finished_at.is_(None)
            & exists(
                select(1)
                .select_from(run_alias)
                .join(
                    instance_alias,
                    instance_alias.id == run_alias.automation_instance_id,
                )
                .join(
                    automation_alias,
                    automation_alias.id == instance_alias.automation_id,
                )
                .where(
                    run_alias.started_at > models.Run.started_at,
                    automation_alias.code == models.Automation.code,
                    instance_alias.host_id == models.AutomationInstance.host_id,
                )
            ),
            True,
        ),
        else_=False,
    ).label("has_code_overlap")

    count_stmt = (
        select(func.count())
        .select_from(models.Run)
        .outerjoin(log_max_subq, log_max_subq.c.run_id == models.Run.id)
    )
    if allowed_automation_ids is not None:
        count_stmt = (
            count_stmt
            .join(models.AutomationInstance, models.AutomationInstance.id == models.Run.automation_instance_id)
            .outerjoin(models.Host, models.Host.id == models.AutomationInstance.host_id)
        )
    data_stmt = (
        select(
            models.Run,
            models.Automation,
            models.Client,
            models.Host,
            log_max_subq.c.last_log_at,
            overlap_expr,
            code_overlap_expr,
        )
        .join(
            models.AutomationInstance,
            models.AutomationInstance.id == models.Run.automation_instance_id,
        )
        .join(models.Automation, models.Automation.id == models.AutomationInstance.automation_id)
        .outerjoin(models.Client, models.Client.id == models.AutomationInstance.client_id)
        .outerjoin(models.Host, models.Host.id == models.AutomationInstance.host_id)
        .outerjoin(log_max_subq, log_max_subq.c.run_id == models.Run.id)
    )
    if filters:
        count_stmt = count_stmt.where(*filters)
        data_stmt = data_stmt.where(*filters)

    total = session.execute(count_stmt).scalar_one()
    rows = session.execute(
        data_stmt.order_by(desc(models.Run.started_at)).offset(offset).limit(limit)
    ).all()
    items = []
    for run, automation, client, host, last_log_at, has_overlap, has_code_overlap in rows:
        items.append(
            {
                "id": run.id,
                "automation_instance_id": run.automation_instance_id,
                "automation_code": automation.code if automation else None,
                "automation_name": automation.name if automation else None,
                "client_name": client.name if client else None,
                "host_hostname": host.hostname if host else None,
                "started_at": run.started_at,
                "finished_at": run.finished_at,
                "status": run.status,
                "last_log_at": last_log_at,
                "has_overlap": bool(has_overlap),
                "has_code_overlap": bool(has_code_overlap),
            }
        )
    return total, items

def get_host_summary(session: Session, host_id: UUID):
    host, host_filters = _resolve_grouped_host_filters(session, host_id)
    if not host:
        return None

    stmt = (
        select(
            func.count(func.distinct(models.Host.root_folder)).label("root_folder_count"),
            func.min(models.Host.root_folder).label("root_folder"),
            func.count(func.distinct(models.AutomationInstance.id)).label("automation_count"),
            func.max(models.AutomationInstance.last_seen_at).label("last_seen_at"),
        )
        .outerjoin(models.AutomationInstance, models.AutomationInstance.host_id == models.Host.id)
        .where(*host_filters)
    )
    result = session.execute(stmt).first()
    if not result:
        return None
    root_folder_count, root_folder, automation_count, last_seen = result
    if root_folder_count and root_folder_count > 1:
        root_folder_display = f"Varias pastas ({root_folder_count})"
    else:
        root_folder_display = root_folder
    return {
        "id": host.id,
        "hostname": host.hostname,
        "display_name": host.display_name,
        "ip_address": str(host.ip_address) if host.ip_address else None,
        "root_folder": root_folder_display,
        "environment": host.environment,
        "tags": host.tags or {},
        "automation_count": automation_count or 0,
        "last_seen_at": last_seen,
    }


def update_host_display_name(session: Session, host_id: UUID, display_name: str | None) -> models.Host | None:
    host = session.get(models.Host, host_id)
    if not host:
        return None
    # Update all hosts in the same group (same hostname + ip)
    session.query(models.Host).filter(
        models.Host.hostname == host.hostname,
        models.Host.ip_address == host.ip_address,
    ).update({"display_name": display_name})
    session.flush()
    return host


def get_automation_summary(session: Session, automation_id: UUID):
    stmt = (
        select(
            models.Automation,
            func.count(models.AutomationInstance.id).label("instances_count"),
            func.count(func.distinct(models.AutomationInstance.host_id)).label("hosts_count"),
            func.count(func.distinct(models.AutomationInstance.client_id)).label("clients_count"),
            func.max(models.AutomationInstance.last_seen_at).label("last_seen_at"),
            func.max(models.Run.started_at).label("last_run_started_at"),
        )
        .outerjoin(
            models.AutomationInstance,
            models.AutomationInstance.automation_id == models.Automation.id,
        )
        .outerjoin(models.Run, models.Run.automation_instance_id == models.AutomationInstance.id)
        .where(models.Automation.id == automation_id)
        .group_by(models.Automation.id)
    )
    result = session.execute(stmt).first()
    if not result:
        return None
    automation, instances_count, hosts_count, clients_count, last_seen, last_run = result
    return {
        "id": automation.id,
        "code": automation.code,
        "name": automation.name,
        "description": automation.description,
        "owner_team": automation.owner_team,
        "instances_count": instances_count or 0,
        "hosts_count": hosts_count or 0,
        "clients_count": clients_count or 0,
        "last_seen_at": last_seen,
        "last_run_started_at": last_run,
    }


def get_client_summary(session: Session, client_id: UUID):
    stmt = (
        select(
            models.Client,
            func.count(func.distinct(models.AutomationInstance.automation_id)).label("automations_count"),
            func.count(models.AutomationInstance.id).label("instances_count"),
            func.max(models.AutomationInstance.last_seen_at).label("last_seen_at"),
        )
        .outerjoin(models.AutomationInstance, models.AutomationInstance.client_id == models.Client.id)
        .where(models.Client.id == client_id)
        .group_by(models.Client.id)
    )
    result = session.execute(stmt).first()
    if not result:
        return None
    client, automations_count, instances_count, last_seen = result
    return {
        "id": client.id,
        "name": client.name,
        "external_code": client.external_code,
        "contact_email": client.contact_email,
        "automations_count": automations_count or 0,
        "instances_count": instances_count or 0,
        "last_seen_at": last_seen,
    }


def list_clients(
    session: Session,
    *,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    allowed_automation_ids: list | None = None,
):
    if allowed_automation_ids is not None and not allowed_automation_ids:
        return 0, []
    filters = []
    if allowed_automation_ids is not None:
        client_ids_sub = (
            select(models.AutomationInstance.client_id)
            .where(models.AutomationInstance.automation_id.in_(allowed_automation_ids))
            .distinct()
        )
        filters.append(models.Client.id.in_(client_ids_sub))
    if search:
        term = f"%{search.lower()}%"
        filters.append(
            or_(
                func.lower(models.Client.name).like(term),
                func.lower(models.Client.external_code).like(term),
            )
        )
    total_stmt = select(func.count()).select_from(models.Client)
    if filters:
        total_stmt = total_stmt.where(*filters)
    total = session.execute(total_stmt).scalar_one()

    data_stmt = (
        select(
            models.Client,
            func.count(func.distinct(models.AutomationInstance.automation_id)).label("automations_count"),
            func.count(models.AutomationInstance.id).label("instances_count"),
            func.max(models.AutomationInstance.last_seen_at).label("last_seen_at"),
        )
        .outerjoin(models.AutomationInstance, models.AutomationInstance.client_id == models.Client.id)
        .group_by(models.Client.id)
        .order_by(models.Client.name)
        .offset(offset)
        .limit(limit)
    )
    if filters:
        data_stmt = data_stmt.where(*filters)

    rows = session.execute(data_stmt).all()
    client_ids = [row[0].id for row in rows]

    # Collect host_ids per client in a single query
    host_ids_map: dict = {}
    if client_ids:
        host_q = (
            select(
                models.AutomationInstance.client_id,
                models.AutomationInstance.host_id,
            )
            .where(
                models.AutomationInstance.client_id.in_(client_ids),
                models.AutomationInstance.host_id.isnot(None),
            )
            .distinct()
        )
        for cid, hid in session.execute(host_q).all():
            host_ids_map.setdefault(cid, []).append(hid)

    items = []
    for client, automations_count, instances_count, last_seen in rows:
        items.append(
            {
                "id": client.id,
                "name": client.name,
                "external_code": client.external_code,
                "contact_email": client.contact_email,
                "automations_count": automations_count or 0,
                "instances_count": instances_count or 0,
                "host_ids": host_ids_map.get(client.id, []),
                "last_seen_at": last_seen,
            }
        )
    return total, items


def list_client_automations(session: Session, client_id: UUID, *, allowed_automation_ids: list | None = None):
    if allowed_automation_ids is not None and not allowed_automation_ids:
        return []
    filters = [models.AutomationInstance.client_id == client_id]
    if allowed_automation_ids is not None:
        filters.append(models.AutomationInstance.automation_id.in_(allowed_automation_ids))
    stmt = (
        select(
            models.Automation,
            models.AutomationInstance,
            models.Host,
            func.count(models.Run.id).label("total_runs"),
            func.max(models.Run.started_at).label("last_run_started_at"),
        )
        .join(models.AutomationInstance, models.AutomationInstance.automation_id == models.Automation.id)
        .outerjoin(models.Host, models.Host.id == models.AutomationInstance.host_id)
        .outerjoin(models.Run, models.Run.automation_instance_id == models.AutomationInstance.id)
        .where(*filters)
        .group_by(
            models.Automation.id,
            models.AutomationInstance.id,
            models.Host.id,
        )
        .order_by(models.Automation.name)
    )
    rows = session.execute(stmt).all()
    items = []
    for automation, instance, host, total_runs, last_run in rows:
        items.append(
            {
                "automation_id": automation.id,
                "automation_code": automation.code,
                "automation_name": automation.name,
                "host_id": host.id if host else None,
                "host_hostname": host.hostname if host else None,
                "host_display_name": host.display_name if host else None,
                "host_ip": str(host.ip_address) if host and host.ip_address else None,
                "deployment_tag": instance.deployment_tag,
                "last_run_started_at": last_run,
                "total_runs": total_runs or 0,
            }
        )
    return items


# ---------------------------------------------------------------------------
# Remote control: Scheduled Jobs
# ---------------------------------------------------------------------------


def create_scheduled_job(
    session: Session,
    *,
    automation_instance_id: UUID,
    script: str = "main.py",
    args: list | None = None,
    recurrence_type: str,
    recurrence_config: dict,
    execution_mode: str = "parallel",
    timezone_name: str = "America/Sao_Paulo",
    enabled: bool = True,
) -> models.ScheduledJob:
    job = models.ScheduledJob(
        automation_instance_id=automation_instance_id,
        script=script,
        args=args or [],
        recurrence_type=recurrence_type,
        recurrence_config=recurrence_config,
        execution_mode=execution_mode,
        timezone=timezone_name,
        enabled=enabled,
    )
    session.add(job)
    session.flush()
    return job


def update_scheduled_job(
    session: Session,
    job_id: UUID,
    **kwargs,
) -> models.ScheduledJob | None:
    job = session.get(models.ScheduledJob, job_id)
    if not job:
        return None
    for key, value in kwargs.items():
        if value is not None:
            setattr(job, key, value)
    job.updated_at = datetime.now(timezone.utc)
    session.flush()
    return job


def delete_scheduled_job(session: Session, job_id: UUID) -> bool:
    job = session.get(models.ScheduledJob, job_id)
    if not job:
        return False
    session.delete(job)
    session.flush()
    return True


def get_scheduled_job(session: Session, job_id: UUID) -> models.ScheduledJob | None:
    return session.get(models.ScheduledJob, job_id)


def _build_schedule_summary(job: models.ScheduledJob) -> dict:
    inst = job.automation_instance
    automation = inst.automation if inst else None
    client = inst.client if inst else None
    host = inst.host if inst else None
    return {
        "id": job.id,
        "automation_instance_id": job.automation_instance_id,
        "automation_id": automation.id if automation else None,
        "automation_code": automation.code if automation else None,
        "automation_name": automation.name if automation else None,
        "client_id": client.id if client else None,
        "client_name": client.name if client else None,
        "host_id": host.id if host else None,
        "host_hostname": host.hostname if host else None,
        "host_display_name": host.display_name if host else None,
        "script": job.script,
        "args": job.args or [],
        "recurrence_type": job.recurrence_type,
        "recurrence_config": job.recurrence_config or {},
        "execution_mode": job.execution_mode,
        "timezone": job.timezone,
        "enabled": job.enabled,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


def list_scheduled_jobs(
    session: Session,
    *,
    automation_instance_id: UUID | None = None,
    host_id: UUID | None = None,
    client_id: UUID | None = None,
    enabled: bool | None = None,
    limit: int = 50,
    offset: int = 0,
    allowed_automation_ids: list | None = None,
) -> tuple[int, list[dict]]:
    if allowed_automation_ids is not None and not allowed_automation_ids:
        return 0, []
    base = select(models.ScheduledJob).join(models.AutomationInstance)
    count_base = select(func.count(models.ScheduledJob.id)).join(models.AutomationInstance)

    filters = []
    if allowed_automation_ids is not None:
        filters.append(models.AutomationInstance.automation_id.in_(allowed_automation_ids))
    if automation_instance_id is not None:
        filters.append(models.ScheduledJob.automation_instance_id == automation_instance_id)
    if host_id is not None:
        filters.append(models.AutomationInstance.host_id == host_id)
    if client_id is not None:
        filters.append(models.AutomationInstance.client_id == client_id)
    if enabled is not None:
        filters.append(models.ScheduledJob.enabled == enabled)

    for f in filters:
        base = base.where(f)
        count_base = count_base.where(f)

    total = session.execute(count_base).scalar() or 0
    rows = (
        session.execute(
            base.order_by(models.ScheduledJob.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        .scalars()
        .all()
    )
    return total, [_build_schedule_summary(j) for j in rows]


def list_due_schedules(session: Session) -> list[models.ScheduledJob]:
    """Return enabled schedules that match the current minute."""
    from zoneinfo import ZoneInfo

    now_utc = datetime.now(timezone.utc)
    jobs = (
        session.execute(
            select(models.ScheduledJob).where(models.ScheduledJob.enabled == True)  # noqa: E712
        )
        .scalars()
        .all()
    )
    due: list[models.ScheduledJob] = []
    for job in jobs:
        try:
            tz = ZoneInfo(job.timezone)
        except (KeyError, Exception):
            continue
        local_now = now_utc.astimezone(tz)
        config = job.recurrence_config or {}
        target_time = config.get("time", "")
        if not target_time:
            continue
        current_hhmm = local_now.strftime("%H:%M")
        if current_hhmm != target_time:
            continue

        rtype = job.recurrence_type
        dow = local_now.weekday()  # 0=Mon

        if rtype == "daily":
            due.append(job)
        elif rtype == "weekdays":
            if dow < 5:
                due.append(job)
        elif rtype == "specific_days":
            days = config.get("days_of_week", [])
            if dow in days:
                due.append(job)
        elif rtype == "monthly":
            dom = config.get("day_of_month")
            if dom is None:
                continue
            if config.get("business_day"):
                target_date = _next_business_day(local_now.year, local_now.month, dom)
                if local_now.date() == target_date:
                    due.append(job)
            else:
                if local_now.day == dom:
                    due.append(job)
        elif rtype == "yearly":
            month = config.get("month")
            dom = config.get("day_of_month")
            if month is not None and dom is not None:
                if local_now.month == month and local_now.day == dom:
                    due.append(job)

    return due


def _next_business_day(year: int, month: int, day: int):
    """Given a target day-of-month, find the next business day on or after it."""
    import calendar
    from datetime import date as date_cls

    last_day = calendar.monthrange(year, month)[1]
    day = min(day, last_day)
    d = date_cls(year, month, day)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def schedule_already_dispatched(
    session: Session,
    job_id: UUID,
    minute_start: datetime,
    minute_end: datetime,
) -> bool:
    """Check if a command was already created for this schedule in the given minute."""
    return session.execute(
        select(
            exists().where(
                models.Command.scheduled_job_id == job_id,
                models.Command.created_at >= minute_start,
                models.Command.created_at < minute_end,
            )
        )
    ).scalar() or False


# ---------------------------------------------------------------------------
# Remote control: Commands
# ---------------------------------------------------------------------------


def create_command(
    session: Session,
    *,
    host_id: UUID,
    automation_instance_id: UUID,
    scheduled_job_id: UUID | None = None,
    script: str = "main.py",
    args: list | None = None,
    working_dir: str,
    execution_mode: str = "parallel",
    created_by: str = "user",
) -> models.Command:
    cmd = models.Command(
        host_id=host_id,
        automation_instance_id=automation_instance_id,
        scheduled_job_id=scheduled_job_id,
        script=script,
        args=args or [],
        working_dir=working_dir,
        execution_mode=execution_mode,
        created_by=created_by,
    )
    session.add(cmd)
    session.flush()
    return cmd


def update_command_status(
    session: Session,
    command_id: UUID,
    *,
    status: str,
    run_id: UUID | None = None,
    result_message: str | None = None,
) -> models.Command | None:
    cmd = session.get(models.Command, command_id)
    if not cmd:
        return None
    now = datetime.now(timezone.utc)
    cmd.status = status
    if status == "acked":
        cmd.acked_at = now
    elif status == "running":
        cmd.started_at = now
        if run_id:
            cmd.run_id = run_id
    elif status in ("completed", "failed", "expired", "cancelled"):
        cmd.finished_at = now
        if result_message is not None:
            cmd.result_message = result_message
    session.flush()
    return cmd


def get_pending_commands_for_host(session: Session, host_id: UUID) -> list[models.Command]:
    return (
        session.execute(
            select(models.Command)
            .where(
                models.Command.host_id == host_id,
                models.Command.status == "pending",
            )
            .order_by(models.Command.created_at)
        )
        .scalars()
        .all()
    )


def has_running_commands_on_host(session: Session, host_id: UUID) -> bool:
    return session.execute(
        select(
            exists().where(
                models.Command.host_id == host_id,
                models.Command.status.in_(["acked", "running"]),
            )
        )
    ).scalar() or False


def _build_command_summary(cmd: models.Command) -> dict:
    inst = cmd.automation_instance
    automation = inst.automation if inst else None
    client = inst.client if inst else None
    host = cmd.host
    return {
        "id": cmd.id,
        "scheduled_job_id": cmd.scheduled_job_id,
        "host_id": cmd.host_id,
        "host_hostname": host.hostname if host else None,
        "automation_instance_id": cmd.automation_instance_id,
        "automation_code": automation.code if automation else None,
        "automation_name": automation.name if automation else None,
        "client_name": client.name if client else None,
        "script": cmd.script,
        "args": cmd.args or [],
        "working_dir": cmd.working_dir,
        "execution_mode": cmd.execution_mode,
        "status": cmd.status,
        "run_id": cmd.run_id,
        "created_by": cmd.created_by,
        "created_at": cmd.created_at,
        "acked_at": cmd.acked_at,
        "started_at": cmd.started_at,
        "finished_at": cmd.finished_at,
        "result_message": cmd.result_message,
    }


def list_commands(
    session: Session,
    *,
    host_id: UUID | None = None,
    automation_instance_id: UUID | None = None,
    status: str | None = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
    allowed_automation_ids: list | None = None,
) -> tuple[int, list[dict]]:
    if allowed_automation_ids is not None and not allowed_automation_ids:
        return 0, []
    base = select(models.Command)
    count_base = select(func.count(models.Command.id))
    if allowed_automation_ids is not None:
        base = base.join(
            models.AutomationInstance,
            models.AutomationInstance.id == models.Command.automation_instance_id,
        )
        count_base = count_base.join(
            models.AutomationInstance,
            models.AutomationInstance.id == models.Command.automation_instance_id,
        )

    filters = []
    if allowed_automation_ids is not None:
        filters.append(models.AutomationInstance.automation_id.in_(allowed_automation_ids))
    if host_id is not None:
        filters.append(models.Command.host_id == host_id)
    if automation_instance_id is not None:
        filters.append(models.Command.automation_instance_id == automation_instance_id)
    if status is not None:
        filters.append(models.Command.status == status)
    if created_after is not None:
        filters.append(models.Command.created_at >= created_after)
    if created_before is not None:
        filters.append(models.Command.created_at <= created_before)

    for f in filters:
        base = base.where(f)
        count_base = count_base.where(f)

    total = session.execute(count_base).scalar() or 0
    rows = (
        session.execute(
            base.order_by(models.Command.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        .scalars()
        .all()
    )
    return total, [_build_command_summary(c) for c in rows]


def get_command(session: Session, command_id: UUID) -> models.Command | None:
    return session.get(models.Command, command_id)


def expire_old_pending_commands(session: Session, *, older_than_hours: int = 2) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
    rows = (
        session.execute(
            select(models.Command).where(
                models.Command.status == "pending",
                models.Command.created_at < cutoff,
            )
        )
        .scalars()
        .all()
    )
    count = 0
    for cmd in rows:
        cmd.status = "expired"
        cmd.finished_at = datetime.now(timezone.utc)
        cmd.result_message = "Expirado — agente não respondeu a tempo"
        count += 1
    if count:
        session.flush()
    return count


# ---------------------------------------------------------------------------
# Remote control: Host agent ping / instance args
# ---------------------------------------------------------------------------


def update_host_agent_ping(session: Session, host_id: UUID) -> None:
    host = session.get(models.Host, host_id)
    if host:
        host.last_agent_ping = datetime.now(timezone.utc)
        session.flush()


def update_instance_args(
    session: Session,
    instance_id: UUID,
    *,
    available_args: list | None = None,
    default_args: list | None = None,
) -> None:
    inst = session.get(models.AutomationInstance, instance_id)
    if not inst:
        return
    if available_args is not None:
        inst.available_args = available_args
    if default_args is not None:
        inst.default_args = default_args
    session.flush()
