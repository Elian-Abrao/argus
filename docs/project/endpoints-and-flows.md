# Endpoints e Fluxos

Todos os endpoints da API entram sob o prefixo configuravel `LOGGER_API_API_PREFIX`, que por padrao e `/api`.

## Health

- `GET /api/health`
  - healthcheck com teste de banco

## Ingestao

### Instancias

- `POST /api/ingest/instances`
  - publica evento de registro de `automation_instance`

### Runs

- `POST /api/runs`
  - publica evento `run.started`
- `PATCH /api/runs`
  - publica evento `run.updated`

### Logs e snapshots

- `POST /api/logs/batch`
  - publica lote de logs
- `POST /api/runs/{run_id}/snapshots`
  - publica snapshot estruturado

### E-mails

- `POST /api/runs/{run_id}/emails`
  - persiste evento de e-mail
- `POST /api/runs/{run_id}/emails/{email_id}/attachments`
  - upload de anexo para MinIO

## Insights

### Hosts

- `GET /api/insights/hosts`
- `GET /api/insights/hosts/{host_id}`
- `GET /api/insights/hosts/{host_id}/instances`

### Automations

- `GET /api/insights/automations`
- `GET /api/insights/automations/{automation_id}`
- `GET /api/insights/automations/{automation_id}/instances`
- `GET /api/insights/automations/{automation_id}/runs`

### Instances

- `GET /api/insights/instances/{instance_id}/runs`
- `PATCH /api/insights/instances/{instance_id}/args`

### Runs

- `GET /api/insights/runs`
- `GET /api/insights/runs/overview`
- `GET /api/insights/runs/timeline`
- `GET /api/insights/runs/{run_id}`
- `GET /api/insights/runs/{run_id}/logs`
- `GET /api/insights/runs/{run_id}/logs/metrics`
- `GET /api/insights/runs/{run_id}/emails`

### Anexos de e-mail

- `GET /api/insights/emails/{email_id}/attachments/{attachment_id}/download`
- `GET /api/insights/emails/{email_id}/attachments/{attachment_id}/preview`

### Clientes

- `GET /api/insights/clients`
- `GET /api/insights/clients/{client_id}`
- `GET /api/insights/clients/{client_id}/automations`

## Controle remoto

### Schedules

- `GET /api/schedules/calendar`
  - expande recorrencia em ocorrencias concretas
- `GET /api/schedules`
- `POST /api/schedules`
- `GET /api/schedules/{schedule_id}`
- `PATCH /api/schedules/{schedule_id}`
- `DELETE /api/schedules/{schedule_id}`

### Commands

- `POST /api/commands/run-now`
- `GET /api/commands`
- `GET /api/commands/{command_id}`
- `POST /api/commands/{command_id}/cancel`

### Agent bootstrap e status

- `GET /api/agent/identify`
- `GET /api/agent/status`
- `WS /api/agent/ws/{host_id}`

## Proxy do dashboard

O frontend nao chama `/api` diretamente. Ele usa:

- `/dashboard-api/health`
- `/dashboard-api/insights/*`
- `/dashboard-api/schedules*`
- `/dashboard-api/commands*`
- `/dashboard-api/agent/status`
- `/dashboard-api/agent/identify`
- `/dashboard-api/instances/{instance_id}/args`

## Fluxos ponta a ponta

### 1. Ingestao de logs

```text
automacao
  -> remote_sink
  -> /api/runs, /api/logs/batch, /api/runs/{run_id}/snapshots
  -> RabbitMQ
  -> worker
  -> Postgres
  -> /api/insights/*
  -> dashboard
```

### 2. Auditoria de e-mail

```text
automacao
  -> /api/runs/{run_id}/emails
  -> /api/runs/{run_id}/emails/{email_id}/attachments
  -> Postgres + MinIO
  -> /api/insights/runs/{run_id}/emails
  -> download/preview pelo dashboard
```

### 3. Run-now

```text
usuario no dashboard
  -> /dashboard-api/commands/run-now
  -> /api/commands/run-now
  -> command criado
  -> WebSocket para o host
  -> agent envia ack/started/completed...
  -> command atualizado
  -> dashboard reflete status
```

### 4. Agendamento automatico

```text
loop interno schedule_checker
  -> list_due_schedules()
  -> cria command
  -> envia execute por WebSocket
  -> agent executa
  -> logger cria run
  -> agent encerra command
  -> API tenta fechar run orfa se necessario
```

### 5. Cancelamento

```text
dashboard
  -> /dashboard-api/commands/{id}/cancel
  -> /api/commands/{id}/cancel
  -> mensagem kill via WebSocket
  -> agent termina processo
  -> API marca command cancelado
```
