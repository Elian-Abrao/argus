"""cleanup.py - Função para limpar a tela do terminal."""

import os
import subprocess
from logging import Logger

__all__ = ["cleanup"]


def cleanup(self: Logger) -> None:
    """Limpa o terminal da plataforma atual."""
    if os.name == "nt":
        subprocess.run(["cmd", "/c", "cls"], check=False)
    else:
        subprocess.run(["clear"], check=False)
