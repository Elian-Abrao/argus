"""Route registration helpers."""

from fastapi import APIRouter

from . import ingest, runs, logs, insights, health, emails, schedules, commands, agent_ws, auth, admin


def get_api_router() -> APIRouter:
    router = APIRouter()
    router.include_router(health.router)
    router.include_router(auth.router)
    router.include_router(admin.router)
    router.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
    router.include_router(runs.router, prefix="/runs", tags=["runs"])
    router.include_router(logs.router, tags=["logs"])
    router.include_router(emails.router, tags=["emails"])
    router.include_router(insights.router, prefix="/insights")
    router.include_router(schedules.router, tags=["schedules"])
    router.include_router(commands.router, tags=["commands"])
    router.include_router(agent_ws.router, tags=["agent"])
    return router
