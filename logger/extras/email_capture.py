"""email_capture.py - Captura automática de envios via smtplib."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from email import policy
from email.message import Message
from email.parser import BytesParser, Parser
from email.utils import getaddresses
import json
import smtplib
import threading
import weakref
from logging import Logger
from typing import Iterable, Any


def _as_recipients(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        return [addr for _, addr in getaddresses([values]) if addr]
    if isinstance(values, Iterable):
        pairs = getaddresses([str(item) for item in values])
        return [addr for _, addr in pairs if addr]
    return [str(values)]


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    items: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        items.append(value)
    return items


def _parse_message(msg: Any) -> Message:
    if isinstance(msg, Message):
        return msg
    if isinstance(msg, (bytes, bytearray)):
        return BytesParser(policy=policy.default).parsebytes(bytes(msg))
    return Parser(policy=policy.default).parsestr(str(msg))


def _decode_text_part(part: Message) -> str:
    payload = part.get_payload(decode=True)
    if payload is None:
        data = part.get_payload()
        return data if isinstance(data, str) else ""
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except LookupError:
        return payload.decode("utf-8", errors="replace")


def _extract_bodies(message: Message) -> tuple[str | None, str | None]:
    plain_parts: list[str] = []
    html_parts: list[str] = []

    if message.is_multipart():
        for part in message.walk():
            if part.is_multipart():
                continue
            if (part.get_content_disposition() or "").lower() == "attachment":
                continue
            content_type = (part.get_content_type() or "").lower()
            text = _decode_text_part(part).strip()
            if not text:
                continue
            if content_type == "text/plain":
                plain_parts.append(text)
            elif content_type == "text/html":
                html_parts.append(text)
    else:
        content_type = (message.get_content_type() or "").lower()
        text = _decode_text_part(message).strip()
        if content_type == "text/html":
            html_parts.append(text)
        else:
            plain_parts.append(text)

    plain = "\n\n".join(part for part in plain_parts if part) or None
    html = "\n\n".join(part for part in html_parts if part) or None
    return plain, html


def _extract_attachment_paths(message: Message) -> list[str]:
    attachments: list[str] = []
    for part in message.walk():
        if part.is_multipart():
            continue
        filename = part.get_filename()
        disposition = (part.get_content_disposition() or "").lower()
        if disposition == "attachment" or filename:
            if filename:
                attachments.append(str(filename))
    return attachments


def _extract_attachments(message: Message) -> list[dict[str, Any]]:
    attachments: list[dict[str, Any]] = []
    for part in message.walk():
        if part.is_multipart():
            continue
        filename = part.get_filename()
        disposition = (part.get_content_disposition() or "").lower()
        if disposition != "attachment" and not filename:
            continue
        payload = part.get_payload(decode=True) or b""
        content_type = part.get_content_type() or "application/octet-stream"
        attachments.append(
            {
                "filename": str(filename or "anexo.bin"),
                "source_path": str(filename or "anexo.bin"),
                "content_type": content_type,
                "content": payload,
            }
        )
    return attachments


def _truncate(value: str | None, max_chars: int) -> str | None:
    if value is None:
        return None
    if max_chars <= 0 or len(value) <= max_chars:
        return value
    remaining = len(value) - max_chars
    return f"{value[:max_chars]}... [truncado +{remaining} chars]"


class EmailCapture:
    """Intercepta sendmail/send_message e registra os dados no logger."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._local = threading.local()
        self._loggers: "weakref.WeakSet[Logger]" = weakref.WeakSet()
        self._settings: "weakref.WeakKeyDictionary[Logger, dict[str, Any]]" = weakref.WeakKeyDictionary()
        self._original_sendmail = None
        self._original_send_message = None
        self._patched_sendmail = None
        self._patched_send_message = None

    def start_capture(self, logger: Logger, *, include_body: bool = True, max_body_chars: int = 12000) -> None:
        with self._lock:
            self._loggers.add(logger)
            self._settings[logger] = {
                "include_body": bool(include_body),
                "max_body_chars": max(0, int(max_body_chars)),
            }
            self._ensure_patched()

    def stop_capture(self, logger: Logger | None = None) -> None:
        with self._lock:
            if logger is not None:
                try:
                    self._loggers.remove(logger)
                except KeyError:
                    pass
                self._settings.pop(logger, None)
            else:
                self._loggers.clear()
                self._settings = weakref.WeakKeyDictionary()
            if not list(self._loggers):
                self._restore_originals()

    def _ensure_patched(self) -> None:
        if self._patched_sendmail is None or smtplib.SMTP.sendmail is not self._patched_sendmail:
            self._original_sendmail = smtplib.SMTP.sendmail

            def _patched_sendmail(instance, from_addr, to_addrs, msg, *args, **kwargs):
                return self._call_sendmail(instance, from_addr, to_addrs, msg, *args, **kwargs)

            smtplib.SMTP.sendmail = _patched_sendmail
            self._patched_sendmail = _patched_sendmail

        if self._patched_send_message is None or smtplib.SMTP.send_message is not self._patched_send_message:
            self._original_send_message = smtplib.SMTP.send_message

            def _patched_send_message(instance, msg, from_addr=None, to_addrs=None, *args, **kwargs):
                return self._call_send_message(instance, msg, from_addr=from_addr, to_addrs=to_addrs, *args, **kwargs)

            smtplib.SMTP.send_message = _patched_send_message
            self._patched_send_message = _patched_send_message

    def _restore_originals(self) -> None:
        if self._patched_sendmail and smtplib.SMTP.sendmail is self._patched_sendmail and self._original_sendmail:
            smtplib.SMTP.sendmail = self._original_sendmail
        if self._patched_send_message and smtplib.SMTP.send_message is self._patched_send_message and self._original_send_message:
            smtplib.SMTP.send_message = self._original_send_message
        self._patched_sendmail = None
        self._patched_send_message = None
        self._original_sendmail = None
        self._original_send_message = None

    def _call_sendmail(self, instance, from_addr, to_addrs, msg, *args, **kwargs):
        original = self._original_sendmail
        if original is None:
            raise RuntimeError("sendmail original não disponível")
        if getattr(self._local, "inside_capture", False):
            return original(instance, from_addr, to_addrs, msg, *args, **kwargs)
        self._local.inside_capture = True
        try:
            try:
                result = original(instance, from_addr, to_addrs, msg, *args, **kwargs)
            except Exception as exc:
                self._log_event(from_addr, to_addrs, msg, status="falha", error=str(exc))
                raise
            else:
                self._log_event(from_addr, to_addrs, msg, status="enviado")
                return result
        finally:
            self._local.inside_capture = False

    def _call_send_message(self, instance, msg, from_addr=None, to_addrs=None, *args, **kwargs):
        original = self._original_send_message
        if original is None:
            raise RuntimeError("send_message original não disponível")
        if getattr(self._local, "inside_capture", False):
            return original(instance, msg, from_addr=from_addr, to_addrs=to_addrs, *args, **kwargs)
        self._local.inside_capture = True
        try:
            try:
                result = original(instance, msg, from_addr=from_addr, to_addrs=to_addrs, *args, **kwargs)
            except Exception as exc:
                self._log_event(from_addr, to_addrs, msg, status="falha", error=str(exc))
                raise
            else:
                self._log_event(from_addr, to_addrs, msg, status="enviado")
                return result
        finally:
            self._local.inside_capture = False

    def _log_event(self, from_addr: Any, to_addrs: Any, message_obj: Any, *, status: str, error: str | None = None) -> None:
        loggers = list(self._loggers)
        if not loggers:
            return

        message = _parse_message(message_obj)
        subject = str(message.get("Subject", "")).strip()

        header_to = _as_recipients(message.get_all("To", []))
        header_cc = _as_recipients(message.get_all("Cc", []))
        header_bcc = _as_recipients(message.get_all("Bcc", []))
        envelope_recipients = _as_recipients(to_addrs)

        base_recipients = set(header_to + header_cc)
        inferred_bcc = [addr for addr in envelope_recipients if addr not in base_recipients]
        bcc = _unique(header_bcc + inferred_bcc)
        destinatarios = _unique(header_to or [addr for addr in envelope_recipients if addr not in bcc])

        plain_body, html_body = _extract_bodies(message)
        attachment_paths = _extract_attachment_paths(message)
        attachment_items = _extract_attachments(message)
        sent_at = datetime.now(timezone.utc).isoformat()

        payload: dict[str, Any] = {
            "from": str(from_addr) if from_addr else "",
            "destinatarios": destinatarios,
            "destinatarios_copia_oculta": bcc,
            "assunto": subject,
            "paths_arquivos": attachment_paths,
            "status": status,
        }

        if error:
            payload["erro"] = error

        for logger in loggers:
            logger_settings = self._settings.get(
                logger,
                {"include_body": True, "max_body_chars": 12000},
            )
            include_body = bool(logger_settings.get("include_body", True))
            max_body_chars = int(logger_settings.get("max_body_chars", 12000))

            logger_payload = dict(payload)
            if include_body:
                logger_payload["corpo"] = {
                    "texto": _truncate(plain_body, max_body_chars),
                    "html": _truncate(html_body, max_body_chars),
                }

            serialized = json.dumps(logger_payload, ensure_ascii=False, default=str)
            logger.info("EMAIL_CAPTURE %s", serialized, extra={"plain": True})
            remote_sink = getattr(logger, "_remote_sink", None)
            if remote_sink and hasattr(remote_sink, "send_email_event"):
                try:
                    remote_sink.send_email_event(
                        {
                            "subject": subject,
                            "body_text": plain_body,
                            "body_html": html_body,
                            "recipients": destinatarios,
                            "bcc_recipients": bcc,
                            "source_paths": attachment_paths,
                            "status": status,
                            "error": error,
                            "sent_at": sent_at,
                        },
                        attachments=attachment_items,
                    )
                except Exception:
                    logger.warning(
                        "Falha ao enviar auditoria de email para API remota",
                        extra={"plain": True, "_remote_sink_skip": True},
                    )


email_capture = EmailCapture()


def logger_capture_emails(
    self: Logger,
    active: bool = True,
    *,
    include_body: bool = True,
    max_body_chars: int = 12000,
) -> None:
    if active:
        email_capture.start_capture(
            self,
            include_body=include_body,
            max_body_chars=max_body_chars,
        )
    else:
        email_capture.stop_capture(self)


@contextmanager
def capture_emails(
    self: Logger,
    *,
    include_body: bool = True,
    max_body_chars: int = 12000,
):
    email_capture.start_capture(
        self,
        include_body=include_body,
        max_body_chars=max_body_chars,
    )
    try:
        yield
    finally:
        email_capture.stop_capture(self)
