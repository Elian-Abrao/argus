# AI Assistant

## What it is

The Argus AI assistant is a natural language data interface embedded in the dashboard. It queries the database via DBHub and answers questions about automations, runs, logs, clients, and hosts using ChatGPT/Codex.

Code lives in the `ai/` directory.

## Architecture

```
Frontend (chat widget)
  ↓  POST /dashboard-api/ai/chat  (SSE)
remote_dashboard (proxy)
  ↓  POST http://argus-ai:8000/chat
argus-ai (FastAPI)
  ↓  python -m codex_bridge serve  (subprocess)
codex-bridge (local broker)
  ↓  HTTPS  ChatGPT/Codex API
  ↓  HTTP   DBHub (npx @bytebase/dbhub)
  ↓  PostgreSQL
```

### Components inside the `argus-ai` container

| Component | Purpose |
|---|---|
| `serve.py` | FastAPI with `POST /chat` (SSE) and `GET /health` |
| `src/agent/loop.py` | Agentic loop — calls Codex, executes tools, iterates |
| `src/agent/broker.py` | Ensures `codex-bridge` is running as a subprocess |
| `src/mcp_server/runtime.py` | Ensures DBHub is running via `npx` |
| `src/mcp_server/dbhub_client.py` | JSON-RPC client for DBHub |
| `prompts/system.md` | System prompt with `{AI_NAME}` and `{PLATFORM_NAME}` placeholders |

### Available tools for the model

- `execute_sql` — executes `SELECT` against PostgreSQL (max 200 rows, readonly)
- `search_objects` — searches tables/columns in the schema

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DB_HOST` | — | PostgreSQL host (use `postgres` in Docker) |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_USER` | — | Database user |
| `DB_PASSWORD` | — | Database password |
| `DB_NAME` | — | Database name |
| `CODEX_MODEL` | `gpt-5.4` | Model to use |
| `CODEX_REASONING` | `medium` | Reasoning effort (`low`, `medium`, `high`) |
| `CODEX_BRIDGE_DISABLE_KEYRING` | `1` | Must be `1` in production (no keyring in container) |
| `ARGUS_AI_NAME` | `Argus AI` | Display name injected into the system prompt |
| `ARGUS_PLATFORM_NAME` | `Argus` | Platform name injected into the system prompt |
| `ARGUS_AI_LANGUAGE` | `en` | Language hint for AI responses |

## Codex Authentication

`codex-bridge` uses an OAuth session from your OpenAI/ChatGPT account. The session is stored at:

```
~/.codex-bridge/auth/codex-session.json
```

In Docker, this directory is mounted as a volume from the host:

```yaml
volumes:
  - ${HOME}/.codex-bridge:/root/.codex-bridge
```

The `refreshToken` ensures automatic renewal without manual intervention.

---

## Deploying (first time)

### Prerequisite: Codex credentials

On your local machine (where you authenticated with `codex-bridge`):

```bash
ssh your-server "mkdir -p ~/.codex-bridge/auth"
scp ~/.codex-bridge/auth/codex-session.json your-server:~/.codex-bridge/auth/codex-session.json
```

> Only needs to be done once. The `refreshToken` renews automatically.

### Full sequence

```bash
# 1. Pull the repository
git pull

# 2. Build and start
docker compose build argus-ai argus-dashboard
docker compose up -d argus-ai argus-dashboard
```

---

## Deploying (updates)

```bash
git pull
docker compose build argus-ai argus-dashboard
docker compose up -d argus-ai argus-dashboard
```

If only the dashboard changed (no AI changes):

```bash
git pull
docker compose build argus-dashboard
docker compose up -d argus-dashboard
```

If only the AI changed:

```bash
git pull
docker compose build argus-ai
docker compose up -d argus-ai
```

---

## Diagnostics

### View container logs

```bash
docker compose logs -f argus-ai
```

### Check the codex-bridge internal log

```bash
docker compose exec argus-ai cat /app/.codex-bridge.log
```

### Verify codex-bridge is responding inside the container

```bash
docker compose exec argus-ai curl -s http://127.0.0.1:47831/v1/health
```

### Verify DBHub is responding

```bash
docker compose exec argus-ai curl -s http://127.0.0.1:8080/healthz
```
