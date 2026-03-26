"""network.py - Monitoramento de conexoes e requisicoes."""

from typing import Dict, Any, Tuple, Optional
from logging import Logger, getLogger
from .dependency import DependencyManager, logger_log_environment
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
import time
import socket
import requests

from .progress import format_block

class NetworkMonitor:
    def __init__(self, timeout: float = 1.0, logger: Logger | None = None):
        self.timeout = timeout
        self.logger = logger or getLogger(__name__)
        self.metrics: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'total_requests': 0,
            'total_errors': 0,
            'total_bytes': 0,
            'latencies': [],
        })
        self._executor = ThreadPoolExecutor(max_workers=5)

    def _validate_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"URL inválida: {url}")

    def check_connection(self, host: str = "8.8.8.8", port: int = 53, timeout: float | None = None) -> Tuple[bool, Optional[float]]:
        timeout = timeout if timeout is not None else self.timeout
        try:
            start = time.time()
            socket.create_connection((host, port), timeout=timeout)
            return True, (time.time() - start) * 1000
        except OSError:
            return False, None

    def measure_latency(self, url: str, timeout: float | None = None) -> Dict[str, Any]:
        self._validate_url(url)
        timeout = timeout if timeout is not None else self.timeout
        try:
            start = time.time()
            response = requests.get(url, timeout=timeout)
            latency = (time.time() - start) * 1000
            domain = urlparse(url).netloc
            metrics = self.metrics[domain]
            metrics['total_requests'] += 1
            metrics['latencies'].append(latency)
            metrics['total_bytes'] += len(response.content)
            return {
                'latency': latency,
                'status_code': response.status_code,
                'content_size': len(response.content),
            }
        except requests.exceptions.Timeout as exc:
            domain = urlparse(url).netloc
            self.metrics[domain]['total_errors'] += 1
            self.logger.error(f"Timeout ao acessar {url}: {exc}")
            return {'error': str(exc), 'type': 'Timeout'}
        except requests.exceptions.ConnectionError as exc:
            domain = urlparse(url).netloc
            self.metrics[domain]['total_errors'] += 1
            msg = str(exc)
            if "NameResolutionError" in msg or "getaddrinfo failed" in msg:
                self.logger.warning(
                    f"Sem conectividade para resolver {domain}: {msg}"
                )
                return {"error": "sem conectividade", "type": "ConnectionError"}
            self.logger.error(f"Erro de conexão ao acessar {url}: {msg}")
            return {"error": msg, "type": "ConnectionError"}
        except requests.RequestException as exc:
            domain = urlparse(url).netloc
            self.metrics[domain]['total_errors'] += 1
            self.logger.error(f"Erro ao acessar {url}: {exc}")
            return {'error': str(exc), 'type': type(exc).__name__}
        except Exception as exc:  # pragma: no cover - unforeseen errors
            domain = urlparse(url).netloc
            self.metrics[domain]['total_errors'] += 1
            self.logger.exception(f"Falha inesperada ao acessar {url}: {exc}")
            return {'error': str(exc), 'type': 'Exception'}

def logger_check_connectivity(
    self: Logger,
    urls: str | list[str] | None = None,
    level: str = "INFO",
    timeout: float = 1.0,
    return_block: bool = False,
) -> str | None:
    """Testa a conectividade geral e opcionalmente múltiplas URLs."""
    connected, latency = self._net_monitor.check_connection(timeout=timeout)  # type: ignore[attr-defined]
    log_method = getattr(self, level.lower())
    linhas: list[str] = []
    if connected:
        linhas.append(f"Status: Conectado • Latência: {latency:.1f}ms")
    else:
        linhas.append("Sem conexão com a internet")
        bloco = format_block("CONECTIVIDADE", linhas)
        if return_block:
            return bloco
        log_method(f"\n{bloco}")
        return None

    urls_list: list[str]
    if urls is None:
        urls_list = ["https://www.google.com"]
    elif isinstance(urls, str):
        urls_list = [urls]
    else:
        urls_list = list(urls)

    for url in urls_list:
        try:
            metrics = self._net_monitor.measure_latency(url, timeout=timeout)  # type: ignore[attr-defined]
            if "latency" in metrics:
                linhas.append(f"URL Testada: {url}")
                linhas.append(
                    f"↳ Latência: {metrics['latency']:.1f}ms • Status: {metrics['status_code']} • Tamanho: {metrics['content_size']/1024:.1f}KB"
                )
            else:
                linhas.append(f"Erro ao acessar {url}: {metrics['error']}")
        except Exception as e:
            linhas.append(f"Erro ao testar {url}: {str(e)}")

    bloco = format_block("CONECTIVIDADE", linhas)
    if return_block:
        return bloco
    log_method(f"\n{bloco}")
    return None

def logger_get_network_metrics(self: Logger, domain: str | None = None) -> Dict[str, Any]:
    if domain:
        metrics = self._net_monitor.metrics[domain]  # type: ignore[attr-defined]
        if metrics['latencies']:
            avg_latency = sum(metrics['latencies']) / len(metrics['latencies'])
            metrics['average_latency'] = avg_latency
        return metrics
    return dict(self._net_monitor.metrics)  # type: ignore[attr-defined]

def _setup_dependencies_and_network(logger: Logger) -> None:
    dep_manager = DependencyManager()
    net_monitor = NetworkMonitor()
    setattr(logger, "_dep_manager", dep_manager)
    setattr(logger, "_net_monitor", net_monitor)
    setattr(Logger, "log_environment", logger_log_environment)
    setattr(Logger, "check_connectivity", logger_check_connectivity)
    setattr(Logger, "get_network_metrics", logger_get_network_metrics)

