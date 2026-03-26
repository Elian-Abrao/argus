# Configuracao Avancada
[Voltar ao indice](README.md)

Este guia detalha os parametros do `start_logger` e como ajustar comportamento
para batch jobs, servicos de longa duracao e envio remoto.

## Parametros principais

| Parametro | Padrao | Descricao |
|---|---|---|
| `name` | `None` | Nome do logger e base do arquivo `.log`. |
| `log_dir` | `"Logs"` | Diretorio principal dos logs. |
| `console_level` | `"INFO"` | Nivel mostrado no console. |
| `file_level` | `"DEBUG"` | Nivel gravado em arquivos. |
| `capture_prints` | `True` | Redireciona `print` para o logger. |
| `capture_emails` | `True` | Captura envios via `smtplib.sendmail/send_message`. |
| `email_retention_days` | `None` | Retencao (dias) para auditoria de email no remote sink. |
| `verbose` | `0` | Niveis de detalhamento nos arquivos. |
| `show_all_leaks` | `False` | Mostra todas as diferencas na checagem de memoria. |
| `watch_objects` | `None` | Tipos a monitorar em vazamentos. |
| `cleanup_days` | `None` | Remove logs antigos em `log_dir` e `LogsDEBUG`. |
| `server_mode` | `False` | Evita snapshot inicial (servicos). |
| `rotation_interval` | `None` | Intervalo para rotacao temporal. |
| `rotation_unit` | `"hours"` | Unidade da rotacao (`minutes`, `hours`, `days`). |
| `remote_sink` | `None` | Envio remoto para a API. |

## Verbose
- `0`: formato simples no arquivo.
- `1`: adiciona call chain.
- `2`: adiciona `pathname:lineno` + call chain.
- `3+`: adiciona thread + detalhes maximos.

## Ciclo de vida
`start_logger` chama `logger.start()` automaticamente e registra `logger.end()`
via `atexit`.

Se precisar executar manualmente:
```python
logger.start(verbose=1)  # type: ignore[attr-defined]
# ... processamento ...
logger.end(verbose=2)  # type: ignore[attr-defined]
```

## Modo servidor
Para servicos que ficam ativos por tempo indefinido:
```python
logger = start_logger("API", server_mode=True)
```

## Rotacao + limpeza
```python
logger = start_logger(
    "Service",
    rotation_interval=12,
    rotation_unit="hours",
    cleanup_days=30,
)
```

## Remote sink
Quando habilitado, o logger envia lotes para a Remote API.
```python
logger = start_logger(
    "Bot",
    capture_emails=True,
    email_retention_days=7,
    remote_sink={
        "enabled": True,
        "endpoint": "http://localhost:8100/api",
        "automation": {"code": "InvoiceBot", "name": "Invoice Bot"},
        "client": {"name": "Cliente XPTO", "external_code": "XPTO"},
        "host": {"environment": "prod"},
        "deployment_tag": "prod-01",
        "batch_size": 25,
        "flush_interval": 0.5,
        "email_retention_days": 7,
    },
)
```

Notas:
- `capture_emails=True` ativa um patch global no `smtplib` para o processo atual.
- O logger emite `EMAIL_CAPTURE ...` em JSON no proprio log.
- Com `remote_sink` ativo, evento e anexos sao enviados para a API.
- `email_retention_days` em `start_logger` vira default para o `remote_sink` quando nao informado no bloco `remote_sink`.

## Configuracao via JSON
1) Copie o exemplo:
```bash
cp logger_config.example.json logger_config.json
```

2) Carregue no codigo:
```python
from logger import start_logger_from_config

logger = start_logger_from_config(
    "logger_config.json",
    overrides={"console_level": "WARNING"},
)
```

Chaves desconhecidas levantam `ValueError` para evitar typos silenciosos.

Exemplo com captura de email:
```json
{
  "name": "Bot",
  "capture_emails": true,
  "email_retention_days": 7,
  "remote_sink": {
    "enabled": true,
    "endpoint": "http://localhost:8100/api",
    "automation": {"code": "InvoiceBot", "name": "Invoice Bot"}
  }
}
```
