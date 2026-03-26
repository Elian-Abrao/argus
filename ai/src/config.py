from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()

AI_NAME = os.getenv("ARGUS_AI_NAME", "Argus AI")
PLATFORM_NAME = os.getenv("ARGUS_PLATFORM_NAME", "Argus")


@dataclass(frozen=True)
class BridgeSettings:
    url: str = os.getenv("CODEX_BRIDGE_URL", "http://127.0.0.1:47831")
    model: str = os.getenv("CODEX_MODEL", "gpt-5.4")
    reasoning_effort: str = os.getenv("CODEX_REASONING", "medium")


@dataclass(frozen=True)
class DbhubSettings:
    url: str = os.getenv("DBHUB_URL", "http://127.0.0.1:8080/mcp")


@dataclass(frozen=True)
class DatabaseSettings:
    host: str = os.getenv("DB_HOST", "")
    port: int = int(os.getenv("DB_PORT", "5432"))
    user: str = os.getenv("DB_USER", "")
    password: str = os.getenv("DB_PASSWORD", "")
    database: str = os.getenv("DB_NAME", "")


def get_bridge_settings() -> BridgeSettings:
    return BridgeSettings()


def get_dbhub_settings() -> DbhubSettings:
    return DbhubSettings()


def get_database_settings() -> DatabaseSettings:
    return DatabaseSettings()


__all__ = [
    "BridgeSettings",
    "DbhubSettings",
    "DatabaseSettings",
    "get_bridge_settings",
    "get_dbhub_settings",
    "get_database_settings",
    "AI_NAME",
    "PLATFORM_NAME",
]
