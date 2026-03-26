"""Storage helpers for email attachments."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from threading import Lock

from minio import Minio
from minio.error import S3Error

from .config import get_settings


@dataclass
class StoredObjectInfo:
    storage_key: str
    size_bytes: int
    content_type: str


class MinioAttachmentStorage:
    """Simple wrapper around MinIO for attachment persistence."""

    def __init__(self) -> None:
        settings = get_settings()
        self.bucket = settings.minio_bucket
        self._client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self._ready = False
        self._lock = Lock()

    def _ensure_bucket(self) -> None:
        if self._ready:
            return
        with self._lock:
            if self._ready:
                return
            if not self._client.bucket_exists(self.bucket):
                self._client.make_bucket(self.bucket)
            self._ready = True

    def put_bytes(
        self,
        *,
        storage_key: str,
        payload: bytes,
        content_type: str,
    ) -> StoredObjectInfo:
        self._ensure_bucket()
        stream = BytesIO(payload)
        self._client.put_object(
            bucket_name=self.bucket,
            object_name=storage_key,
            data=stream,
            length=len(payload),
            content_type=content_type or "application/octet-stream",
        )
        return StoredObjectInfo(
            storage_key=storage_key,
            size_bytes=len(payload),
            content_type=content_type or "application/octet-stream",
        )

    def get_stream(self, storage_key: str):
        self._ensure_bucket()
        return self._client.get_object(self.bucket, storage_key)

    def remove(self, storage_key: str) -> None:
        self._ensure_bucket()
        try:
            self._client.remove_object(self.bucket, storage_key)
        except S3Error:
            return


storage = MinioAttachmentStorage()

