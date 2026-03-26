"""Background workers that consume RabbitMQ and persist data."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from uuid import UUID

import aio_pika
from aio_pika import IncomingMessage

from ..config import get_settings
from ..database import session_scope
from .. import crud, schemas


logger = logging.getLogger("remote_api.workers")
Handler = Callable[[dict], Awaitable[None]]


def _parse_json(message: IncomingMessage) -> dict:
    return json.loads(message.body.decode("utf-8"))


class WorkerService:
    def __init__(self):
        self.settings = get_settings()
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.abc.AbstractRobustChannel | None = None
        self._tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        self._connection = await aio_pika.connect_robust(self.settings.rabbitmq_url)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=256)

        self._tasks = [
            asyncio.create_task(
                self._consume(self.settings.queue_instances, self._handle_instance)
            ),
            asyncio.create_task(
                self._consume(self.settings.queue_runs, self._handle_run)
            ),
            asyncio.create_task(
                self._consume(self.settings.queue_logs, self._handle_logs)
            ),
            asyncio.create_task(
                self._consume(self.settings.queue_snapshots, self._handle_snapshot)
            ),
        ]
        logger.info("Workers started. Awaiting messages...")
        await asyncio.gather(*self._tasks)

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        if self._channel and not self._channel.is_closed:
            await self._channel.close()
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
        logger.info("Workers stopped.")

    async def _consume(self, queue_name: str, handler: Handler) -> None:
        assert self._channel is not None
        queue = await self._channel.declare_queue(queue_name, durable=True)
        async with queue.iterator() as iterator:
            async for message in iterator:
                try:
                    payload = _parse_json(message)
                    await handler(payload)
                except ValueError as exc:
                    logger.warning("Dropping invalid %s message: %s", queue_name, exc)
                    await message.ack()
                except Exception as exc:  # pragma: no cover - runtime errors
                    if message.redelivered:
                        logger.exception(
                            "Dropping poison %s message after retry",
                            queue_name,
                            exc_info=exc,
                        )
                        await message.reject(requeue=False)
                    else:
                        logger.exception(
                            "Error handling %s message. Requeueing once.",
                            queue_name,
                            exc_info=exc,
                        )
                        await message.reject(requeue=True)
                else:
                    await message.ack()

    async def _handle_instance(self, envelope: dict):
        data = schemas.AutomationInstanceRequest(**envelope["payload"])

        def _persist():
            with session_scope() as session:
                crud.get_or_create_instance(session, data)

        await asyncio.to_thread(_persist)
        logger.debug("Processed automation instance event.")

    async def _handle_run(self, envelope: dict):
        event = envelope.get("event")
        payload = envelope["payload"]

        if event == "run.started":
            data = schemas.RunCreateRequest(**payload)

            def _persist():
                with session_scope() as session:
                    instance_id = data.automation_instance_id
                    if instance_id is None and data.instance is not None:
                        instance = crud.get_or_create_instance(session, data.instance)
                        instance_id = instance.id
                    crud.create_run(session, data, automation_instance_id=instance_id)

            await asyncio.to_thread(_persist)
            logger.debug("Stored run start %s", data.run_id)
        elif event == "run.updated":
            data = schemas.RunUpdateRequest(**payload)

            def _persist():
                with session_scope() as session:
                    crud.update_run(session, data.run_id, data)

            await asyncio.to_thread(_persist)
            logger.debug("Updated run %s", data.run_id)
        else:
            logger.warning("Unknown run event: %s", event)

    async def _handle_logs(self, envelope: dict):
        data = schemas.LogBatchRequest(**envelope["payload"])

        def _persist():
            with session_scope() as session:
                crud.insert_log_entries(session, data.run_id, data.entries)

        await asyncio.to_thread(_persist)
        logger.debug("Stored %d log entries for run %s", len(data.entries), data.run_id)

    async def _handle_snapshot(self, envelope: dict):
        payload = envelope["payload"]
        run_id = UUID(payload["run_id"])
        snapshot = schemas.SnapshotRequest(**{k: v for k, v in payload.items() if k != "run_id"})

        def _persist():
            with session_scope() as session:
                crud.create_snapshot(session, run_id, snapshot)

        await asyncio.to_thread(_persist)
        logger.debug("Stored snapshot for run %s", run_id)
