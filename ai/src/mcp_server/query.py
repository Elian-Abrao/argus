from __future__ import annotations

from typing import Any

from .dbhub_client import create_dbhub_client
from .postgres import inspect_database_access, test_connection


def execute_sql_query(sql: str) -> dict[str, Any]:
    client = create_dbhub_client()
    client.initialize()
    return client.call_tool("execute_sql", {"sql": sql})


def _build_fallback_payload(question: str, dbhub_error: str) -> dict[str, Any]:
    connection = test_connection()
    access = inspect_database_access()
    return {
        "source": "postgres-diagnostics",
        "question": question,
        "summary": (
            "DBHub is unavailable or returned an error. Current output contains "
            "database connectivity and access diagnostics only."
        ),
        "dbhubError": dbhub_error,
        "connection": connection,
        "access": access,
        "rows": [],
    }


__all__ = ["execute_sql_query"]
