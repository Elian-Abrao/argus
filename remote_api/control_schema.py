"""DDL bootstrap for remote control tables (scheduled_jobs, commands)."""

from __future__ import annotations

from sqlalchemy import text

from .database import engine


def ensure_control_schema() -> None:
    """Creates remote control tables/indexes and adds new columns when missing."""
    statements = [
        # -- New columns on existing tables --
        """
        ALTER TABLE hosts
            ADD COLUMN IF NOT EXISTS last_agent_ping timestamptz
        """,
        """
        ALTER TABLE automation_instances
            ADD COLUMN IF NOT EXISTS script text NOT NULL DEFAULT 'main.py'
        """,
        """
        ALTER TABLE automation_instances
            ADD COLUMN IF NOT EXISTS default_args jsonb NOT NULL DEFAULT '[]'::jsonb
        """,
        """
        ALTER TABLE automation_instances
            ADD COLUMN IF NOT EXISTS available_args jsonb NOT NULL DEFAULT '[]'::jsonb
        """,
        # -- scheduled_jobs --
        """
        CREATE TABLE IF NOT EXISTS scheduled_jobs (
            id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            automation_instance_id  uuid NOT NULL REFERENCES automation_instances(id),
            script                  text NOT NULL DEFAULT 'main.py',
            args                    jsonb NOT NULL DEFAULT '[]'::jsonb,
            recurrence_type         text NOT NULL,
            recurrence_config       jsonb NOT NULL DEFAULT '{}'::jsonb,
            execution_mode          text NOT NULL DEFAULT 'parallel',
            enabled                 boolean NOT NULL DEFAULT true,
            timezone                text NOT NULL DEFAULT 'America/Sao_Paulo',
            created_at              timestamptz NOT NULL DEFAULT now(),
            updated_at              timestamptz NOT NULL DEFAULT now()
        )
        """,
        "CREATE INDEX IF NOT EXISTS scheduled_jobs_instance_idx ON scheduled_jobs (automation_instance_id)",
        "CREATE INDEX IF NOT EXISTS scheduled_jobs_enabled_idx ON scheduled_jobs (enabled) WHERE enabled = true",
        # -- commands --
        """
        CREATE TABLE IF NOT EXISTS commands (
            id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            host_id                 uuid NOT NULL REFERENCES hosts(id),
            automation_instance_id  uuid NOT NULL REFERENCES automation_instances(id),
            scheduled_job_id        uuid REFERENCES scheduled_jobs(id) ON DELETE SET NULL,
            script                  text NOT NULL DEFAULT 'main.py',
            args                    jsonb NOT NULL DEFAULT '[]'::jsonb,
            working_dir             text NOT NULL,
            execution_mode          text NOT NULL DEFAULT 'parallel',
            status                  text NOT NULL DEFAULT 'pending',
            run_id                  uuid REFERENCES runs(id),
            created_by              text NOT NULL DEFAULT 'user',
            created_at              timestamptz NOT NULL DEFAULT now(),
            acked_at                timestamptz,
            started_at              timestamptz,
            finished_at             timestamptz,
            result_message          text
        )
        """,
        "CREATE INDEX IF NOT EXISTS commands_host_status_idx ON commands (host_id, status)",
        "CREATE INDEX IF NOT EXISTS commands_instance_idx ON commands (automation_instance_id, created_at DESC)",
    ]
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
