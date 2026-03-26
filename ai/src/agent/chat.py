from __future__ import annotations

import random

from codex_bridge_sdk import BridgeClientError, create_chat_client

from .broker import ensure_broker_running
from ..config import get_bridge_settings
from .loop import run_agentic_loop


BRIDGE_SETTINGS = get_bridge_settings()
BRIDGE_URL = BRIDGE_SETTINGS.url
DEFAULT_MODEL = BRIDGE_SETTINGS.model
DEFAULT_REASONING = BRIDGE_SETTINGS.reasoning_effort

_CODEX_LIMIT_MESSAGES = [
    "Sinto muito, atingi meu limite de uso agora. Tente novamente em alguns minutos, por favor.",
    "Desculpe, fiquei temporariamente indisponível por limite de uso. Se você tentar novamente daqui a pouco, eu continuo com você.",
    "Perdão, meu acesso bateu no limite neste momento. Pode me chamar de novo em instantes.",
    "Sinto muito, alcancei o limite de uso por agora. Tente novamente daqui a pouco que eu volto a ajudar.",
]


def is_codex_usage_limit_error(exc: Exception | str) -> bool:
    text = str(exc).lower()
    patterns = (
        "rate limit",
        "rate-limit",
        "quota",
        "usage limit",
        "too many requests",
        "429",
        "limit reached",
        "exceeded your current quota",
    )
    return any(pattern in text for pattern in patterns)


def get_codex_limit_message() -> str:
    return random.choice(_CODEX_LIMIT_MESSAGES)


def ask_data_assistant(
    user_question: str,
    history: list[dict[str, str]] | None = None,
) -> str:
    ensure_broker_running()
    client = create_chat_client(BRIDGE_URL)
    return run_agentic_loop(
        user_question,
        history or [],
        client,
        DEFAULT_MODEL,
        DEFAULT_REASONING,
    )


__all__ = [
    "BRIDGE_URL",
    "BridgeClientError",
    "ask_data_assistant",
    "is_codex_usage_limit_error",
    "get_codex_limit_message",
]
