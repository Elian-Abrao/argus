"""RabbitMQ publisher used by the API to enqueue events."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, Iterable

import aio_pika
from aio_pika import Message, DeliveryMode
from fastapi import Request

from .config import get_settings


def _json_default(value: Any):
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _serialize(payload: Any) -> bytes:
    return json.dumps(payload, default=_json_default, ensure_ascii=False).encode("utf-8")


class RabbitPublisher:
    """Wrapper around aio-pika to publish JSON payloads."""

    def __init__(self, queues: Iterable[str], url: str):
        self._queues = list(queues)
        self._url = url
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        async with self._lock:
            if self._connection and not self._connection.is_closed:
                return
            self._connection = await aio_pika.connect_robust(self._url)
            self._channel = await self._connection.channel()
            await self._channel.set_qos(prefetch_count=256)
            for queue_name in self._queues:
                await self._channel.declare_queue(queue_name, durable=True)

    async def close(self) -> None:
        async with self._lock:
            if self._channel and not self._channel.is_closed:
                await self._channel.close()
            if self._connection and not self._connection.is_closed:
                await self._connection.close()
            self._channel = None
            self._connection = None

    async def publish(self, queue_name: str, payload: Any) -> None:
        if not self._channel or self._channel.is_closed:
            await self.connect()
        assert self._channel is not None  # for type checkers
        message = Message(
            body=_serialize(payload),
            delivery_mode=DeliveryMode.PERSISTENT,
            content_type="application/json",
        )
        await self._channel.default_exchange.publish(
            message, routing_key=queue_name
        )


def create_publisher() -> RabbitPublisher:
    settings = get_settings()
    queues = {
        settings.queue_instances,
        settings.queue_runs,
        settings.queue_logs,
        settings.queue_snapshots,
    }
    return RabbitPublisher(queues=queues, url=settings.rabbitmq_url)


def get_publisher(request: Request) -> RabbitPublisher:
    publisher: RabbitPublisher | None = getattr(request.app.state, "publisher", None)
    if publisher is None:
        raise RuntimeError("Publisher not initialized")
    return publisher
