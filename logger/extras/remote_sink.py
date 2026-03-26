"""Remote sink handler that forwards logs to the ingestion API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import queue
import socket
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

import requests


RemoteLogger = logging.getLogger("logger.remote_sink")
RemoteLogger.propagate = False

_EMAIL_EVENT_MAX_ATTEMPTS = 6
_EMAIL_EVENT_RETRY_BASE_SECONDS = 0.25
_BOOTSTRAP_RETRY_SECONDS = 1.0

_QUEUE_KIND_LOG = "log"
_QUEUE_KIND_EMAIL = "email"
_QUEUE_KIND_STOP = "_stop"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_ip() -> Optional[str]:
    try:
        return socket.gethostbyname(socket.gethostname())
    except OSError:
        return None


def _sanitize_endpoint(endpoint: str) -> str:
    return endpoint.rstrip("/")


@dataclass
class RemoteSinkSettings:
    endpoint: str
    api_key: Optional[str]
    batch_size: int = 50
    flush_interval: float = 1.0
    automation: Mapping[str, Any] = None  # type: ignore[assignment]
    client: Mapping[str, Any] | None = None
    host: Mapping[str, Any] | None = None
    deployment_tag: Optional[str] = None
    config_signature: Optional[str] = None
    server_mode: bool = False
    email_retention_days: int | None = None

    def __post_init__(self) -> None:
        if not self.automation:
            self.automation = {}
        if not self.host:
            self.host = {}
        if self.email_retention_days is not None:
            try:
                value = int(self.email_retention_days)
            except (TypeError, ValueError):
                value = 0
            self.email_retention_days = value if value > 0 else None


class RemoteSinkHandler(logging.Handler):
    """Logging handler that forwards records to RemoteSink."""

    def __init__(self, sink: "RemoteSink") -> None:
        super().__init__(level=logging.NOTSET)
        self.sink = sink

    def emit(self, record: logging.LogRecord) -> None:
        if getattr(record, "_remote_sink_skip", False):
            return
        try:
            self.sink.enqueue(record)
        except Exception:  # pragma: no cover - best effort
            RemoteLogger.exception("Falha ao enfileirar log remoto")


class RemoteSink:
    """Manages communication with the remote ingestion API."""

    def __init__(self, settings: RemoteSinkSettings) -> None:
        self.settings = settings
        self.endpoint = _sanitize_endpoint(settings.endpoint)
        self.session = requests.Session()
        if settings.api_key:
            self.session.headers.update({"X-API-Key": settings.api_key})

        self.queue: queue.Queue[dict[str, Any]] = queue.Queue()
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.stop_event = threading.Event()

        self.seq = 0
        self.instance_payload = self._build_instance_payload()
        self.run_id = uuid.uuid4()
        self.instance_id = self.instance_payload["instance_id"]

        self._run_bootstrapped = False
        self._final_status = "completed"

    def start(self) -> None:
        """Starts background worker (bootstrap happens asynchronously)."""
        self.thread.start()

    def finalize(self, status: str = "completed") -> None:
        """Signals shutdown without blocking robot execution."""
        self._final_status = status or "completed"
        self.stop_event.set()
        self.queue.put({"kind": _QUEUE_KIND_STOP})
        self.thread.join(timeout=1.0)

    def enqueue(self, record: logging.LogRecord) -> None:
        entry = self._record_to_entry(record)
        self.queue.put({"kind": _QUEUE_KIND_LOG, "entry": entry})

    def send_email_event(
        self,
        event_payload: Mapping[str, Any],
        attachments: Iterable[Mapping[str, Any]] | None = None,
    ) -> None:
        payload = dict(event_payload)
        if (
            payload.get("retention_days") is None
            and self.settings.email_retention_days
            and self.settings.email_retention_days > 0
        ):
            payload["retention_days"] = int(self.settings.email_retention_days)

        self.queue.put(
            {
                "kind": _QUEUE_KIND_EMAIL,
                "payload": payload,
                "attachments": list(attachments or []),
            }
        )

    # ------------------------------------------------------------------ helpers
    def _build_instance_payload(self) -> dict[str, Any]:
        automation = dict(self.settings.automation)
        automation.setdefault("code", automation.get("name") or "Automation")
        automation.setdefault("name", automation.get("code"))

        host_info = dict(self.settings.host or {})
        host_info.setdefault("hostname", socket.gethostname())
        host_info.setdefault("ip_address", _safe_ip())
        host_info.setdefault("root_folder", str(Path.cwd()))

        client_info = dict(self.settings.client or {})
        fingerprint = "|".join(
            filter(
                None,
                [
                    automation.get("code"),
                    client_info.get("external_code") or client_info.get("name"),
                    host_info.get("ip_address"),
                    host_info.get("root_folder"),
                    self.settings.deployment_tag or "",
                ],
            )
        )
        instance_id = uuid.uuid5(uuid.NAMESPACE_URL, fingerprint or automation["code"])
        return {
            "instance_id": str(instance_id),
            "automation": automation,
            "client": client_info or None,
            "host": host_info,
            "deployment_tag": self.settings.deployment_tag,
            "config_signature": self.settings.config_signature,
            "metadata": {},
        }

    def _record_to_entry(self, record: logging.LogRecord) -> dict[str, Any]:
        self.seq += 1
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()
        context: dict[str, Any] = {}
        if hasattr(record, "context") and record.context:
            context["context"] = record.context
        if hasattr(record, "call_chain") and record.call_chain:
            context["call_chain"] = record.call_chain
        if record.threadName != "MainThread":
            context["thread"] = record.threadName
        if record.pathname:
            context["pathname"] = record.pathname
            context["lineno"] = record.lineno
        extra: dict[str, Any] = {}
        if hasattr(record, "plain"):
            extra["plain"] = record.plain
        if hasattr(record, "file_only"):
            extra["file_only"] = record.file_only
        if record.exc_info:
            formatter = logging.Formatter()
            extra["exception"] = formatter.formatException(record.exc_info)

        message = record.getMessage()
        if extra.get("exception"):
            message = f"{message}\n{extra['exception']}"

        return {
            "sequence": self.seq,
            "ts": ts,
            "level": record.levelname,
            "message": message,
            "logger_name": record.name,
            "context": context,
            "extra": extra,
        }

    # ---------------------------------------------------------------- worker
    def _worker(self) -> None:
        self._run_bootstrapped = self._wait_until_bootstrap()

        batch: list[dict[str, Any]] = []
        last_flush = time.monotonic()
        interval = max(self.settings.flush_interval, 0.1)

        while True:
            timeout = max(0, interval - (time.monotonic() - last_flush))
            try:
                item = self.queue.get(timeout=timeout)
            except queue.Empty:
                item = None

            if item and item.get("kind") == _QUEUE_KIND_STOP:
                break

            if item and item.get("kind") == _QUEUE_KIND_LOG:
                entry = item.get("entry")
                if isinstance(entry, dict):
                    batch.append(entry)
                    if len(batch) >= self.settings.batch_size:
                        self._flush_batch(batch)
                        batch.clear()
                        last_flush = time.monotonic()
                continue

            if item and item.get("kind") == _QUEUE_KIND_EMAIL:
                if batch:
                    self._flush_batch(batch)
                    batch.clear()
                self._send_email_event_now(
                    event_payload=item.get("payload") or {},
                    attachments=item.get("attachments"),
                )
                last_flush = time.monotonic()
                continue

            if item is None:
                if batch:
                    self._flush_batch(batch)
                    batch.clear()
                last_flush = time.monotonic()

        if batch:
            self._flush_batch(batch)

        if self._run_bootstrapped:
            try:
                self._send_run_update(self._final_status)
            except Exception as exc:  # pragma: no cover - best effort
                RemoteLogger.warning(
                    "Falha ao atualizar status final da run remota: %s",
                    exc,
                    extra={"_remote_sink_skip": True},
                )

    def _wait_until_bootstrap(self) -> bool:
        while not self.stop_event.is_set():
            if self._bootstrap_run_once():
                return True
            time.sleep(_BOOTSTRAP_RETRY_SECONDS)
        return False

    def _bootstrap_run_once(self) -> bool:
        try:
            self._send_instance()
            self._send_run_start()
            return True
        except Exception as exc:  # pragma: no cover - best effort
            RemoteLogger.warning(
                "Falha ao registrar contexto remoto (run/instance): %s",
                exc,
                extra={"_remote_sink_skip": True},
            )
            return False

    # ---------------------------------------------------------------- HTTP calls
    def _send_instance(self) -> None:
        payload = {
            "instance_id": self.instance_payload["instance_id"],
            "automation": self.instance_payload["automation"],
            "client": self.instance_payload["client"],
            "host": self.instance_payload["host"],
            "deployment_tag": self.instance_payload["deployment_tag"],
            "config_signature": self.instance_payload["config_signature"],
        }
        self._post("/ingest/instances", payload)

    def _send_run_start(self) -> None:
        metadata: dict[str, Any] = {}
        if self.settings.email_retention_days and self.settings.email_retention_days > 0:
            metadata["email_retention_days"] = int(self.settings.email_retention_days)
        payload = {
            "run_id": str(self.run_id),
            "automation_instance_id": self.instance_payload["instance_id"],
            "instance": self.instance_payload,
            "started_at": _now_iso(),
            "server_mode": self.settings.server_mode,
            "host_ip": self.instance_payload["host"].get("ip_address"),
            "root_folder": self.instance_payload["host"].get("root_folder"),
            "metadata": metadata,
        }
        self._post("/runs", payload)

    def _send_run_update(self, status: str) -> None:
        payload = {
            "run_id": str(self.run_id),
            "status": status,
            "finished_at": _now_iso(),
        }
        self._patch("/runs", payload)

    def _flush_batch(self, batch: list[dict[str, Any]]) -> None:
        if not batch or not self._run_bootstrapped:
            return

        payload = {
            "run_id": str(self.run_id),
            "entries": batch,
        }
        try:
            self._post("/logs/batch", payload)
        except Exception as exc:  # pragma: no cover - best effort
            RemoteLogger.warning(
                "Falha ao enviar lote de logs remoto: %s",
                exc,
                extra={"_remote_sink_skip": True},
            )

    def _send_email_event_now(
        self,
        event_payload: Mapping[str, Any],
        attachments: Iterable[Mapping[str, Any]] | None = None,
    ) -> None:
        if not self._run_bootstrapped:
            return

        url = f"{self.endpoint}/runs/{self.run_id}/emails"
        payload = dict(event_payload)
        if (
            payload.get("retention_days") is None
            and self.settings.email_retention_days
            and self.settings.email_retention_days > 0
        ):
            payload["retention_days"] = int(self.settings.email_retention_days)
        try:
            email_id = self._post_email_event_with_retry(url, payload)
        except Exception as exc:  # pragma: no cover - network errors
            RemoteLogger.warning(
                "Falha ao enviar evento de email para %s: %s",
                url,
                exc,
                extra={"_remote_sink_skip": True},
            )
            return

        if not email_id:
            RemoteLogger.warning(
                "Resposta de email sem email_id em %s",
                url,
                extra={"_remote_sink_skip": True},
            )
            return

        for attachment in attachments or []:
            filename = str(attachment.get("filename") or "anexo.bin")
            content = attachment.get("content")
            if not isinstance(content, (bytes, bytearray)):
                continue
            content_type = str(attachment.get("content_type") or "application/octet-stream")
            upload_url = f"{self.endpoint}/runs/{self.run_id}/emails/{email_id}/attachments"
            files = {
                "file": (filename, bytes(content), content_type),
            }
            data: dict[str, str] = {}
            source_path = attachment.get("source_path")
            if source_path:
                data["source_path"] = str(source_path)
            try:
                resp = self.session.post(upload_url, files=files, data=data, timeout=30)
                resp.raise_for_status()
            except Exception as exc:  # pragma: no cover - network errors
                RemoteLogger.warning(
                    "Falha ao enviar anexo de email para %s: %s",
                    upload_url,
                    exc,
                    extra={"_remote_sink_skip": True},
                )

    def _post(self, path: str, payload: Mapping[str, Any]) -> None:
        url = f"{self.endpoint}{path}"
        response = self.session.post(url, json=payload, timeout=5)
        response.raise_for_status()

    def _patch(self, path: str, payload: Mapping[str, Any]) -> None:
        url = f"{self.endpoint}{path}"
        response = self.session.patch(url, json=payload, timeout=5)
        response.raise_for_status()

    def _post_email_event_with_retry(self, url: str, payload: Mapping[str, Any]) -> Any:
        last_error: Exception | None = None
        for attempt in range(1, _EMAIL_EVENT_MAX_ATTEMPTS + 1):
            try:
                response = self.session.post(url, json=payload, timeout=10)
            except Exception as exc:
                last_error = exc
                if attempt >= _EMAIL_EVENT_MAX_ATTEMPTS:
                    raise
                time.sleep(_EMAIL_EVENT_RETRY_BASE_SECONDS * attempt)
                continue

            if response.status_code != 404:
                response.raise_for_status()
                return response.json().get("email_id")

            detail = ""
            try:
                payload_json = response.json()
                if isinstance(payload_json, dict):
                    detail = str(payload_json.get("detail") or "")
            except ValueError:
                detail = response.text or ""

            # run.started é assíncrono via Rabbit; aguarda consistência antes de desistir.
            if "Run not found" in detail and attempt < _EMAIL_EVENT_MAX_ATTEMPTS:
                time.sleep(_EMAIL_EVENT_RETRY_BASE_SECONDS * attempt)
                continue

            response.raise_for_status()

        if last_error:
            raise last_error
        raise RuntimeError("Falha ao enviar evento de email remoto")


def setup_remote_sink(logger: logging.Logger, config: Mapping[str, Any]) -> None:
    settings = RemoteSinkSettings(
        endpoint=config["endpoint"],
        api_key=config.get("api_key"),
        batch_size=int(config.get("batch_size", 50)),
        flush_interval=float(config.get("flush_interval", 1.0)),
        automation=config.get("automation") or {"code": logger.name, "name": logger.name},
        client=config.get("client"),
        host=config.get("host"),
        deployment_tag=config.get("deployment_tag"),
        config_signature=config.get("config_signature"),
        server_mode=bool(getattr(logger, "_server_mode", False)),
        email_retention_days=config.get("email_retention_days"),
    )
    sink = RemoteSink(settings)
    sink.start()
    handler = RemoteSinkHandler(sink)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    setattr(logger, "_remote_sink", sink)
