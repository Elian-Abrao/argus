"""Purge all logger-related queues from RabbitMQ management API."""

from __future__ import annotations

import os
from urllib.parse import quote

import requests
from requests.auth import HTTPBasicAuth


RABBIT_API = os.environ.get("LOGGER_PURGE_RABBIT_API", "http://10.0.5.30:15678")
RABBIT_VHOST = os.environ.get("LOGGER_PURGE_RABBIT_VHOST", "/")
RABBIT_USER = os.environ.get("LOGGER_PURGE_RABBIT_USER", "guest")
RABBIT_PASS = os.environ.get("LOGGER_PURGE_RABBIT_PASS", "guest")
QUEUE_NAMES = [
    "logger.instances",
    "logger.runs",
    "logger.logs",
    "logger.snapshots",
]


def purge_queue(queue: str) -> None:
    url = f"{RABBIT_API}/api/queues/{quote(RABBIT_VHOST, safe='')}/{queue}/contents"
    resp = requests.delete(url, auth=HTTPBasicAuth(RABBIT_USER, RABBIT_PASS), timeout=10)
    resp.raise_for_status()
    print(f"Fila {queue} purgada com sucesso.")


def main() -> None:
    for queue in QUEUE_NAMES:
        purge_queue(queue)


if __name__ == "__main__":
    # Caso queira limpar tbm os dados das tabelas, execute: 
    # docker compose exec postgres psql -U logger -d logger_db -c "TRUNCATE TABLE run_snapshots, log_entries, runs, automation_instances, automations, hosts, clients RESTART IDENTITY CASCADE;"
    main()
