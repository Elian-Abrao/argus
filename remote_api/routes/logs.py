"""Routes for log entries and snapshots."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, status

from ..config import get_settings
from ..messaging import get_publisher, RabbitPublisher
from ..schemas import LogBatchRequest, SnapshotRequest, AckResponse


router = APIRouter()
settings = get_settings()


@router.post("/logs/batch", response_model=AckResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_logs(
    payload: LogBatchRequest,
    publisher: RabbitPublisher = Depends(get_publisher),
):
    message = {
        "event": "logs.batch",
        "received_at": datetime.utcnow().isoformat(),
        "payload": payload.dict(),
    }
    await publisher.publish(settings.queue_logs, message)
    return AckResponse()


@router.post(
    "/runs/{run_id}/snapshots",
    response_model=AckResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_run_snapshot(
    run_id: UUID,
    payload: SnapshotRequest,
    publisher: RabbitPublisher = Depends(get_publisher),
):
    message = {
        "event": "run.snapshot",
        "received_at": datetime.utcnow().isoformat(),
        "payload": {"run_id": str(run_id), **payload.dict()},
    }
    await publisher.publish(settings.queue_snapshots, message)
    return AckResponse()
