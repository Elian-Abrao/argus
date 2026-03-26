"""Routes for email audit ingestion."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from .. import crud, models
from ..database import get_db
from ..schemas import (
    EmailAttachmentCreateResponse,
    EmailEventCreateRequest,
    EmailEventCreateResponse,
)
from ..storage import storage
from ..crud import normalize_mime_type


router = APIRouter()


def _ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@router.post(
    "/runs/{run_id}/emails",
    response_model=EmailEventCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def ingest_email_event(
    run_id: UUID,
    payload: EmailEventCreateRequest,
    db: Session = Depends(get_db),
):
    try:
        event = crud.create_email_event(
            db,
            run_id=run_id,
            subject=payload.subject,
            body_text=payload.body_text,
            body_html=payload.body_html,
            recipients=list(payload.recipients or []),
            bcc_recipients=list(payload.bcc_recipients or []),
            source_paths=list(payload.source_paths or []),
            status=payload.status,
            error=payload.error,
            sent_at=_ensure_utc(payload.sent_at),
            retention_days=payload.retention_days,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao persistir email: {exc}") from exc
    return EmailEventCreateResponse(email_id=event.id)


@router.post(
    "/runs/{run_id}/emails/{email_id}/attachments",
    response_model=EmailAttachmentCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_email_attachment(
    run_id: UUID,
    email_id: UUID,
    file: UploadFile = File(...),
    source_path: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    event = db.get(models.EmailEvent, email_id)
    if not event or event.run_id != run_id:
        raise HTTPException(status_code=404, detail="Email event not found for run")

    raw = await file.read()
    filename = Path(file.filename or "anexo").name
    storage_key = f"{run_id}/{email_id}/{uuid4()}-{filename}"
    # Normalize MIME type by extension to prevent misdetection
    # (e.g. .xlsx being uploaded as application/zip)
    content_type = normalize_mime_type(filename, file.content_type)

    try:
        stored = storage.put_bytes(
            storage_key=storage_key,
            payload=raw,
            content_type=content_type,
        )
        attachment = crud.create_email_attachment(
            db,
            email_event_id=email_id,
            filename=filename,
            mime_type=stored.content_type,
            size_bytes=stored.size_bytes,
            storage_key=stored.storage_key,
            source_path=source_path,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao armazenar anexo: {exc}") from exc

    return EmailAttachmentCreateResponse(
        attachment_id=attachment.id,
        filename=attachment.filename,
        mime_type=attachment.mime_type,
        size_bytes=int(attachment.size_bytes),
        preview_supported=bool(attachment.preview_supported),
    )
