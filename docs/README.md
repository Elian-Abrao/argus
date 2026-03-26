# Documentacao
[Voltar ao README principal](../README.md)

Indice navegavel para tudo em `docs/`.

## Comece por aqui
- [Quickstart](quickstart.md) - instalacao + primeiro logger.
- [Examples](examples.md) - snippets prontos.
- [Advanced Config](advanced_config.md) - parametros e comportamento.
- [start_logger_from_config](start_logger_from_config.md) - guia completo do helper.

## Arquitetura e internals
- [Architecture](architecture.md) - modulos e fluxo de dados.
- [API Reference](api_reference.md) - metodos e helpers.
- [Performance](performance.md) - volume alto e tuning.
- [Troubleshooting](troubleshooting.md) - erros comuns.

## Servicos remotos
- [Remote API](remote_api.md) - ingest, insights, workers.
- [Security](security.md) - hardening e boas praticas.

Destaques recentes:
- Captura automatica de emails enviados via `smtplib`.
- Auditoria de emails por run no dashboard (corpo, destinatarios, status e anexos).
- Persistencia de anexos no MinIO com retencao configuravel.

## Contribuicao
- [Developer Guide](developer_guide.md)
- [Tests](tests.md)
- [Changelog](changelog.md)

## Gerar HTML
```bash
make -C docs html
```
