# Instalacao
[Voltar ao indice](README.md)

## Requisitos
- Python >= 3.8
- Acesso a internet para instalar dependencias (ou cache local)

## Instalar para desenvolvimento
```bash
pip install -e .[dev]
```

## Instalar apenas runtime
```bash
pip install -e .
```

## Instalar com API remota
```bash
pip install -e .[api]
```

## Subir stack completo (API + dashboard + MinIO)
Com Docker Compose:
```bash
cp .env.example .env
docker compose up -d postgres rabbitmq minio logger-api logger-workers logger-dashboard
```

Variaveis novas relevantes:
- `LOGGER_API_EMAIL_RETENTION_DAYS_DEFAULT`
- `LOGGER_API_EMAIL_RETENTION_CLEANUP_ENABLED`
- `LOGGER_API_RUN_STALE_CLEANUP_ENABLED`
- `LOGGER_API_RUN_STALE_TIMEOUT_HOURS`
- `LOGGER_API_RUN_STALE_CLEANUP_INTERVAL_SECONDS`
- `LOGGER_API_RUN_STALE_CLEANUP_BATCH_SIZE`
- `LOGGER_API_MINIO_ENDPOINT`
- `LOGGER_API_MINIO_ACCESS_KEY`
- `LOGGER_API_MINIO_SECRET_KEY`
- `LOGGER_API_MINIO_BUCKET`
- `LOGGER_API_MINIO_SECURE`
- `LOGGER_MINIO_API_HOST_PORT` (porta exposta no host para API S3 do MinIO, padrao `9010`)
- `LOGGER_MINIO_CONSOLE_HOST_PORT` (porta exposta no host para console do MinIO, padrao `9011`)

Para rodar o dashboard fora de container, gere o build React:
```bash
npm --prefix remote_dashboard/frontend ci
npm --prefix remote_dashboard/frontend run build
uvicorn remote_dashboard.main:app --reload --port 8200
```

## Ambiente reproduzivel
Se precisar fixar exatamente as versoes usadas no projeto:
```bash
pip install -r requirements.lock
```

## Estrutura de logs
Por padrao os logs sao gravados em `Logs/` e `LogsDEBUG/`.
Use `log_dir` para trocar o diretorio:
```python
from logger import start_logger

logger = start_logger("Demo", log_dir="/var/log/minha-app")
```

## Azure Artifacts
Se voce instala via feed privado, configure o pip:
```
[global]
index-url=https://pkgs.dev.azure.com/qualysystem/RPA/_packaging/Logger-Seed/pypi/simple/
```

Opcionalmente, configure `.pypirc` para publicar:
```
[distutils]
index-servers =
  Logger-Seed

[Logger-Seed]
repository = https://pkgs.dev.azure.com/qualysystem/RPA/_packaging/Logger-Seed/pypi/upload/
```
