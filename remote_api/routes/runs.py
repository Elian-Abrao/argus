"""Routes related to runs lifecycle."""

from datetime import datetime
from fastapi import APIRouter, Depends, status
from ..config import get_settings
from ..messaging import get_publisher, RabbitPublisher
from ..schemas import RunCreateRequest, RunResponse, RunUpdateRequest


router = APIRouter()
settings = get_settings()


@router.post("", response_model=RunResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_run_endpoint(
    payload: RunCreateRequest,
    publisher: RabbitPublisher = Depends(get_publisher),
):
    message = {
        "event": "run.started",
        "received_at": datetime.utcnow().isoformat(),
        "payload": payload.dict(),
    }
    await publisher.publish(settings.queue_runs, message)
    return RunResponse(run_id=payload.run_id)


@router.patch("", response_model=RunResponse)
async def update_run_endpoint(
    payload: RunUpdateRequest,
    publisher: RabbitPublisher = Depends(get_publisher),
):
    message = {
        "event": "run.updated",
        "received_at": datetime.utcnow().isoformat(),
        "payload": payload.dict(),
    }
    await publisher.publish(settings.queue_runs, message)
    return RunResponse(run_id=payload.run_id)
