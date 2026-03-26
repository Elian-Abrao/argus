# Arquitetura
[Voltar ao indice](README.md)

## Componentes
- `logger/core/` - configuracao do logger, handlers e metadados.
- `logger/formatters/` - formatadores com cores e niveis customizados.
- `logger/handlers/` - handlers para console e arquivos.
- `logger/extras/` - utilitarios (timer, progress, lifecycle, metrics, captura de email).
- `remote_api/` - API FastAPI para ingest e consulta.
- `remote_dashboard/` - dashboard web (FastAPI + React SPA + proxy same-origin).
- `db/` - schema SQL usado pelos workers.

## Fluxo basico
```mermaid
graph TD
    A[App] --> B[start_logger]
    B --> C[Handlers]
    C --> D[Console]
    C --> E[Arquivos]
    B --> F[Extras]
```

## Fluxo remoto (opcional)
```mermaid
graph TD
    Bot --> API[Remote API]
    API --> MQ[RabbitMQ]
    MQ --> W[Workers]
    W --> PG[Postgres]
    API --> MINIO[MinIO anexos email]
    Dash[Dashboard] --> Proxy[/dashboard-api]
    Proxy --> API
```

## Fluxo de auditoria de email
```mermaid
sequenceDiagram
    participant Bot
    participant Logger
    participant API
    participant MinIO
    participant Dash

    Bot->>Logger: smtplib.sendmail/send_message
    Logger->>Logger: EMAIL_CAPTURE (metadados)
    Logger->>API: POST /runs/{run_id}/emails
    loop cada anexo
        Logger->>API: POST /runs/{run_id}/emails/{email_id}/attachments
        API->>MinIO: put_object
    end
    Dash->>API: GET /insights/runs/{run_id}/emails
    Dash->>API: GET /insights/emails/{email_id}/attachments/.../(preview|download)
```

## Sequencia tipica
```mermaid
sequenceDiagram
    participant App
    participant Logger
    participant Console
    participant File

    App->>Logger: start_logger()
    Logger->>Console: banner de inicio
    loop processamento
        App->>Logger: info/debug
        Logger->>File: grava log
        Logger->>Console: imprime
    end
    App->>Logger: end()
    Logger->>Console: banner final
```
