"""dependency.py - Informacoes de dependencias e ambiente.

Contem a classe ``DependencyManager`` e funcoes de log relacionadas.
"""

from typing import Optional, Dict, Any
import platform
import pkg_resources  # type: ignore
import time
from logging import Logger
from .progress import format_block  # will use relative import; but we haven't created progress yet

class DependencyManager:
    """Coleta informacoes sobre dependencias e ambiente de execucao."""
    def __init__(self):
        self._cached_info: Optional[Dict[str, Any]] = None
        self._last_update: float = 0
        self._cache_duration: int = 300

    def get_environment_info(self, force_update: bool = False) -> Dict[str, Any]:
        now = time.time()
        if self._cached_info and not force_update and (now - self._last_update) < self._cache_duration:
            return self._cached_info
        info = {
            'python': {
                'version': platform.python_version(),
                'implementation': platform.python_implementation(),
                'compiler': platform.python_compiler(),
                'build': platform.python_build(),
            },
            'system': {
                'os': platform.system(),
                'release': platform.release(),
                'machine': platform.machine(),
                'processor': platform.processor(),
                'node': platform.node(),
            },
            'packages': {pkg.key: pkg.version for pkg in pkg_resources.working_set},
        }
        self._cached_info = info
        self._last_update = now
        return info

def logger_log_environment(self: Logger, level: str = 'INFO', return_block: bool = False) -> str | None:
    info = self._dep_manager.get_environment_info()  # type: ignore[attr-defined]
    log_method = getattr(self, level.lower())
    linhas = [
        f"Python {info['python']['version']} ({info['python']['implementation']})",
        f"SO: {info['system']['os']} {info['system']['release']} ({info['system']['machine']})",
        "Pacotes Principais:",
    ]
    important = ['requests', 'psutil', 'colorama', 'pyautogui']
    for pkg in important:
        if pkg in info['packages']:
            linhas.append(f"  - {pkg}: {info['packages'][pkg]}")
    bloco = format_block("AMBIENTE", linhas)
    if return_block:
        return bloco
    log_method(f"\n{bloco}")
    return None
