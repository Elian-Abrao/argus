# Remote API
[Voltar ao indice](README.md)

A Remote API recebe logs do logger, enfileira no RabbitMQ e grava no Postgres
via workers. Tambem oferece endpoints read-only para o dashboard e auditoria
de emails enviados pelas automacoes.

## Visao geral
```
Bots -> API (FastAPI) -> RabbitMQ -> Workers -> Postgres
            |                               |
            +-> email attachments --------> MinIO
                                   -> Dashboard (consultas)
```

## Entidades principais
- `clients`: clientes/tenants.
- `hosts`: maquinas/ambientes.
- `automations`: catalogo de automacoes.
- `automation_instances`: combinacao automacao + cliente + host.
- `runs`: execucoes do logger.
- `log_entries`: mensagens de log.
- `run_snapshots`: blocos estruturados (perfil, memoria, etc.).
- `email_events`: metadados de emails enviados por run.
- `email_attachments`: anexos dos emails com metadados de armazenamento.

## Endpoints
Base: `/api`

### Ingest (escrita)
- `POST /ingest/instances`
- `POST /runs`
- `PATCH /runs`
- `POST /logs/batch`
- `POST /runs/{run_id}/snapshots`
- `POST /runs/{run_id}/emails`
- `POST /runs/{run_id}/emails/{email_id}/attachments` (`multipart/form-data`)

Exemplo de payload (instances):
```json
{
  "instance_id": "c1e3ae4d-fafe-51e7-bf01-000000000001",
  "automation": {"code": "InvoiceBot", "name": "Invoice Bot"},
  "client": {"name": "Cliente XPTO", "external_code": "CXPTO"},
  "host": {"root_folder": "D:/Bots/Faturamento", "ip_address": "10.0.0.5"},
  "deployment_tag": "prod-01",
  "config_signature": "sha256:abc123"
}
```

### Insights (consulta)
- `GET /insights/hosts`
- `GET /insights/hosts/{host_id}`
- `GET /insights/hosts/{host_id}/instances`
- `GET /insights/automations`
- `GET /insights/automations/{automation_id}`
- `GET /insights/automations/{automation_id}/instances`
- `GET /insights/automations/{automation_id}/runs`
- `GET /insights/instances/{instance_id}/runs`
- `GET /insights/runs/timeline`
- `GET /insights/runs/{run_id}`
- `GET /insights/runs/{run_id}/logs`
- `GET /insights/runs/{run_id}/logs/metrics`
- `GET /insights/runs/{run_id}/emails`
- `GET /insights/emails/{email_id}/attachments/{attachment_id}/download`
- `GET /insights/emails/{email_id}/attachments/{attachment_id}/preview`
- `GET /insights/clients`
- `GET /insights/clients/{client_id}`
- `GET /insights/clients/{client_id}/automations`

### Health
- `GET /api/health` (verifica o banco)

Observacao: o Nginx pode expor um `/health` separado para liveness.

## Configuracao
Variaveis de ambiente (`LOGGER_API_*`):
- `DATABASE_URL`
- `RABBITMQ_URL`
- `API_PREFIX` (padrao: `/api`)
- `EMAIL_RETENTION_DAYS_DEFAULT` (padrao: `7`)
- `EMAIL_RETENTION_CLEANUP_ENABLED` (padrao: `true`)
- `EMAIL_RETENTION_CLEANUP_INTERVAL_SECONDS` (padrao: `3600`)
- `EMAIL_RETENTION_CLEANUP_BATCH_SIZE` (padrao: `500`)
- `RUN_STALE_CLEANUP_ENABLED` (padrao: `true`)
- `RUN_STALE_TIMEOUT_HOURS` (padrao: `24`)
- `RUN_STALE_CLEANUP_INTERVAL_SECONDS` (padrao: `300`)
- `RUN_STALE_CLEANUP_BATCH_SIZE` (padrao: `500`)
- `MINIO_ENDPOINT` (padrao: `minio:9000`)
- `MINIO_ACCESS_KEY`
- `MINIO_SECRET_KEY`
- `MINIO_BUCKET` (padrao: `logger-email-attachments`)
- `MINIO_SECURE` (padrao: `false`)

Auto-stop de runs stale:
- A API marca automaticamente como `stopped` qualquer run com `status=running`
  que esteja sem logs por mais de 24h (configuravel).
- O `finished_at` e fixado no ultimo log conhecido (ou `started_at` quando nao ha logs),
  evitando manter execucoes antigas abertas indefinidamente.

## Rodando local
### 1) Dependencias
```bash
pip install -e .[api]
```

### 2) Banco e schema
```bash
psql -f db/schema.sql
```

### 3) API
```bash
uvicorn remote_api.main:app --reload --port 8100
```

### 4) Workers
```bash
LOGGER_API_DATABASE_URL=postgresql+psycopg://logger:logger@localhost:5432/logger_db \
LOGGER_API_RABBITMQ_URL=amqp://guest:guest@localhost/ \
python -m remote_api.workers
```

### 5) Storage de anexos
Suba MinIO local (via compose) e configure `LOGGER_API_MINIO_*`.

## Dashboard (proxy same-origin)
O dashboard usa `GET /dashboard-api/*` e o backend proxy repassa para:
- `/api/health`
- `/api/insights/*`

## Docker Compose
O `docker-compose.yml` inclui Postgres, RabbitMQ, MinIO, API, workers e dashboard.
Por padrao, o MinIO publica no host em `9010` (API) e `9011` (console) para
evitar conflito com servicos que ja usam `9000`.

## Seguranca
Nao ha autenticacao embutida na API. Recomenda-se:
- proteger `/api/insights` e dashboard via VPN/rede interna,
- expor apenas ingestao publicamente, se necessario,
- usar HTTPS sempre,
- trocar credenciais default do MinIO em producao.
