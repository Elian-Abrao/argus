# Documentacao Interna do Projeto

Esta pasta organiza a documentacao do Argus por responsabilidade.

## Como navegar

- `logger-core.md`
  - biblioteca `logger/`, bootstrap, extras, remote sink e captura de e-mails
- `backend-api.md`
  - servico `remote_api/`, camadas, filas, workers, controle remoto e loops de manutencao
- `frontend-dashboard.md`
  - servico `remote_dashboard/`, SPA React, rotas, paginas e componentes principais
- `ai-assistant.md`
  - modulo `ai/`, assistente de linguagem natural, loop agentico, ferramentas e deploy
- `agent-runtime.md`
  - runtime `agent/`, bootstrap, scan, websocket, execucao de comandos e cancelamento
- `data-model.md`
  - tabelas, relacoes, schema base, bootstrap complementar e entidades principais
- `infrastructure-and-ops.md`
  - Docker, Nginx, redes, servicos, variaveis e operacao local/producao
- `endpoints-and-flows.md`
  - inventario de endpoints HTTP/WS e fluxos ponta a ponta

## Visao geral do sistema

O repositorio tem cinco blocos principais:

1. `logger/`
   - biblioteca Python usada dentro das automacoes
   - gera logs locais e pode enviar telemetria remota
2. `remote_api/`
   - FastAPI para ingestao, consulta, agendamentos, comandos e comunicacao com agents
3. `remote_dashboard/`
   - FastAPI + React SPA para operacao e observabilidade
4. `ai/`
   - assistente de linguagem natural que consulta o banco em tempo real
5. `agent/`
   - cliente que roda na maquina remota e executa comandos enviados pela API

## Fluxo macro

```text
Automacao Python
  -> logger/start_logger
  -> remote_sink (opcional)
  -> remote_api (/api)
  -> RabbitMQ (ingestao)
  -> workers
  -> PostgreSQL + MinIO
  -> dashboard (/dashboard-api -> /api)

Dashboard/usuario
  -> cria agendamentos ou run-now
  -> remote_api cria commands
  -> agent conectado por WebSocket recebe execute/kill
  -> agent responde ack/started/completed/failed/cancelled
  -> API atualiza command e reconcilia run
```

## Observacoes importantes

- O projeto tem documentacao historica em `docs/`, mas esta pasta reune um mapa mais pratico do estado atual do codigo.
- Parte do schema de banco nao esta apenas em `db/schema.sql`; ha bootstrap adicional em runtime.
- O dashboard consome a API sempre via proxy same-origin em `/dashboard-api`.
- O `scheduled_job_id` identifica o agendamento recorrente, nao uma ocorrencia unica do calendario.
