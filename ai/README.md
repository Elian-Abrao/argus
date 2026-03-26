# Argus AI

AI assistant module for the Argus automation monitoring platform. Answers natural language questions about automations, runs, logs, clients, and hosts by querying the database in real time via ChatGPT/Codex and DBHub.

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

## Components

| Component | Purpose |
|---|---|
| `serve.py` | FastAPI with `POST /chat` (SSE) and `GET /health` |
| `src/agent/loop.py` | Agentic loop — calls Codex, executes tools, iterates |
| `src/agent/broker.py` | Ensures `codex-bridge` is running as a subprocess |
| `src/mcp_server/runtime.py` | Ensures DBHub is running via `npx` |
| `src/mcp_server/dbhub_client.py` | JSON-RPC client for DBHub |
| `prompts/system.md` | System prompt (supports `{AI_NAME}` and `{PLATFORM_NAME}` placeholders) |

## Setup

1. Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Create a `.env` file:

```env
CODEX_BRIDGE_URL=http://127.0.0.1:47831
CODEX_MODEL=gpt-5.4
CODEX_REASONING=medium

DB_HOST=localhost
DB_PORT=5544
DB_USER=logger
DB_PASSWORD=logger
DB_NAME=logger_db

DBHUB_PORT=8080
DBHUB_URL=http://127.0.0.1:8080/mcp

# Branding (optional)
ARGUS_AI_NAME=Argus AI
ARGUS_PLATFORM_NAME=Argus
```

3. Authenticate `codex-bridge`:

```bash
codex-bridge login
```

4. Start DBHub:

```bash
./scripts/start_dbhub.sh
```

5. Run the web server:

```bash
uvicorn serve:app --host 0.0.0.0 --port 8000
```

Or run the CLI:

```bash
python main.py
```

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
