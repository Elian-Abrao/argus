"""Same-origin API proxy for the React dashboard frontend."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse

from .config import get_settings
from .http_client import ApiClient, get_client


router = APIRouter(prefix="/dashboard-api", tags=["dashboard-api"])


def _make_client_dep():
    """Return a dependency that creates an ApiClient with the request's Authorization header."""
    async def _dep(request: Request) -> ApiClient:
        return await get_client(request)
    return _dep


_get_client = _make_client_dep()


@router.get("/health")
async def dashboard_health(
    request: Request,
    client: ApiClient = Depends(_get_client),
):
    return await client.proxy_get("/health", params=list(request.query_params.multi_items()))


@router.get("/insights")
async def dashboard_insights_root(
    request: Request,
    client: ApiClient = Depends(_get_client),
):
    return await client.proxy_get(
        "/insights",
        params=list(request.query_params.multi_items()),
    )


@router.get("/insights/{insight_path:path}")
async def dashboard_insights(
    insight_path: str,
    request: Request,
    client: ApiClient = Depends(_get_client),
):
    return await client.proxy_get(
        f"/insights/{insight_path}",
        params=list(request.query_params.multi_items()),
    )


# ---------------------------------------------------------------------------
# Remote control proxy routes
# ---------------------------------------------------------------------------


@router.get("/schedules/calendar")
async def proxy_schedules_calendar(request: Request, client: ApiClient = Depends(_get_client)):
    return await client.proxy_get("/schedules/calendar", params=list(request.query_params.multi_items()))


@router.get("/schedules")
async def proxy_schedules_list(request: Request, client: ApiClient = Depends(_get_client)):
    return await client.proxy_get("/schedules", params=list(request.query_params.multi_items()))


@router.post("/schedules")
async def proxy_schedule_create(request: Request, client: ApiClient = Depends(_get_client)):
    body = await request.body()
    ct = request.headers.get("content-type", "application/json")
    return await client.proxy_post("/schedules", body, ct)


@router.get("/schedules/{schedule_id}")
async def proxy_schedule_get(schedule_id: str, request: Request, client: ApiClient = Depends(_get_client)):
    return await client.proxy_get(f"/schedules/{schedule_id}", params=list(request.query_params.multi_items()))


@router.patch("/schedules/{schedule_id}")
async def proxy_schedule_update(schedule_id: str, request: Request, client: ApiClient = Depends(_get_client)):
    body = await request.body()
    ct = request.headers.get("content-type", "application/json")
    return await client.proxy_patch(f"/schedules/{schedule_id}", body, ct)


@router.delete("/schedules/{schedule_id}")
async def proxy_schedule_delete(schedule_id: str, request: Request, client: ApiClient = Depends(_get_client)):
    return await client.proxy_delete(f"/schedules/{schedule_id}")


@router.post("/commands/run-now")
async def proxy_run_now(request: Request, client: ApiClient = Depends(_get_client)):
    body = await request.body()
    ct = request.headers.get("content-type", "application/json")
    return await client.proxy_post("/commands/run-now", body, ct)


@router.get("/commands")
async def proxy_commands_list(request: Request, client: ApiClient = Depends(_get_client)):
    return await client.proxy_get("/commands", params=list(request.query_params.multi_items()))


@router.get("/agent/identify")
async def proxy_agent_identify(request: Request, client: ApiClient = Depends(_get_client)):
    return await client.proxy_get("/agent/identify", params=list(request.query_params.multi_items()))


@router.get("/agent/status")
async def proxy_agent_status(request: Request, client: ApiClient = Depends(_get_client)):
    return await client.proxy_get("/agent/status")


@router.patch("/insights/hosts/{host_id}")
async def proxy_host_update(host_id: str, request: Request, client: ApiClient = Depends(_get_client)):
    body = await request.body()
    ct = request.headers.get("content-type", "application/json")
    return await client.proxy_patch(f"/insights/hosts/{host_id}", body, ct)


@router.patch("/instances/{instance_id}/args")
async def proxy_instance_args_update(instance_id: str, request: Request, client: ApiClient = Depends(_get_client)):
    body = await request.body()
    ct = request.headers.get("content-type", "application/json")
    return await client.proxy_patch(f"/insights/instances/{instance_id}/args", body, ct)


# ---------------------------------------------------------------------------
# Auth proxy routes
# ---------------------------------------------------------------------------


@router.post("/auth/login")
async def proxy_auth_login(request: Request, client: ApiClient = Depends(_get_client)):
    body = await request.body()
    ct = request.headers.get("content-type", "application/json")
    # Forward Cookie header so refresh token is sent on refresh requests
    cookie_header = request.headers.get("cookie", "")
    extra = {"cookie": cookie_header} if cookie_header else {}
    return await client.proxy_post("/auth/login", body, ct, extra_headers=extra or None)


@router.post("/auth/logout")
async def proxy_auth_logout(request: Request, client: ApiClient = Depends(_get_client)):
    cookie_header = request.headers.get("cookie", "")
    extra = {"cookie": cookie_header} if cookie_header else {}
    return await client.proxy_post("/auth/logout", b"", "", extra_headers=extra or None)


