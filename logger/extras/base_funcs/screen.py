"""screen.py - Função ``screen`` para registrar screenshot."""

from logging import Logger
from pathlib import Path
from ..helpers import _attach_screenshot

__all__ = ["screen"]


def screen(self: Logger, msg: str, *args, webdriver=None, **kwargs) -> None:
    """Registra mensagem e captura de tela se possível."""
    screen_dir: Path | None = getattr(self, "_screen_dir", None)
    name: str = getattr(self, "_screen_name", "log")
    if screen_dir:
        _attach_screenshot(self, name, screen_dir, webdriver)
    self.log(35, msg, *args, stacklevel=2, **kwargs)
