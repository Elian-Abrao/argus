"""CRUD routes for scheduled jobs."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from .. import crud, models
from ..auth.dependencies import get_current_user, get_accessible_automation_ids, require_permission, PERM_RUN_AUTOMATIONS
from ..schemas import (
    ScheduleCreateRequest,
    ScheduleUpdateRequest,
    ScheduleSummary,
    ScheduleListResponse,
    CalendarEvent,
    CalendarResponse,
)

router = APIRouter()


# --- Calendar must be registered BEFORE /{schedule_id} ---


@router.get("/schedules/calendar", response_model=CalendarResponse, tags=["schedules"])
def get_calendar(
    *,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
    accessible_automation_ids: list = Depends(get_accessible_automation_ids),
    start: datetime = Query(..., description="Início da janela ISO 8601"),
    end: datetime = Query(..., description="Fim da janela ISO 8601"),
    host_id: Optional[UUID] = Query(None),
    client_id: Optional[UUID] = Query(None),
    automation_instance_id: Optional[UUID] = Query(None),
):
    """Expand recurrence rules into concrete occurrences within [start, end]."""
    from datetime import timedelta, date as date_cls
    import calendar

    _, jobs = crud.list_scheduled_jobs(
        db,
        host_id=host_id,
        client_id=client_id,
        automation_instance_id=automation_instance_id,
        limit=500,
        offset=0,
        allowed_automation_ids=accessible_automation_ids,
    )

    events: list[dict] = []
    for job_dict in jobs:
        config = job_dict.get("recurrence_config") or {}
        target_time = config.get("time", "")
        if not target_time:
            continue

        try:
            hour, minute = map(int, target_time.split(":"))
        except (ValueError, AttributeError):
            continue

        tz_name = job_dict.get("timezone", "America/Sao_Paulo")
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            continue

        rtype = job_dict.get("recurrence_type")
        current = start.date() if hasattr(start, "date") else start
        end_date = end.date() if hasattr(end, "date") else end

        while current <= end_date:
            match = False
            if rtype == "daily":
                match = True
            elif rtype == "weekdays":
                match = current.weekday() < 5
            elif rtype == "specific_days":
                days = config.get("days_of_week", [])
                match = current.weekday() in days
            elif rtype == "monthly":
                dom = config.get("day_of_month")
                if dom is not None:
                    if config.get("business_day"):
                        target_date = crud._next_business_day(current.year, current.month, dom)
                        match = current == target_date
                    else:
                        match = current.day == dom
            elif rtype == "yearly":
                month = config.get("month")
                dom = config.get("day_of_month")
                if month is not None and dom is not None:
                    match = current.month == month and current.day == dom

            if match:
                scheduled_dt = datetime(
                    current.year, current.month, current.day,
                    hour, minute, tzinfo=tz,
                )
                events.append(
                    CalendarEvent(
                        id=job_dict["id"],
                        automation_instance_id=job_dict["automation_instance_id"],
                        automation_id=job_dict.get("automation_id"),
                        automation_code=job_dict.get("automation_code"),
                        automation_name=job_dict.get("automation_name"),
                        client_id=job_dict.get("client_id"),
                        client_name=job_dict.get("client_name"),
                        host_hostname=job_dict.get("host_hostname"),
                        host_display_name=job_dict.get("host_display_name"),
                        scheduled_time=scheduled_dt,
                        recurrence_type=rtype,
                        execution_mode=job_dict.get("execution_mode", "parallel"),
                        enabled=job_dict.get("enabled", True),
                    ).model_dump()
                )

            current += timedelta(days=1)

    events.sort(key=lambda e: e["scheduled_time"])
    return {"items": events}


# --- Standard CRUD ---


@router.get("/schedules", response_model=ScheduleListResponse, tags=["schedules"])
def list_schedules(
    *,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
    accessible_automation_ids: list = Depends(get_accessible_automation_ids),
    automation_instance_id: Optional[UUID] = Query(None),
    host_id: Optional[UUID] = Query(None),
    client_id: Optional[UUID] = Query(None),
    enabled: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    total, items = crud.list_scheduled_jobs(
        db,
        automation_instance_id=automation_instance_id,
        host_id=host_id,
        client_id=client_id,
        enabled=enabled,
        limit=limit,
        offset=offset,
        allowed_automation_ids=accessible_automation_ids,
    )
    return {"total": total, "limit": limit, "offset": offset, "items": items}


@router.post("/schedules", response_model=ScheduleSummary, status_code=201, tags=["schedules"])
def create_schedule(
    *,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_permission(PERM_RUN_AUTOMATIONS)),
    payload: ScheduleCreateRequest,
):
    job = crud.create_scheduled_job(
        db,
        automation_instance_id=payload.automation_instance_id,
        script=payload.script,
        args=payload.args,
        recurrence_type=payload.recurrence_type,
        recurrence_config=payload.recurrence_config.model_dump(exclude_none=True),
        execution_mode=payload.execution_mode,
        timezone_name=payload.timezone,
        enabled=payload.enabled,
    )
    return crud._build_schedule_summary(job)


@router.get("/schedules/{schedule_id}", response_model=ScheduleSummary, tags=["schedules"])
def get_schedule(
    schedule_id: UUID,
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
):
    job = crud.get_scheduled_job(db, schedule_id)
    if not job:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    return crud._build_schedule_summary(job)


@router.patch("/schedules/{schedule_id}", response_model=ScheduleSummary, tags=["schedules"])
def update_schedule(
    schedule_id: UUID,
    payload: ScheduleUpdateRequest,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_permission(PERM_RUN_AUTOMATIONS)),
):
    update_data = payload.model_dump(exclude_none=True)
    if "recurrence_config" in update_data and update_data["recurrence_config"] is not None:
        update_data["recurrence_config"] = payload.recurrence_config.model_dump(exclude_none=True)
    if "timezone" in update_data:
        update_data["timezone"] = update_data.pop("timezone")

    job = crud.update_scheduled_job(db, schedule_id, **update_data)
    if not job:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    return crud._build_schedule_summary(job)


@router.delete("/schedules/{schedule_id}", status_code=204, tags=["schedules"])
def delete_schedule(
    schedule_id: UUID,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_permission(PERM_RUN_AUTOMATIONS)),
):
    deleted = crud.delete_scheduled_job(db, schedule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
