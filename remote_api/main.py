"""FastAPI application factory."""

import asyncio
import contextlib
import logging
from datetime import datetime, timedelta

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

from .config import get_settings
from .routes import get_api_router
from .messaging import create_publisher
from .email_schema import ensure_email_schema
from .control_schema import ensure_control_schema
from .auth_schema import ensure_auth_schema
from .retention import cleanup_expired_email_data, stop_stale_running_runs
from .database import ensure_database_schema


logger = logging.getLogger("remote_api.main")


class ForwardedHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        proto = request.headers.get("x-forwarded-proto")
        if proto:
            request.scope["scheme"] = proto
        host = request.headers.get("x-forwarded-host")
        if host:
            server = request.scope.get("server")
            port = server[1] if server else 80
            request.scope["server"] = (host, port)
        return await call_next(request)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    app.add_middleware(ForwardedHeadersMiddleware)
    app.include_router(get_api_router(), prefix=settings.api_prefix)

    publisher = create_publisher()
    app.state.publisher = publisher
    retention_task: asyncio.Task | None = None
    stale_runs_task: asyncio.Task | None = None
    schedule_checker_task: asyncio.Task | None = None
    command_expiry_task: asyncio.Task | None = None

    async def _run_retention_loop() -> None:
        interval_seconds = max(60, int(settings.email_retention_cleanup_interval_seconds))
        batch_size = max(1, int(settings.email_retention_cleanup_batch_size))
        while True:
            try:
                await asyncio.to_thread(
                    cleanup_expired_email_data,
                    batch_size=batch_size,
                )
            except Exception:  # pragma: no cover - best effort loop
                logger.exception("Falha durante cleanup de retenção de e-mails")
            await asyncio.sleep(interval_seconds)

    async def _run_stale_runs_loop() -> None:
        interval_seconds = max(60, int(settings.run_stale_cleanup_interval_seconds))
        batch_size = max(1, int(settings.run_stale_cleanup_batch_size))
        stale_after_hours = max(1 / 60, float(settings.run_stale_timeout_hours))
        while True:
            try:
                await asyncio.to_thread(
                    stop_stale_running_runs,
                    stale_after_hours=stale_after_hours,
                    batch_size=batch_size,
                )
            except Exception:  # pragma: no cover - best effort loop
                logger.exception("Falha durante auto-stop de runs sem logs")
            await asyncio.sleep(interval_seconds)

    async def _run_schedule_checker_loop() -> None:
        from .database import session_scope
        from . import crud
        from .ws_manager import manager
        from .routes.agent_ws import _serialize_command
        from datetime import timezone as tz

        interval = max(30, int(settings.schedule_checker_interval_seconds))
        while True:
            try:
                created_commands = await asyncio.to_thread(_check_and_dispatch_schedules)
                for host_id, cmd_payload in created_commands:
                    await manager.send_command(host_id, cmd_payload)
            except Exception:
                logger.exception("Falha no verificador de agendamentos")
            await asyncio.sleep(interval)

    def _check_and_dispatch_schedules() -> list:
        from .database import session_scope
        from . import crud
        from .routes.agent_ws import _serialize_command
        from datetime import timezone as tz

        results = []
        with session_scope() as session:
            due_jobs = crud.list_due_schedules(session)
            now_utc = datetime.now(tz.utc)
            minute_start = now_utc.replace(second=0, microsecond=0)
            minute_end = minute_start + timedelta(seconds=60)

            for job in due_jobs:
                # Prevent duplicate dispatch
                if crud.schedule_already_dispatched(session, job.id, minute_start, minute_end):
                    continue

                inst = job.automation_instance
                if not inst or not inst.host:
                    continue

                # For sequential mode, skip if host has running commands
                if job.execution_mode == "sequential":
                    if crud.has_running_commands_on_host(session, inst.host_id):
                        continue

                cmd = crud.create_command(
                    session,
                    host_id=inst.host_id,
                    automation_instance_id=inst.id,
                    scheduled_job_id=job.id,
                    script=job.script,
                    args=job.args or [],
                    working_dir=inst.host.root_folder,
                    execution_mode=job.execution_mode,
                    created_by="scheduler",
                )
                results.append((inst.host_id, _serialize_command(cmd)))
        return results

    async def _run_command_expiry_loop() -> None:
        from .database import session_scope
        from . import crud

        interval = max(60, int(settings.command_expiry_interval_seconds))
        expiry_hours = max(1, int(settings.command_expiry_hours))
        while True:
            try:
                await asyncio.to_thread(_expire_commands, expiry_hours)
            except Exception:
                logger.exception("Falha na expiração de comandos")
            await asyncio.sleep(interval)

    def _expire_commands(expiry_hours: int) -> None:
        from .database import session_scope
        from . import crud

        with session_scope() as session:
            count = crud.expire_old_pending_commands(session, older_than_hours=expiry_hours)
            if count:
                logger.info("Expirados %d comandos pendentes", count)

    @app.on_event("startup")
    async def _startup():
        nonlocal retention_task, stale_runs_task, schedule_checker_task, command_expiry_task
        ensure_database_schema()
        ensure_auth_schema()
        ensure_email_schema()
        ensure_control_schema()
        # Additive migration: display_name column for hosts
        from sqlalchemy import text
        from .database import engine
        with engine.begin() as conn:
            conn.execute(text(
                "ALTER TABLE hosts ADD COLUMN IF NOT EXISTS display_name text"
            ))
        await publisher.connect()
        if settings.email_retention_cleanup_enabled:
            retention_task = asyncio.create_task(_run_retention_loop())
        if settings.run_stale_cleanup_enabled:
            stale_runs_task = asyncio.create_task(_run_stale_runs_loop())
        if settings.schedule_checker_enabled:
            schedule_checker_task = asyncio.create_task(_run_schedule_checker_loop())
        command_expiry_task = asyncio.create_task(_run_command_expiry_loop())

    @app.on_event("shutdown")
    async def _shutdown():
        nonlocal retention_task, stale_runs_task, schedule_checker_task, command_expiry_task
        for task in (retention_task, stale_runs_task, schedule_checker_task, command_expiry_task):
            if task:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
        retention_task = stale_runs_task = schedule_checker_task = command_expiry_task = None
        await publisher.close()

    return app


app = create_app()
