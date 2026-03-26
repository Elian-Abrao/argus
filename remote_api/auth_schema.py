"""DDL bootstrap for authentication tables."""

from __future__ import annotations

from sqlalchemy import text

from .database import engine


def ensure_auth_schema() -> None:
    """Creates auth tables/indexes when missing (idempotent)."""
    statements = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            email           text NOT NULL,
            password_hash   text NOT NULL,
            full_name       text NOT NULL DEFAULT '',
            role            text NOT NULL DEFAULT 'user',
            is_active       boolean NOT NULL DEFAULT true,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now()
        )
        """,
        "CREATE UNIQUE INDEX IF NOT EXISTS users_email_uq ON users (lower(email))",
        "CREATE INDEX IF NOT EXISTS users_email_idx ON users (email)",
        """
        CREATE TABLE IF NOT EXISTS user_permissions (
            id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id     uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            permission  text NOT NULL
        )
        """,
        "CREATE UNIQUE INDEX IF NOT EXISTS user_permissions_uq ON user_permissions (user_id, permission)",
        """
        CREATE TABLE IF NOT EXISTS user_host_access (
            id      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            host_id uuid NOT NULL REFERENCES hosts(id) ON DELETE CASCADE
        )
        """,
        "CREATE UNIQUE INDEX IF NOT EXISTS user_host_access_uq ON user_host_access (user_id, host_id)",
        """
        CREATE TABLE IF NOT EXISTS user_automation_access (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id         uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            automation_id   uuid NOT NULL REFERENCES automations(id) ON DELETE CASCADE
        )
        """,
        "CREATE UNIQUE INDEX IF NOT EXISTS user_automation_access_uq ON user_automation_access (user_id, automation_id)",
        """
        CREATE TABLE IF NOT EXISTS user_client_access (
            id        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id   uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            client_id uuid NOT NULL REFERENCES clients(id) ON DELETE CASCADE
        )
        """,
        "CREATE UNIQUE INDEX IF NOT EXISTS user_client_access_uq ON user_client_access (user_id, client_id)",
        """
        CREATE TABLE IF NOT EXISTS user_sessions (
            id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id     uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_hash  text NOT NULL,
            expires_at  timestamptz NOT NULL,
            created_at  timestamptz NOT NULL DEFAULT now(),
            revoked_at  timestamptz
        )
        """,
        "CREATE UNIQUE INDEX IF NOT EXISTS user_sessions_token_uq ON user_sessions (token_hash)",
        "CREATE INDEX IF NOT EXISTS user_sessions_user_idx ON user_sessions (user_id)",
    ]
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
