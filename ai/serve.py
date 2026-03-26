"""Argus AI — FastAPI endpoint for dashboard integration."""

from __future__ import annotations

import asyncio
import json
import queue
import threading
import uuid

from codex_bridge_sdk import create_chat_client
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.agent.broker import ensure_broker_running
from src.agent.chat import (
    BridgeClientError,
    get_codex_limit_message,
    is_codex_usage_limit_error,
)
from src.agent.loop import iter_agentic_loop
from src.config import get_bridge_settings

app = FastAPI(title="Argus AI")

# ---------------------------------------------------------------------------
# Pending continue decisions (human-in-the-loop)
# ---------------------------------------------------------------------------

class _ContinueState:
    __slots__ = ("event", "decision")
    def __init__(self):
        self.event = threading.Event()
        self.decision: str | bool = False

_pending_continues: dict[str, _ContinueState] = {}
_pending_lock = threading.Lock()

CONTINUE_TIMEOUT = 300  # 5 minutes


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class UserContext(BaseModel):
    is_restricted: bool = True   # Fail-closed: restrito por padrão
    instance_ids: list[str] = []  # automation_instance IDs (physical data-layer filter)


class UserInfo(BaseModel):
    name: str = ""
    email: str = ""
    role: str = ""


class ChatRequest(BaseModel):
    question: str
    history: list[dict] = []
    user_context: UserContext = UserContext()  # Default: restrito, sem automações
    user_info: UserInfo = UserInfo()
    current_page: str = ""


class ContinueRequest(BaseModel):
    session_id: str
    decision: str  # "continue", "stop", or custom message


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/chat/continue")
async def chat_continue(req: ContinueRequest) -> dict:
    with _pending_lock:
        state = _pending_continues.get(req.session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found or already expired")

    decision_val = req.decision.strip()
    if decision_val == "stop":
        state.decision = False
    elif decision_val == "continue":
        state.decision = True
    else:
        # Custom message from user — treated as "continue + inject message"
        state.decision = decision_val
    state.event.set()
    return {"ok": True}


@app.post("/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    print(
        f"[AI /chat] user_context recebido: "
        f"is_restricted={req.user_context.is_restricted}, "
        f"instance_ids_count={len(req.user_context.instance_ids)}"
    )
    session_id = str(uuid.uuid4())
    q: queue.Queue = queue.Queue()

    # Create continue state for this session
    continue_state = _ContinueState()
    with _pending_lock:
        _pending_continues[session_id] = continue_state

    def _ask_continue() -> str | bool:
        """Blocks until the user sends a decision via /chat/continue."""
        continue_state.event.clear()
        if continue_state.event.wait(timeout=CONTINUE_TIMEOUT):
            result = continue_state.decision
            continue_state.decision = False
            return result
        # Timeout — force answer with available data
        return False

    def _run_loop() -> None:
        try:
            ensure_broker_running()
            settings = get_bridge_settings()
            client = create_chat_client(settings.url)
            for event in iter_agentic_loop(
                req.question,
                req.history,
                client,
                settings.model,
                settings.reasoning_effort,
                ask_continue_fn=_ask_continue,
                user_context=req.user_context,
                user_info={"name": req.user_info.name, "email": req.user_info.email, "role": req.user_info.role},
                current_page=req.current_page,
            ):
                # Inject session_id into ask_continue events
                if event.get("type") == "ask_continue":
                    event = {**event, "session_id": session_id}
                q.put(event)
        except BridgeClientError as exc:
            if is_codex_usage_limit_error(exc):
                q.put({"type": "error", "text": get_codex_limit_message()})
            else:
                q.put({"type": "error", "text": str(exc)})
        except Exception as exc:  # noqa: BLE001
            q.put({"type": "error", "text": str(exc)})
        finally:
            q.put(None)
            # Clean up
            with _pending_lock:
                _pending_continues.pop(session_id, None)

    threading.Thread(target=_run_loop, daemon=True).start()

    async def _stream():
        loop = asyncio.get_event_loop()
        while True:
            event = await loop.run_in_executor(None, q.get)
            if event is None:
                yield f'data: {json.dumps({"type": "done"}, ensure_ascii=False)}\n\n'
                break
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
