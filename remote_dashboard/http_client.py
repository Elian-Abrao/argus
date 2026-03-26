"""HTTP client helpers to call the remote API."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import httpx
from fastapi import HTTPException
from fastapi.responses import JSONResponse, Response

from .config import get_settings


QueryParams = Mapping[str, Any] | Sequence[tuple[str, Any]]
_PASSTHROUGH_HEADERS = {
    "content-disposition",
    "content-length",
    "cache-control",
    "etag",
    "last-modified",
}


class ApiClient:
    def __init__(self, auth_header: str | None = None) -> None:
        self.settings = get_settings()
        self._auth_header = auth_header
        self._client = httpx.AsyncClient(
            base_url=self.settings.api_base_url,
            timeout=self.settings.timeout,
        )

    def _auth_headers(self) -> dict[str, str]:
        if self._auth_header:
            return {"Authorization": self._auth_header}
        return {}

    async def get(self, path: str, params: QueryParams | None = None) -> Any:
        response = await self._request_get(path, params=params)
        return _parse_json_response(response)

    async def proxy_get(self, path: str, params: QueryParams | None = None) -> Response:
        response = await self._request_get(path, params=params)
        return _to_proxy_response(response)

    async def _request_get(self, path: str, params: QueryParams | None = None) -> httpx.Response:
        try:
            response = await self._client.get(path, params=params, headers=self._auth_headers())
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            detail = _extract_error_detail(exc.response)
            raise HTTPException(
                status_code=exc.response.status_code,
                detail=detail,
            ) from exc
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Falha ao conectar na API remota: {exc}",
            ) from exc

    async def proxy_post(
        self, path: str, body: bytes, content_type: str, params: QueryParams | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> Response:
        response = await self._request_with_body("POST", path, body, content_type, params, extra_headers)
        return _to_proxy_response(response)

    async def proxy_put(
        self, path: str, body: bytes, content_type: str, params: QueryParams | None = None
    ) -> Response:
        response = await self._request_with_body("PUT", path, body, content_type, params)
        return _to_proxy_response(response)

    async def proxy_patch(
        self, path: str, body: bytes, content_type: str, params: QueryParams | None = None
    ) -> Response:
        response = await self._request_with_body("PATCH", path, body, content_type, params)
        return _to_proxy_response(response)

    async def proxy_delete(self, path: str, params: QueryParams | None = None) -> Response:
        try:
            response = await self._client.delete(path, params=params, headers=self._auth_headers())
            response.raise_for_status()
            return _to_proxy_response(response)
        except httpx.HTTPStatusError as exc:
            detail = _extract_error_detail(exc.response)
            raise HTTPException(status_code=exc.response.status_code, detail=detail) from exc
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"Falha ao conectar na API remota: {exc}") from exc

    async def _request_with_body(
        self, method: str, path: str, body: bytes, content_type: str,
        params: QueryParams | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        headers = {**self._auth_headers(), "content-type": content_type}
        if extra_headers:
            headers.update(extra_headers)
        try:
            response = await self._client.request(
                method, path, content=body, headers=headers, params=params
            )
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            detail = _extract_error_detail(exc.response)
            raise HTTPException(status_code=exc.response.status_code, detail=detail) from exc
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"Falha ao conectar na API remota: {exc}") from exc

    async def close(self) -> None:
        await self._client.aclose()


_shared_client: ApiClient | None = None


async def get_client(request: "Request | None" = None) -> ApiClient:
    """Return a per-request ApiClient that forwards the Authorization header."""
    from fastapi import Request as FastAPIRequest
    auth_header: str | None = None
    if request is not None:
        auth_header = request.headers.get("Authorization")
    if auth_header:
        return ApiClient(auth_header=auth_header)
    # No auth header — reuse shared instance for efficiency
    global _shared_client
    if _shared_client is None:
        _shared_client = ApiClient()
    return _shared_client


def _parse_json_response(response: httpx.Response) -> Any:
    content_type = (response.headers.get("content-type") or "").lower()
    if "application/json" not in content_type:
        raise HTTPException(
            status_code=502,
            detail="Resposta inesperada da API remota (esperado JSON).",
        )
    return response.json()


def _to_proxy_response(response: httpx.Response) -> Response:
    if response.status_code == 204 or not response.content:
        return Response(status_code=response.status_code)

    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type.lower():
        payload = response.json()
        return JSONResponse(content=payload, status_code=response.status_code)

    passthrough_headers: dict[str, str] = {}
    for header, value in response.headers.items():
        if header.lower() in _PASSTHROUGH_HEADERS:
            passthrough_headers[header] = value
    return Response(
        content=response.content,
        status_code=response.status_code,
        media_type=content_type or None,
        headers=passthrough_headers,
    )


def _extract_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        text = response.text.strip()
        if text:
            return text
        return f"Erro na API remota ({response.status_code})."

    if isinstance(payload, dict):
        detail = payload.get("detail") or payload.get("message")
        if detail:
            return str(detail)

    return f"Erro na API remota ({response.status_code})."
