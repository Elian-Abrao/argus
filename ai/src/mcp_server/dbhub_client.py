from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib import error, request

from ..config import get_dbhub_settings
from .runtime import ensure_dbhub_running


class DbhubClientError(RuntimeError):
    """Raised when DBHub cannot be reached or returns an invalid payload."""


@dataclass
class DbhubClient:
    url: str
    timeout: float = 20.0

    def initialize(self) -> dict[str, Any]:
        return self._rpc(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "argus-ai-mcp",
                    "version": "0.1.0",
                },
            },
            request_id=1,
        )

    def list_tools(self) -> list[dict[str, Any]]:
        payload = self._rpc("tools/list", {}, request_id=2)
        tools = payload.get("tools")
        if not isinstance(tools, list):
            raise DbhubClientError("DBHub returned an invalid tools list.")
        return [tool for tool in tools if isinstance(tool, dict)]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        payload = self._rpc(
            "tools/call",
            {
                "name": name,
                "arguments": arguments,
            },
            request_id=3,
        )
        return self._parse_tool_result(payload)

    def _rpc(self, method: str, params: dict[str, Any], *, request_id: int) -> dict[str, Any]:
        body = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params,
            }
        ).encode("utf-8")

        req = request.Request(
            self.url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
        )

        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            raise DbhubClientError(f"DBHub HTTP error {exc.code}: {raw}") from exc
        except error.URLError as exc:
            raise DbhubClientError(f"Failed to reach DBHub at {self.url}: {exc.reason}") from exc
        except TimeoutError as exc:
            raise DbhubClientError(f"Failed to reach DBHub at {self.url}: timed out") from exc

        try:
            envelope = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise DbhubClientError("DBHub returned malformed JSON.") from exc

        if not isinstance(envelope, dict):
            raise DbhubClientError("DBHub returned an invalid JSON-RPC envelope.")

        if isinstance(envelope.get("error"), dict):
            message = envelope["error"].get("message") or "Unknown DBHub error."
            raise DbhubClientError(str(message))

        result = envelope.get("result")
        if not isinstance(result, dict):
            raise DbhubClientError("DBHub returned an invalid JSON-RPC result.")

        return result

    def _parse_tool_result(self, payload: dict[str, Any]) -> dict[str, Any]:
        content = payload.get("content")
        if not isinstance(content, list) or not content:
            raise DbhubClientError("DBHub returned an empty tool result.")

        first_item = content[0]
        if not isinstance(first_item, dict):
            raise DbhubClientError("DBHub returned an invalid tool content item.")

        text = first_item.get("text")
        if not isinstance(text, str) or not text.strip():
            raise DbhubClientError("DBHub returned tool content without text.")

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {"rawText": text}

        if not isinstance(parsed, dict):
            return {"raw": parsed}

        return parsed


def create_dbhub_client() -> DbhubClient:
    ensure_dbhub_running()
    return DbhubClient(url=get_dbhub_settings().url)


__all__ = ["DbhubClient", "DbhubClientError", "create_dbhub_client"]
