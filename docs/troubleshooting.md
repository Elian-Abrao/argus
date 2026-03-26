# Troubleshooting
[Voltar ao indice](README.md)

## Problemas comuns

| Sintoma | Causa provavel | Solucao |
|---|---|---|
| `ModuleNotFoundError` | Dependencias faltando | Reinstale com `pip install -e .[dev]` |
| `Permission denied` ao gravar | Pasta sem permissao | Troque `log_dir` ou ajuste permissoes |
| Nao aparece no console | `console_level` alto | Use `console_level="INFO"` |
| Logs remotos nao chegam | API/worker fora do ar | Verifique RabbitMQ e workers |
| Emails nao aparecem no dashboard | `capture_emails` desativado ou `remote_sink` sem conexao | Ative `capture_emails=True` e valide `remote_sink.endpoint` |
| Erro ao enviar anexo de email | MinIO indisponivel ou credencial incorreta | Verifique `LOGGER_API_MINIO_*` e status do container MinIO |
| Dashboard retorna `Frontend build nao encontrado` | `dist` do frontend inexistente | Execute `npm --prefix remote_dashboard/frontend run build` |
| `/docs` retorna 403 | Nginx bloqueando | Libere `/docs` para a rede correta |

## Dicas rapidas
- Confira `log_path` e `debug_log_path` no logger.
- Em producao, mantenha console em `INFO` e arquivo em `DEBUG`.
- Para servicos longos, use `server_mode=True`.
