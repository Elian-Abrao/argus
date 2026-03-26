# Seguranca
[Voltar ao indice](README.md)

## Boas praticas
- Nunca exponha logs com dados sensiveis.
- Restrinja `/api/insights` e `/docs` a redes internas (VPN/allowlist).
- Restrinja tambem o dashboard (`/` e rotas SPA) para rede interna/VPN.
- Use HTTPS no Nginx.
- Separe ambiente de testes e producao.
- Troque credenciais padrao do MinIO e use bucket dedicado.
- Evite manter credenciais SMTP hardcoded em codigo fonte.

## Nginx (exemplo)
- Ingest publicamente.
- Dashboard e insights apenas na VPN.

Consulte `docs/remote_api.md` para mais contexto do fluxo remoto.
