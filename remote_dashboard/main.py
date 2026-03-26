"""Entry point for the dashboard FastAPI app."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from .api_proxy import router as api_proxy_router


class ForwardedHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        proto = request.headers.get("x-forwarded-proto")
        if proto:
            request.scope["scheme"] = proto
        host = request.headers.get("x-forwarded-host")
        if host:
            server = request.scope.get("server")
            port = server[1] if server else 80
            request.scope["server"] = (host, port)
        return await call_next(request)


def create_app() -> FastAPI:
    app = FastAPI(title="Logger Dashboard")
    app.add_middleware(ForwardedHeadersMiddleware)
    app.include_router(api_proxy_router)

    dist_dir = Path(__file__).parent / "frontend" / "dist"
    dist_dir_resolved = dist_dir.resolve()
    assets_dir = dist_dir / "assets"

    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/", include_in_schema=False)
    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_entrypoint(full_path: str = ""):
        if full_path.startswith("dashboard-api"):
            raise HTTPException(status_code=404, detail="Not Found")

        # Serve static files generated in dist root (e.g., /favicon.svg)
        # before falling back to index.html for client-side routes.
        if full_path:
            requested_file = (dist_dir_resolved / full_path).resolve()
            if requested_file.is_file() and requested_file.is_relative_to(dist_dir_resolved):
                return FileResponse(requested_file)

        index_file = dist_dir / "index.html"
        if not index_file.exists():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": (
                        "Frontend build nao encontrado. "
                        "Execute: npm --prefix remote_dashboard/frontend run build"
                    )
                },
            )

        return HTMLResponse(index_file.read_text(encoding="utf-8"))

    return app


app = create_app()
