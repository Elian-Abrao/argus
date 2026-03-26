"""Routes for registering automation instances."""

from fastapi import APIRouter, Depends, status
from datetime import datetime

from ..messaging import get_publisher, RabbitPublisher
from ..schemas import AutomationInstanceRequest, AckResponse
from ..config import get_settings


router = APIRouter()
settings = get_settings()


@router.post("/instances", response_model=AckResponse, status_code=status.HTTP_202_ACCEPTED)
async def register_instance(
    payload: AutomationInstanceRequest,
    publisher: RabbitPublisher = Depends(get_publisher),
):
    message = {
        "event": "automation_instance.registered",
        "received_at": datetime.utcnow().isoformat(),
        "payload": payload.dict(),
    }
    await publisher.publish(settings.queue_instances, message)
    return AckResponse()
