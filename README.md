# Argus

<p align="center">
  <img src="assets/readme/argus.png" alt="Argus" width="180" />
</p>

Argus is an open source, self-hosted platform for monitoring and operating RPA and automation workloads.

It brings execution history, structured logs, schedules, remote actions, and operational context into one place, so teams can understand what is running, what failed, and what needs attention without stitching together scripts, terminals, and spreadsheets.

Argus is built for teams that run automations in production and want better observability, control, and ownership over their automation stack.

## Why Argus

- Centralized visibility for automation and RPA runs
- Structured logs, statuses, snapshots, and execution history
- Web dashboard for operations and troubleshooting
- Scheduling and remote execution from a single interface
- Embedded AI assistant for natural-language exploration of run data
- Self-hosted architecture for teams that want control over infrastructure and data

## Quick Start

```bash
cp .env.example .env
docker network create proxy-net
docker compose up -d
docker compose exec argus-api python -m scripts.create_admin
```

After startup, access the Argus dashboard through your configured reverse proxy.

Use `.env.example` as the reference for required environment variables and `nginx/logger_nginx.conf` as the base template for proxy setup.

The project includes:

- Python services for ingestion, workers, and remote agents
- A React dashboard for operations
- An AI assistant service connected to your runtime data
- Docker-based local and production-friendly deployment

## License

[MIT](LICENSE)
