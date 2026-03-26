# API Reference
[Voltar ao indice](README.md)

## start_logger
```python
start_logger(
    name=None,
    log_dir="Logs",
    console_level="INFO",
    file_level="DEBUG",
    capture_prints=True,
    capture_emails=True,
    email_retention_days=None,
    verbose=0,
    show_all_leaks=False,
    watch_objects=None,
    cleanup_days=None,
    server_mode=False,
    rotation_interval=None,
    rotation_unit="hours",
    remote_sink=None,
) -> logging.Logger
```

Cria e devolve um `logging.Logger` configurado com handlers, formatacao e
metodos auxiliares.

## start_logger_from_config
```python
start_logger_from_config(config, overrides=None) -> logging.Logger
```
Carrega um JSON (ou dict) e chama `start_logger`. Chaves desconhecidas
lancam `ValueError`.

## Metodos adicionados ao Logger
Depois de `start_logger`, o logger exposto ganha metodos utilitarios:
- `start()` / `end()` - banners de ciclo de vida.
- `progress(iterable, desc=...)` - barra de progresso.
- `timer(label)` - contexto de medicao.
- `sleep(seconds)` - pausa com log (útil em jobs batch).
- `capture_prints(enabled=True)` - redireciona `print`.
- `capture_emails(active=True, include_body=True, max_body_chars=12000)` - intercepta envios via `smtplib`.
- `screen()` - log voltado ao console.
- `path()` / `debug_path()` - caminho dos arquivos de log.
- `cleanup()` - limpeza manual de logs antigos.
- `pause()` - pausa interativa (quando aplicavel).

Observacao: alguns metodos podem variar conforme extras habilitados.

## Captura de email (extras)
- Context manager: `logger.extras.capture_emails(logger, include_body=True, max_body_chars=12000)`
- Metodo no logger: `logger.capture_emails(...)`
- Evento gerado: `EMAIL_CAPTURE {json}` com campos como:
  - `destinatarios`
  - `destinatarios_copia_oculta`
  - `assunto`
  - `corpo.texto` / `corpo.html` (quando `include_body=True`)
  - `paths_arquivos`
  - `status` (`enviado` ou `falha`)
