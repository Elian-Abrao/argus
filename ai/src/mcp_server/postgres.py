from __future__ import annotations

from typing import Any

from ..config import DatabaseSettings, get_database_settings

try:
    import psycopg
except ImportError:  # pragma: no cover
    psycopg = None

try:
    import psycopg2
except ImportError:  # pragma: no cover
    psycopg2 = None


def _ensure_driver() -> None:
    if psycopg is None and psycopg2 is None:
        raise RuntimeError(
            "Nenhum driver PostgreSQL encontrado. Instale `psycopg[binary]` ou `psycopg2-binary`."
        )


def _connection_kwargs(settings: DatabaseSettings) -> dict[str, Any]:
    return {
        "host": settings.host,
        "port": settings.port,
        "dbname": settings.database or "postgres",
        "user": settings.user,
        "password": settings.password,
        "connect_timeout": 10,
    }


def _connect(settings: DatabaseSettings) -> Any:
    _ensure_driver()
    kwargs = _connection_kwargs(settings)
    if psycopg is not None:
        return psycopg.connect(**kwargs)
    return psycopg2.connect(**kwargs)


def test_connection(settings: DatabaseSettings | None = None) -> dict[str, Any]:
    current = settings or get_database_settings()

    with _connect(current) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), current_user")
            db_name, login_name = cur.fetchone()

    return {
        "connected": True,
        "host": current.host,
        "port": current.port,
        "database": db_name,
        "requestedDatabase": current.database or "postgres",
        "login": login_name,
    }


def inspect_database_access(settings: DatabaseSettings | None = None) -> dict[str, Any]:
    current = settings or get_database_settings()

    with _connect(current) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    current_database(),
                    has_database_privilege(current_user, current_database(), 'CONNECT'),
                    current_schema()
                """
            )
            database_name, has_access, current_schema = cur.fetchone()

    return {
        "database": database_name,
        "requestedDatabase": current.database or "postgres",
        "hasAccess": bool(has_access),
        "currentSchema": current_schema,
    }


__all__ = ["inspect_database_access", "test_connection"]
