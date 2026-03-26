"""Retention cleanup routines for email audit data."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging

from sqlalchemy import and_, func, or_, select

from . import models
from .database import session_scope
from .storage import storage


logger = logging.getLogger("remote_api.retention")


def cleanup_expired_email_data(*, batch_size: int = 500) -> dict[str, int]:
    """Deletes expired email events and associated MinIO objects."""
    limit = max(1, int(batch_size))
    now = datetime.now(timezone.utc)

    removed_events = 0
    removed_attachments = 0

    with session_scope() as session:
        events = session.execute(
            select(models.EmailEvent)
            .where(models.EmailEvent.expires_at <= now)
            .order_by(models.EmailEvent.expires_at.asc())
            .limit(limit)
        ).scalars().all()
        if not events:
            return {"events": 0, "attachments": 0}

        event_ids = [event.id for event in events]
        attachments = session.execute(
            select(models.EmailAttachment).where(models.EmailAttachment.email_event_id.in_(event_ids))
        ).scalars().all()

        for attachment in attachments:
            try:
                storage.remove(attachment.storage_key)
            except Exception:  # pragma: no cover - best effort
                logger.exception("Falha ao remover anexo expirado no storage: %s", attachment.storage_key)

        removed_attachments = len(attachments)
        for event in events:
            session.delete(event)
        removed_events = len(events)

    if removed_events > 0:
        logger.info(
            "Cleanup de retenção finalizado: %d eventos e %d anexos removidos",
            removed_events,
            removed_attachments,
        )
    return {"events": removed_events, "attachments": removed_attachments}


def stop_stale_running_runs(
    *,
    stale_after_hours: float = 0.5,
    batch_size: int = 500,
) -> dict[str, int]:
    """
    Mark runs as failed when they remain in "running" without log activity
    for longer than ``stale_after_hours`` (supports fractions, e.g. 0.5 = 30 min).
    """
    limit = max(1, int(batch_size))
    stale_hours = max(1 / 60, float(stale_after_hours))
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=stale_hours)

    log_max_subq = (
        select(
            models.LogEntry.run_id.label("run_id"),
            func.max(models.LogEntry.ts).label("last_log_at"),
        )
        .group_by(models.LogEntry.run_id)
        .subquery()
    )

    stale_filter = or_(
        and_(
            log_max_subq.c.last_log_at.is_not(None),
            log_max_subq.c.last_log_at < cutoff,
        ),
        and_(
            log_max_subq.c.last_log_at.is_(None),
            models.Run.started_at < cutoff,
        ),
    )

    with session_scope() as session:
        rows = session.execute(
            select(models.Run, log_max_subq.c.last_log_at)
            .outerjoin(log_max_subq, log_max_subq.c.run_id == models.Run.id)
            .where(
                models.Run.status == "running",
                models.Run.finished_at.is_(None),
                stale_filter,
            )
            .order_by(models.Run.started_at.asc())
            .limit(limit)
        ).all()
        if not rows:
            return {"runs": 0}

        stopped_runs = 0
        for run, last_log_at in rows:
            finished_at = last_log_at or run.started_at or now
            if finished_at.tzinfo is None:
                finished_at = finished_at.replace(tzinfo=timezone.utc)

            metadata = dict(run.attributes or {})
            metadata["stale_auto_failed"] = {
                "checked_at": now.isoformat(),
                "stale_after_hours": stale_hours,
                "last_log_at": last_log_at.isoformat() if last_log_at else None,
            }

            run.status = "failed"
            run.finished_at = finished_at
            run.attributes = metadata
            stopped_runs += 1

    if stopped_runs > 0:
        logger.info(
            "Auto-fail finalizado: %d run(s) marcados como failed (sem logs ha mais de %.1fh)",
            stopped_runs,
            stale_hours,
        )
    return {"runs": stopped_runs}
