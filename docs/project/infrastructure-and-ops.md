# Infraestrutura e Operacao

## Stack de containers

Arquivo principal:

- `docker-compose.yml`

## Servicos

### `postgres`

- imagem: `postgres:15`
- volume: `postgres-data`
- porta local: `5544:5432`

### `rabbitmq`

- imagem: `rabbitmq:3-management`
- portas:
  - `5678:5672`
  - `15678:15672`

### `minio`

- imagem: `minio/minio:latest`
- volume: `minio-data`
- portas padrao:
  - `9010:9000`
  - `9011:9001`

### `argus-api`

- build: `Dockerfile.api`
- depende de:
  - postgres
  - rabbitmq
  - minio

### `argus-workers`

- build: `Dockerfile.api`
- comando: `python -m remote_api.workers`

### `argus-ai`

- build: `Dockerfile.ai`
- AI assistant in natural language (ChatGPT/Codex + DBHub)
- depende de `postgres`
- volume: `${HOME}/.codex-bridge:/root/.codex-bridge` (OAuth credentials)
- acessível apenas na `argus-net` (sem porta exposta ao host)
- detalhes: `docs/project/ai-assistant.md`

### `argus-dashboard`

- build: `Dockerfile.dashboard`
- depende de `argus-api` e `argus-ai`

## Redes

- `argus-net`
  - bridge interna
- `proxy-net`
  - externa
  - precisa existir antes do `docker compose up`

## Reverse proxy

Arquivo:

- `nginx/logger_nginx.conf`

### Responsabilidades

- expor a API e o dashboard em dominios publicos
- aplicar regras de allowlist/restricao
- suportar WebSocket do agent
- servir TLS com certificados externos

## Variaveis importantes

### Infra geral

- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`

### API

- `LOGGER_API_DATABASE_URL`
- `LOGGER_API_RABBITMQ_URL`
- `LOGGER_API_EMAIL_RETENTION_*`
- `LOGGER_API_RUN_STALE_*`
- `LOGGER_API_MINIO_*`
- `LOGGER_API_SCHEDULE_CHECKER_*`
- `LOGGER_API_COMMAND_EXPIRY_*`

### Dashboard

- `ARGUS_API_BASE_URL`
- `ARGUS_AI_BASE_URL` (default: `http://argus-ai:8000`)
- `ARGUS_TIMEOUT`
- `ARGUS_TIMEZONE`

### AI Assistant

- `CODEX_MODEL` (default: `gpt-5.4`)
- `CODEX_REASONING` (default: `medium`)
- `CODEX_BRIDGE_DISABLE_KEYRING` (deve ser `1` em producao)
- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
- `ARGUS_AI_NAME` (default: `Argus AI`)
- `ARGUS_PLATFORM_NAME` (default: `Argus`)
- `ARGUS_AI_LANGUAGE` (default: `en`)

## Como rodar local

### Biblioteca apenas

```bash
pip install -e .
```

### API

```bash
pip install -e .[api]
uvicorn remote_api.main:app --reload --port 8100
python -m remote_api.workers
```

### Dashboard

```bash
npm --prefix remote_dashboard/frontend ci
npm --prefix remote_dashboard/frontend run build
ARGUS_API_BASE_URL="http://localhost:8100/api" \
uvicorn remote_dashboard.main:app --reload --port 8200
```

### Stack completa

```bash
cp .env.example .env
docker compose up -d postgres rabbitmq minio argus-api argus-workers argus-dashboard
```

## Observacoes operacionais

- o dashboard precisa do build do frontend para responder corretamente
- a API depende do RabbitMQ para ingestao de telemetria
- anexos de e-mail dependem do MinIO
- sem framework formal de migrations, o ambiente novo depende de SQL base + bootstrap da API

## Ponto de atencao de documentacao

Quando houver conflito entre docs e codigo, conferir primeiro:

- `remote_api/config.py`
- `remote_dashboard/config.py`
- `docker-compose.yml`
