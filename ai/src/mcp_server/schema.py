from __future__ import annotations

SCHEMA_CONTEXT = """\
Banco: PostgreSQL (`logger_db`)

Contexto atual:
- esta versao trabalha somente com o banco de dados
- banco focado em monitoramento operacional de automacoes executadas para clientes
- trate qualquer hipotese como hipotese ate confirmar com discovery
- use sempre nomes de tabela simples sem prefixo de schema (ex: `clients`, nao `public.clients`)

Tabelas confirmadas:
- `automation_instances`
- `automations`
- `clients`
- `commands`
- `email_attachments`
- `email_events`
- `hosts`
- `log_entries`
- `run_snapshots`
- `runs`
- `scheduled_jobs`

Heuristicas confiaveis:
- use `search_objects` antes de escrever SQL analitico
- explore `information_schema` e `pg_catalog` para entender schemas, tabelas e colunas
- nao assuma relacoes, significados de campos ou regras de negocio sem validar
- use amostras pequenas antes de fazer joins ou agregacoes
- prefira consultas com poucas colunas e `LIMIT`
- prefira tabelas base para analises oficiais: `automations`, `automation_instances`, `clients`, `hosts`, `runs`, `log_entries`, `run_snapshots`, `commands`, `scheduled_jobs`, `email_events`, `email_attachments`
- `log_entries` tem granularidade muito maior que `runs`

Relacionamentos principais:
- `automation_instances.automation_id -> automations.id`
- `automation_instances.client_id -> clients.id`
- `automation_instances.host_id -> hosts.id`
- `runs.automation_instance_id -> automation_instances.id`
- `scheduled_jobs.automation_instance_id -> automation_instances.id`
- `commands.automation_instance_id -> automation_instances.id`
- `commands.host_id -> hosts.id`
- `commands.run_id -> runs.id`
- `commands.scheduled_job_id -> scheduled_jobs.id`
- `email_events.run_id -> runs.id`
- `email_attachments.email_event_id -> email_events.id`
- `log_entries.run_id -> runs.id`
- `run_snapshots.run_id -> runs.id`

Tabelas e papéis:
- `automations`: cadastro mestre da automacao
- `automation_instances`: elo central entre automacao, cliente, host e execucao
- `runs`: tabela fato principal de monitoramento operacional
- `log_entries`: logs detalhados por run
- `run_snapshots`: snapshots estruturados da run
- `commands`: comandos disparados
- `scheduled_jobs`: agendamentos
- `email_events`: e-mails gerados por runs
- `email_attachments`: anexos de e-mails

Valores observados que precisam de cautela:
- `runs.status`: `completed`, `stopped`, `failed`, `running`
- `commands.status`: `cancelled`, `completed`, `failed`
- `email_events.status`: `enviado`
- `scheduled_jobs.recurrence_type`: `daily`
- esses valores sao observados, nao enums definitivos

Caso critico de troubleshooting:
- quando a pergunta for "qual foi o erro na automacao X", localize a automacao, as instancias e a run mais recente
- consulte pelo menos os ultimos 20 logs dessa run
- consulte tambem os ultimos 5 logs com nivel de erro ou critico dessa run
- se necessario, consulte mais logs, snapshots, commands e email_events da mesma run
"""


def get_schema_context() -> str:
    return SCHEMA_CONTEXT


__all__ = ["get_schema_context", "SCHEMA_CONTEXT"]
