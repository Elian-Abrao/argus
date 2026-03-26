"""Entry point: python -m agent"""

from __future__ import annotations

import asyncio
import json
import logging
import socket
import sys
import urllib.request
import urllib.error
import urllib.parse

from .config import load_config
from .connection import AgentConnection
from .executor import Executor


def _discover_host_id(api_url: str) -> str:
    """Call GET /agent/identify to resolve the local hostname into a host_id."""
    hostname = socket.gethostname()
    ip_address = _get_local_ip()

    params = {}
    if hostname:
        params["hostname"] = hostname
    if ip_address:
        params["ip_address"] = ip_address

    url = f"{api_url.rstrip('/')}/agent/identify?{urllib.parse.urlencode(params)}"
    logging.getLogger("agent").info(
        "Identificando host — hostname=%s, ip=%s", hostname, ip_address
    )

    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            host_id = data["host_id"]
            logging.getLogger("agent").info(
                "Host identificado — id=%s (%s)", host_id, data.get("hostname")
            )
            return host_id
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        logging.getLogger("agent").error(
            "API retornou %s ao identificar host: %s", exc.code, body
        )
        print(
            f"\nErro: não foi possível identificar este host na API.\n"
            f"  hostname={hostname}, ip={ip_address}\n"
            f"  Resposta: {exc.code} — {body}\n\n"
            f"Verifique se este host já possui execuções registradas no sistema.\n",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as exc:
        logging.getLogger("agent").error("Falha ao conectar na API: %s", exc)
        print(
            f"\nErro: falha de conexão com a API em {api_url}\n  {exc}\n",
            file=sys.stderr,
        )
        sys.exit(1)


def _get_local_ip() -> str | None:
    """Best-effort local IP discovery."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger("agent")

    config = load_config()
    logger.info("API: %s", config.api_url)
    logger.info("Diretorios de scan: %s", config.scan_dirs)

    host_id = _discover_host_id(config.api_url)

    executor = Executor()
    connection = AgentConnection(config, host_id, executor)

    try:
        asyncio.run(connection.run_forever())
    except KeyboardInterrupt:
        logger.info("Agente encerrado pelo usuario")
        sys.exit(0)


if __name__ == "__main__":
    main()
