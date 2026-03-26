# Modelo de Dados

## Fonte do schema

O estado do banco vem da combinacao de:

- `db/schema.sql`
- `remote_api/email_schema.py`
- `remote_api/control_schema.py`
- `remote_api/models.py`

## Cadeia principal de entidades

```text
Client
  -> Host
  -> Automation
  -> AutomationInstance
  -> Run
  -> LogEntry / RunSnapshot / EmailEvent
  -> EmailAttachment

Controle remoto:
AutomationInstance
  -> ScheduledJob
  -> Command
  -> (opcionalmente) Run
```

## Entidades principais

### `clients`

- empresa/cliente final
- chaves:
  - `id`
  - `name`
  - `external_code`

### `hosts`

- maquina/ambiente que executa automacoes
- chaves:
  - `id`
  - `hostname`
  - `ip_address`
  - `root_folder`
  - `environment`
- extensao posterior:
  - `last_agent_ping`

### `automations`

- catalogo de automacoes
- chaves:
  - `id`
  - `code`
  - `name`

### `automation_instances`

- representa uma implantacao de uma automacao em um cliente/host
- relaciona:
  - `automation_id`
  - `client_id`
  - `host_id`
- campos operacionais:
  - `deployment_tag`
  - `config_signature`
  - `first_seen_at`
  - `last_seen_at`
- extensoes usadas pelo controle remoto:
  - `script`
  - `default_args`
  - `available_args`

### `runs`

- execucao individual
- chaves:
  - `automation_instance_id`
  - `started_at`
  - `finished_at`
  - `status`
- metadados:
  - `pid`
  - `user_name`
  - `server_mode`
  - `host_ip`
  - `root_folder`
  - `config_version`

### `log_entries`

- logs estruturados de uma run
- cardinalidade:
  - muitos por `run`
- campos:
  - `sequence`
  - `ts`
  - `level`
  - `message`
  - `context`
  - `extra`

### `run_snapshots`

- blocos estruturados de estado/perfiling
- ligados a uma `run`

### `email_events`

- auditoria de e-mails enviados por uma run
- campos:
  - `subject`
  - `body_text`
  - `body_html`
  - `recipients`
  - `bcc_recipients`
  - `status`
  - `retention_days`
  - `expires_at`

### `email_attachments`

- anexos associados a `email_events`
- payload binario vai para MinIO
- banco guarda metadado e `storage_key`

### `scheduled_jobs`

- agendamentos recorrentes
- campos:
  - `automation_instance_id`
  - `script`
  - `args`
  - `recurrence_type`
  - `recurrence_config`
  - `execution_mode`
  - `enabled`
  - `timezone`

### `commands`

- fila de comandos de execucao remota
- pode nascer de:
  - `run-now`
  - scheduler interno
- campos:
  - `host_id`
  - `automation_instance_id`
  - `scheduled_job_id`
  - `status`
  - `run_id`
  - `created_by`
  - `acked_at`
  - `started_at`
  - `finished_at`

## Views auxiliares

- `host_automations`
- `client_automations`

## Ponto de atencao sobre nomes

Ha diferenca entre SQL base e modelos Python em alguns campos:

- `db/schema.sql`
  - usa `metadata` em `automation_instances` e `runs`
- `remote_api/models.py`
  - usa `attributes`

Isso mostra que o schema evoluiu ao longo do tempo e precisa ser lido junto com o bootstrap complementar.

## Regra importante para schedules

O `scheduled_job_id` identifica o agendamento recorrente, nao uma ocorrencia concreta do calendario. As ocorrencias concretas sao expandidas em `GET /schedules/calendar`.

## Onde buscar detalhes

- SQL bruto e indices: `db/schema.sql`
- shape ORM usado pela API: `remote_api/models.py`
- contratos JSON: `remote_api/schemas.py`
