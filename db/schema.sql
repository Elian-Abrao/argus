-- Logger remote ingestion schema
-- Requer PostgreSQL 13+ e extensão pgcrypto para geração de UUIDs

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Clientes finais (empresas que contratam as automações)
CREATE TABLE IF NOT EXISTS clients (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name            text        NOT NULL,
    external_code   text,
    contact_email   text,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (name)
);
CREATE UNIQUE INDEX IF NOT EXISTS clients_external_code_uidx
    ON clients (external_code) WHERE external_code IS NOT NULL;

-- Máquinas/ambientes onde as automações são executadas
CREATE TABLE IF NOT EXISTS hosts (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    hostname        text,
    display_name    text,
    ip_address      inet,
    root_folder     text        NOT NULL,
    environment     text,
    tags            jsonb       NOT NULL DEFAULT '{}'::jsonb,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (ip_address, root_folder)
);

-- Catálogo de automações/projetos
CREATE TABLE IF NOT EXISTS automations (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code            text        NOT NULL,
    name            text        NOT NULL,
    description     text,
    owner_team      text,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (code)
);

-- Relaciona automação + cliente + host (instância implantada)
CREATE TABLE IF NOT EXISTS automation_instances (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    automation_id       uuid NOT NULL REFERENCES automations(id),
    client_id           uuid REFERENCES clients(id),
    host_id             uuid REFERENCES hosts(id),
    deployment_tag      text,
    config_signature    text,
    first_seen_at       timestamptz NOT NULL DEFAULT now(),
    last_seen_at        timestamptz,
    metadata            jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE UNIQUE INDEX IF NOT EXISTS automation_instances_uniq
    ON automation_instances (automation_id, client_id, host_id, coalesce(deployment_tag, ''));

-- Execuções individuais do logger
CREATE TABLE IF NOT EXISTS runs (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    automation_instance_id  uuid NOT NULL REFERENCES automation_instances(id),
    started_at              timestamptz NOT NULL DEFAULT now(),
    finished_at             timestamptz,
    status                  text        NOT NULL DEFAULT 'running',
    pid                     integer,
    user_name               text,
    server_mode             boolean     NOT NULL DEFAULT false,
    host_ip                 inet,
    root_folder             text,
    config_version          text,
    metadata                jsonb       NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS runs_instance_idx
    ON runs (automation_instance_id, started_at DESC);

-- Registros de log
CREATE TABLE IF NOT EXISTS log_entries (
    id              bigserial PRIMARY KEY,
    run_id          uuid        NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    sequence        bigint      NOT NULL,
    ts              timestamptz NOT NULL,
    level           text        NOT NULL,
    logger_name     text,
    message         text        NOT NULL,
    context         jsonb       NOT NULL DEFAULT '{}'::jsonb,
    extra           jsonb       NOT NULL DEFAULT '{}'::jsonb,
    created_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (run_id, sequence)
);
CREATE INDEX IF NOT EXISTS log_entries_run_ts_idx
    ON log_entries (run_id, ts);
CREATE INDEX IF NOT EXISTS log_entries_context_gin_idx
    ON log_entries USING GIN (context);
CREATE INDEX IF NOT EXISTS log_entries_extra_gin_idx
    ON log_entries USING GIN (extra);

-- Blocos estruturados (status do sistema, profiling, etc.)
CREATE TABLE IF NOT EXISTS run_snapshots (
    id              bigserial PRIMARY KEY,
    run_id          uuid        NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    snapshot_type   text        NOT NULL,
    taken_at        timestamptz NOT NULL DEFAULT now(),
    payload         jsonb       NOT NULL,
    UNIQUE (run_id, snapshot_type, taken_at)
);

-- Auditoria de e-mails enviados
CREATE TABLE IF NOT EXISTS email_events (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          uuid        NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    subject         text,
    body_text       text,
    body_html       text,
    recipients      jsonb       NOT NULL DEFAULT '[]'::jsonb,
    bcc_recipients  jsonb       NOT NULL DEFAULT '[]'::jsonb,
    source_paths    jsonb       NOT NULL DEFAULT '[]'::jsonb,
    status          text        NOT NULL DEFAULT 'enviado',
    error           text,
    retention_days  integer     NOT NULL DEFAULT 7,
    sent_at         timestamptz NOT NULL DEFAULT now(),
    expires_at      timestamptz NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS email_events_run_idx
    ON email_events (run_id, sent_at DESC);
CREATE INDEX IF NOT EXISTS email_events_expires_idx
    ON email_events (expires_at);

CREATE TABLE IF NOT EXISTS email_attachments (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email_event_id    uuid        NOT NULL REFERENCES email_events(id) ON DELETE CASCADE,
    filename          text        NOT NULL,
    mime_type         text,
    size_bytes        bigint      NOT NULL,
    storage_key       text        NOT NULL,
    source_path       text,
    preview_supported boolean     NOT NULL DEFAULT false,
    created_at        timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS email_attachments_event_idx
    ON email_attachments (email_event_id);

-- Agendamentos de execução remota
CREATE TABLE IF NOT EXISTS scheduled_jobs (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    automation_instance_id  uuid NOT NULL REFERENCES automation_instances(id),
    script                  text NOT NULL DEFAULT 'main.py',
    args                    jsonb NOT NULL DEFAULT '[]'::jsonb,
    recurrence_type         text NOT NULL,
    recurrence_config       jsonb NOT NULL DEFAULT '{}'::jsonb,
    execution_mode          text NOT NULL DEFAULT 'parallel',
    enabled                 boolean NOT NULL DEFAULT true,
    timezone                text NOT NULL DEFAULT 'America/Sao_Paulo',
    created_at              timestamptz NOT NULL DEFAULT now(),
    updated_at              timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS scheduled_jobs_instance_idx
    ON scheduled_jobs (automation_instance_id);
CREATE INDEX IF NOT EXISTS scheduled_jobs_enabled_idx
    ON scheduled_jobs (enabled) WHERE enabled = true;

-- Fila de comandos de execução remota
CREATE TABLE IF NOT EXISTS commands (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    host_id                 uuid NOT NULL REFERENCES hosts(id),
    automation_instance_id  uuid NOT NULL REFERENCES automation_instances(id),
    scheduled_job_id        uuid REFERENCES scheduled_jobs(id) ON DELETE SET NULL,
    script                  text NOT NULL DEFAULT 'main.py',
    args                    jsonb NOT NULL DEFAULT '[]'::jsonb,
    working_dir             text NOT NULL,
    execution_mode          text NOT NULL DEFAULT 'parallel',
    status                  text NOT NULL DEFAULT 'pending',
    run_id                  uuid REFERENCES runs(id),
    created_by              text NOT NULL DEFAULT 'user',
    created_at              timestamptz NOT NULL DEFAULT now(),
    acked_at                timestamptz,
    started_at              timestamptz,
    finished_at             timestamptz,
    result_message          text
);
CREATE INDEX IF NOT EXISTS commands_host_status_idx
    ON commands (host_id, status);
CREATE INDEX IF NOT EXISTS commands_instance_idx
    ON commands (automation_instance_id, created_at DESC);

-- Views auxiliares
CREATE OR REPLACE VIEW host_automations AS
SELECT
    h.id         AS host_id,
    h.hostname,
    h.ip_address,
    h.root_folder,
    h.environment,
    ai.id        AS automation_instance_id,
    a.code       AS automation_code,
    a.name       AS automation_name,
    ai.deployment_tag,
    ai.config_signature,
    ai.first_seen_at,
    ai.last_seen_at
FROM hosts h
JOIN automation_instances ai ON ai.host_id = h.id
JOIN automations a ON ai.automation_id = a.id;

CREATE OR REPLACE VIEW client_automations AS
SELECT
    c.id         AS client_id,
    c.name       AS client_name,
    a.code       AS automation_code,
    a.name       AS automation_name,
    ai.id        AS automation_instance_id,
    ai.deployment_tag,
    ai.first_seen_at,
    ai.last_seen_at
FROM clients c
JOIN automation_instances ai ON ai.client_id = c.id
JOIN automations a ON ai.automation_id = a.id;
