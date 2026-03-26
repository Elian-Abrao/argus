# Changelog

## [Unreleased]
- Captura automatica de emails via `smtplib` no logger (`capture_emails=True` por padrao).
- Envio de auditoria de email para a API remota (evento + anexos).
- Persistencia de anexos no MinIO com metadata em `email_events`/`email_attachments`.
- Endpoints de ingestao de email:
  - `POST /api/runs/{run_id}/emails`
  - `POST /api/runs/{run_id}/emails/{email_id}/attachments`
- Endpoints de consulta de email no insights:
  - `GET /api/insights/runs/{run_id}/emails`
  - `GET /api/insights/emails/{email_id}/attachments/{attachment_id}/download`
  - `GET /api/insights/emails/{email_id}/attachments/{attachment_id}/preview`
- Rotina de retencao automatica para dados de email expirados.
- Dashboard atualizado para consumir anexos via proxy same-origin (`/dashboard-api/*`).
- Documentacao reorganizada e expandida para o novo fluxo.

## [0.1.0]
- Estrutura basica do pacote.
- Handlers e formatadores customizados.
- Modulo de metricas e monitoramento.
