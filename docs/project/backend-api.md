# Backend API

## Escopo

O servico `remote_api/` e o nucleo da plataforma remota. Ele mistura tres responsabilidades:

1. ingestao de telemetria
2. leitura/insights para o dashboard
3. controle remoto de automacoes, agendamentos e agents

## App factory

- `remote_api/main.py`

### Responsabilidades do startup

- registrar rotas sob `LOGGER_API_API_PREFIX` (default `/api`)
- conectar publisher RabbitMQ
- garantir schema complementar:
  - `ensure_email_schema()`
  - `ensure_control_schema()`
- iniciar loops de manutencao:
  - limpeza de e-mails expirados
  - fechamento de runs sem atividade
  - verificador de schedules
  - expiracao de comandos pendentes

## Camadas

- `routes/`
  - HTTP e WebSocket
- `crud.py`
  - persistencia, listagens, agregacoes e regras de acesso a dados
- `models.py`
  - modelos SQLAlchemy
- `schemas.py`
  - contratos Pydantic
- `messaging.py`
  - publisher RabbitMQ
- `workers/`
  - consumo assincrono das filas
- `storage.py`
  - acesso ao MinIO
- `retention.py`
  - rotinas de limpeza e reconciliacao

## Divisao funcional das rotas

- `health.py`
  - saude do servico e banco
- `ingest.py`
  - registro de instancias
- `runs.py`
  - inicio/fim/atualizacao de runs via fila
- `logs.py`
  - batches de logs e snapshots
- `emails.py`
  - auditoria de e-mails e anexos
- `insights.py`
  - leitura para dashboard
- `schedules.py`
  - CRUD de agendamentos e calendario expandido
- `commands.py`
  - run-now, listagem, cancelamento e status/identify do agent
- `agent_ws.py`
  - canal WebSocket bidirecional com o agent

## Fluxo de ingestao

```text
logger/extras/remote_sink.py
  -> POST /api/ingest/instances
  -> POST /api/runs
  -> PATCH /api/runs
  -> POST /api/logs/batch
  -> POST /api/runs/{run_id}/snapshots
  -> publisher RabbitMQ
  -> remote_api/workers/service.py
  -> crud.py
  -> PostgreSQL
```

## Fluxo de controle remoto

```text
Dashboard
  -> POST /api/commands/run-now
  ou schedule checker interno
  -> cria command
  -> ws_manager.send_command(host_id, payload)
  -> agent recebe execute/kill
  -> agent responde ack/started/completed/failed/cancelled
  -> API atualiza command
  -> API tenta reconciliar run aberta da mesma instancia
```

## Schedule checker

O loop de schedule checker vive em `remote_api/main.py` e:

- busca schedules vencidos
- evita duplicacao por minuto com `schedule_already_dispatched`
- respeita `execution_mode=sequential`
- cria `commands` com `created_by="scheduler"`
- envia o comando ao host se o agent estiver conectado

## Reconciliacao de run orfa

Quando o agent informa fim/falha/cancelamento e nao ha vinculo forte com `run_id`, a API usa inferencia temporal em `agent_ws._close_orphan_run()`:

- mesma `automation_instance_id`
- `finished_at` ainda nulo
- `started_at >= command.created_at`

Isso e util operacionalmente, mas nao e um vinculo deterministico absoluto.

## Workers e filas

### Filas padrao

- `logger.instances`
- `logger.runs`
- `logger.logs`
- `logger.snapshots`

### Worker

- `remote_api/workers/service.py`
  - consome as quatro filas em paralelo
  - usa `session_scope()`
  - descarta mensagens invalidas
  - faz retry simples para erro de processamento

## Configuracao

- `remote_api/config.py`

### Variaveis principais

- `LOGGER_API_DATABASE_URL`
- `LOGGER_API_RABBITMQ_URL`
- `LOGGER_API_QUEUE_*`
- `LOGGER_API_API_PREFIX`
- `LOGGER_API_EMAIL_RETENTION_*`
- `LOGGER_API_RUN_STALE_*`
- `LOGGER_API_MINIO_*`
- `LOGGER_API_SCHEDULE_CHECKER_*`
- `LOGGER_API_COMMAND_EXPIRY_*`

### Defaults relevantes do codigo

- `api_prefix=/api`
- `run_stale_timeout_hours=0.5`
- `schedule_checker_interval_seconds=60`
- `command_expiry_hours=2`

## Arquivos que mais concentram regra de negocio

- `remote_api/crud.py`
- `remote_api/routes/insights.py`
- `remote_api/routes/schedules.py`
- `remote_api/routes/commands.py`
- `remote_api/routes/agent_ws.py`

## Ponto de atencao

Existe drift controlado entre `db/schema.sql` e o estado final do schema em runtime:

- `email_schema.py`
- `control_schema.py`

Em ambiente novo, o estado completo depende do SQL base e tambem do bootstrap da API.