@router.post("/auth/refresh")
async def proxy_auth_refresh(request: Request, client: ApiClient = Depends(_get_client)):
    cookie_header = request.headers.get("cookie", "")
    extra = {"cookie": cookie_header} if cookie_header else {}
    return await client.proxy_post("/auth/refresh", b"", "", extra_headers=extra or None)


@router.get("/auth/me")
async def proxy_auth_me(request: Request, client: ApiClient = Depends(_get_client)):
    return await client.proxy_get("/auth/me")


@router.post("/auth/change-password")
async def proxy_auth_change_password(request: Request, client: ApiClient = Depends(_get_client)):
    body = await request.body()
    ct = request.headers.get("content-type", "application/json")
    return await client.proxy_post("/auth/change-password", body, ct)


# ---------------------------------------------------------------------------
# Admin proxy routes
# ---------------------------------------------------------------------------


@router.get("/admin/users")
async def proxy_admin_users_list(request: Request, client: ApiClient = Depends(_get_client)):
    return await client.proxy_get("/admin/users", params=list(request.query_params.multi_items()))


@router.post("/admin/users")
async def proxy_admin_users_create(request: Request, client: ApiClient = Depends(_get_client)):
    body = await request.body()
    ct = request.headers.get("content-type", "application/json")
    return await client.proxy_post("/admin/users", body, ct)


@router.get("/admin/users/{user_id}")
async def proxy_admin_user_get(user_id: str, request: Request, client: ApiClient = Depends(_get_client)):
    return await client.proxy_get(f"/admin/users/{user_id}")


@router.patch("/admin/users/{user_id}")
async def proxy_admin_user_update(user_id: str, request: Request, client: ApiClient = Depends(_get_client)):
    body = await request.body()
    ct = request.headers.get("content-type", "application/json")
    return await client.proxy_patch(f"/admin/users/{user_id}", body, ct)


@router.post("/admin/users/{user_id}/reset-password")
async def proxy_admin_user_reset_password(user_id: str, request: Request, client: ApiClient = Depends(_get_client)):
    return await client.proxy_post(f"/admin/users/{user_id}/reset-password", b"", "")


@router.put("/admin/users/{user_id}/access")
async def proxy_admin_user_access(user_id: str, request: Request, client: ApiClient = Depends(_get_client)):
    body = await request.body()
    ct = request.headers.get("content-type", "application/json")
    return await client.proxy_put(f"/admin/users/{user_id}/access", body, ct)


@router.delete("/admin/users/{user_id}/sessions")
async def proxy_admin_user_sessions_revoke(user_id: str, request: Request, client: ApiClient = Depends(_get_client)):
    return await client.proxy_delete(f"/admin/users/{user_id}/sessions")


# ---------------------------------------------------------------------------
# AI assistant proxy routes (SSE streaming)
# ---------------------------------------------------------------------------


@router.post("/ai/chat")
async def proxy_ai_chat(request: Request) -> StreamingResponse:
    """Proxy SSE: forwards chat request to AI assistant with user access context."""
    from fastapi import HTTPException
    import json

    settings = get_settings()
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Autenticação necessária")

    # Resolve perfil do usuário para construir o contexto de acesso
    api_base = str(settings.api_base_url).rstrip("/")
    async with httpx.AsyncClient(timeout=5.0) as http:
        me_resp = await http.get(
            f"{api_base}/auth/me",
            headers={"Authorization": auth_header},
        )
    if me_resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")

    profile = me_resp.json()
    is_admin = profile.get("role") == "admin"
    has_view_all = "view_all" in profile.get("permissions", [])
    # instance_ids: physically-scoped list of automation_instance UUIDs the user can see.
    # Computed server-side from both direct automation access AND client access — this is
    # the hard data-layer filter used by the AI CTE (not prompt-level).
    instance_ids: list[str] = [str(i) for i in profile.get("instance_ids", [])]

    user_context = {
        "is_restricted": not (is_admin or has_view_all),
        "instance_ids": instance_ids if not (is_admin or has_view_all) else [],
    }

    import logging
    logging.getLogger("ai_proxy").info(
        "AI chat — user=%s role=%s permissions=%s instance_ids_count=%d → is_restricted=%s",
        profile.get("email", "?"),
        profile.get("role", "?"),
        profile.get("permissions", []),
        len(instance_ids),
        user_context["is_restricted"],
    )

    # Inject user_context into body before forwarding to the AI assistant
    try:
        body_data = json.loads(await request.body())
    except Exception:
        raise HTTPException(status_code=400, detail="Body inválido")
    body_data["user_context"] = user_context
    body_data["user_info"] = {
        "name": profile.get("full_name", ""),
        "email": profile.get("email", ""),
        "role": profile.get("role", ""),
    }
    ai_body = json.dumps(body_data).encode()

    async def _stream():
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{settings.ai_base_url}/chat",
                content=ai_body,
                headers={"content-type": "application/json"},
            ) as response:
                async for chunk in response.aiter_bytes():
                    yield chunk

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/ai/chat/continue")
async def proxy_ai_chat_continue(request: Request):
    """Proxy: sends user decision to continue or stop the AI assistant loop."""
    settings = get_settings()
    body = await request.body()
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{settings.ai_base_url}/chat/continue",
            content=body,
            headers={"content-type": "application/json"},
        )
    return JSONResponse(content=resp.json(), status_code=resp.status_code)
