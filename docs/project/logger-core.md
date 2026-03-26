# Logger Core

## Escopo

O modulo `logger/` e a biblioteca instalada dentro das automacoes. Ele estende `logging.Logger` com recursos operacionais, observabilidade e integracao remota.

## Ponto de entrada

- `logger/core/logger_core.py`
  - `start_logger()`
  - `start_logger_from_config()`

## Responsabilidades principais

- configurar handlers de console e arquivo
- aplicar formatters customizados
- injetar contexto em registros
- registrar banners de ciclo de vida
- habilitar extras opcionais
- enviar dados para a API remota quando `remote_sink` esta ativo
- capturar eventos de e-mail enviados por `smtplib`

## Estrutura relevante

- `logger/core/`
  - bootstrap, contexto e composicao do logger
- `logger/formatters/`
  - formatacao visual de logs
- `logger/handlers/`
  - handler de progresso
- `logger/extras/`
  - recursos adicionais como progress, monitoring, metrics, email capture e remote sink
- `logger/extras/base_funcs/`
  - helpers auxiliares

## Extras mais importantes

- `progress.py`
  - barras de progresso seguras para console
- `logger_lifecycle.py`
  - banners de inicio/fim
- `metrics.py` e `monitoring.py`
  - snapshots de sistema e medicao
- `printing.py`
  - captura de `print()`
- `email_capture.py`
  - intercepta `smtplib.SMTP.sendmail`
- `remote_sink.py`
  - envio em lote para `remote_api`

## Remote sink

O `remote_sink` e a ponte entre a automacao e a stack remota.

### O que ele envia

- registro/atualizacao de `automation_instance`
- eventos de `run`
- batches de `log_entries`
- snapshots estruturados
- eventos de e-mail e anexos

### Caracteristicas

- fila thread-safe local
- flush em lote
- sem dependencia de async no codigo da automacao
- permite operar em contexto sync e async

## Captura de e-mails

O sistema de captura de e-mails:

- intercepta `sendmail`
- persiste metadados de destinatarios, corpo e status
- sobe anexos para MinIO quando integracao remota esta habilitada

## Configuracao

### Arquivos relevantes

- `logger_config.json`
- `logger/cli/demo.py`
- `README.md`
- `docs/advanced_config.md`
- `docs/start_logger_from_config.md`

### Ponto de atencao

O repositorio menciona `logger_config.example.json` em documentacao antiga, mas o arquivo visivel hoje e `logger_config.json`.

## Testes

- `logger/tests/`
  - cobre comportamentos da biblioteca e extras principais

## Onde buscar cada tipo de informacao

- bootstrap do logger: `logger/core/logger_core.py`
- contexto e monkey-patching: `logger/core/context.py`
- envio remoto: `logger/extras/remote_sink.py`
- captura de e-mail: `logger/extras/email_capture.py`
- helpers e utilitarios: `logger/extras/`
