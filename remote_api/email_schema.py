"""DDL bootstrap for email audit tables."""

from __future__ import annotations

from sqlalchemy import text

from .database import engine


def ensure_email_schema() -> None:
    """Creates email audit tables/indexes when missing."""
    statements = [
        """
        CREATE TABLE IF NOT EXISTS email_events (
            id              uuid PRIMARY KEY,
            run_id          uuid NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
            subject         text,
            body_text       text,
            body_html       text,
            recipients      jsonb NOT NULL DEFAULT '[]'::jsonb,
            bcc_recipients  jsonb NOT NULL DEFAULT '[]'::jsonb,
            source_paths    jsonb NOT NULL DEFAULT '[]'::jsonb,
            status          text NOT NULL DEFAULT 'enviado',
            error           text,
            retention_days  integer NOT NULL DEFAULT 7,
            sent_at         timestamptz NOT NULL DEFAULT now(),
            expires_at      timestamptz NOT NULL,
            created_at      timestamptz NOT NULL DEFAULT now()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS email_attachments (
            id                uuid PRIMARY KEY,
            email_event_id    uuid NOT NULL REFERENCES email_events(id) ON DELETE CASCADE,
            filename          text NOT NULL,
            mime_type         text,
            size_bytes        bigint NOT NULL,
            storage_key       text NOT NULL,
            source_path       text,
            preview_supported boolean NOT NULL DEFAULT false,
            created_at        timestamptz NOT NULL DEFAULT now()
        )
        """,
        "CREATE INDEX IF NOT EXISTS email_events_run_idx ON email_events (run_id, sent_at DESC)",
        "CREATE INDEX IF NOT EXISTS email_events_expires_idx ON email_events (expires_at)",
        "CREATE INDEX IF NOT EXISTS email_attachments_event_idx ON email_attachments (email_event_id)",
    ]
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))

