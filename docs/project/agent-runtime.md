# Agent Runtime

## Escopo

O diretorio `agent/` contem o runtime que roda nas maquinas remotas e executa as automacoes sob comando da API.

## Funcao do agent

- descobrir automacoes locais
- identificar o host na API
- manter WebSocket persistente com a API
- receber comandos `execute` e `kill`
- executar subprocessos
- enviar heartbeats e status de execucao

## Arquivos principais

- `agent/run.py`
  - entrada principal
- `agent/config.py`
  - carga de configuracao
- `agent/connection.py`
  - conexao WebSocket e protocolo
- `agent/executor.py`
  - execucao e cancelamento de subprocessos
- `agent/scanner.py`
  - scan de diretorios por `logger_config.json`
- `agent/venv_resolver.py`
  - resolve o Python do venv da automacao

## Bootstrap

O agent precisa de:

- `agent_config.json`
  ou
- `AGENT_API_URL`

## Configuracao

### Campos principais

- `api_url`
- `scan_dirs`
- `scan_depth`
- `heartbeat_interval`
- `reconnect_base_delay`
- `reconnect_max_delay`

### Comportamento default

Se `scan_dirs` nao for informado, o agent usa os diretorios irmaos da propria pasta `agent/`.

## Scan de automacoes

- procura `logger_config.json`
- ignora diretorios como `.venv`, `node_modules`, `.git`, `dist`, `build`
- tenta extrair:
  - `automation.code`
  - `available_args`

Esse resultado e enviado para a API como `scan_result`.

## Identificacao do host

O fluxo esperado e:

1. descobrir `hostname`/IP local
2. chamar `GET /api/agent/identify`
3. receber `host_id`
4. abrir `WS /api/agent/ws/{host_id}`

## Protocolo WebSocket

### Mensagens recebidas do servidor

- `execute`
- `kill`
- `scan_request`

### Mensagens enviadas pelo agent

- `heartbeat`
- `scan_result`
- `ack`
- `started`
- `completed`
- `failed`
- `cancelled`

## Execucao de comandos

- `executor.execute()`
  - resolve o Python do venv
  - monta `[python, script] + args`
  - executa com `start_new_session=True`
  - drena `stderr` em background
  - suporta `execution_mode=sequential`

## Cancelamento

- `kill(command_id)`
  - tenta matar o grupo de processo inteiro com `SIGTERM`
  - fallback para `proc.terminate()`

## Heartbeat

O agent envia heartbeat periodico com lista de comandos rodando. A API usa isso para atualizar `hosts.last_agent_ping`.

## Limitacoes e observacoes

- o agent nao cria a run diretamente; a run nasce do logger dentro da automacao
- por isso a API precisa reconciliar runs por inferencia temporal em alguns casos
- `agent/README.md` ainda estava placeholder na data desta documentacao; o mapa confiavel e este arquivo
