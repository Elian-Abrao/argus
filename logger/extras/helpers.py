"""helpers.py - Funções utilitárias comuns do logger.

Este módulo reúne funções auxiliares usadas na configuração do logger
principal. Inclui inicialização do colorama para saída colorida, criação
de diretórios de log e captura opcional de screenshots.
"""

from pathlib import Path
from datetime import datetime
from logging import Logger
from colorama import init
from types import ModuleType
try:
    import pyautogui as _pyautogui  # pragma: no cover - dependência opcional
except Exception:  # pragma: no cover - ambiente sem a lib
    _pyautogui = None

pyautogui: ModuleType | None = _pyautogui


def _init_colorama() -> None:
    """Inicializa o colorama para colorir a saída do console."""
    init(autoreset=True)


def _setup_directories(base_dir: Path) -> tuple[Path, Path]:
    """Garante que os diretórios de log existam.

    Parameters
    ----------
    base_dir: Path
        Diretório base onde serão criados os logs.

    Returns
    -------
    tuple[Path, Path]
        Caminhos para os diretórios de capturas de tela e logs de depuração.
    """
    screen_dir = base_dir / "PrintScreens"
    debug_dir = base_dir / "LogsDEBUG"
    base_dir.mkdir(parents=True, exist_ok=True)
    screen_dir.mkdir(parents=True, exist_ok=True)
    debug_dir.mkdir(parents=True, exist_ok=True)
    return screen_dir, debug_dir


def _get_log_filename(name: str | None, *, use_timestamp: bool = True) -> str:
    """Gera um nome de arquivo de log.

    Se ``use_timestamp`` for ``False``, devolve apenas ``<name>.log`` para
    compatibilidade com handlers que fazem rotação automática.
    """
    base = name or "log"
    if not use_timestamp:
        return f"{base}.log"
    ts = datetime.now().strftime("%d-%m-%Y %H-%M-%S")
    return f"{base} - {ts}.log"


def _attach_screenshot(logger: Logger, name: str, screen_dir: Path, webdriver=None) -> None:
    """Captura uma screenshot utilizando ``pyautogui`` ou Selenium.

    Parameters
    ----------
    logger : Logger
        Instância do logger para registrar mensagens de erro caso a captura
        falhe.
    name : str
        Nome base do arquivo de imagem.
    screen_dir : Path
        Diretório onde a imagem será salva.
    webdriver : opcional
        Objeto webdriver do Selenium para captura via navegador.
    """
    path = screen_dir / f"{name}.png"
    try:
        if webdriver is not None:
            webdriver.save_screenshot(str(path))
        elif pyautogui is not None:
            pyautogui.screenshot(str(path))
        else:
            return
        logger.debug(f"Screenshot salva: {path}")
    except Exception as exc:  # pragma: no cover - funcionalidade opcional
        logger.warning(f"Falha ao capturar screenshot: {exc}")
