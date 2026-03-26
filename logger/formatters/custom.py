"""custom.py - Formatadores e classe de logger personalizada.

Este modulo define o ``CustomFormatter`` usado para colorir mensagens,
alem do ``AutomaticTracebackLogger`` e funcao ``_define_custom_levels``.
Uso:
    from logger.formatters.custom import CustomFormatter, AutomaticTracebackLogger, _define_custom_levels
"""

import logging
from logging import Formatter, Logger
from pathlib import Path
from colorama import Fore, Style
import threading
import inspect
import sys
from contextvars import ContextVar


from logger.extras.helpers import _init_colorama

__all__ = [
    "_init_colorama",
    "CustomFormatter",
    "AutomaticTracebackLogger",
    "_define_custom_levels",
]

# Funcoes internas ignoradas na geracao da call chain
_INTERNAL_FUNCS = {
    'format', '_extract_call_chain', '_init_colorama',
    '_define_custom_levels', '_setup_directories', '_get_log_filename',
    '_attach_screenshot', 'screen',
    'logger_progress', '__call__', '_log_progress', 'log_with_context',
    '_log_start', '_log_end', 'emit'
}

# Contexto para filtragem de funcoes internas
_log_context: ContextVar[list[str]] = ContextVar('log_context', default=[])

class CustomFormatter(Formatter):
    """Formatter com emojis e cores para saida humanizada."""
    LEVEL_EMOJI = {
        'DEBUG': '🐛',
        'INFO': '🔍',
        'SUCCESS': '✅',
        'WARNING': '🚨',
        'ERROR': '❌',
        'CRITICAL': '🔥',
        'SCREEN': '📸',
    }
    LEVEL_COLOR = {
        'DEBUG': Fore.BLUE,
        'INFO': Fore.GREEN,
        'SUCCESS': Fore.CYAN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.MAGENTA,
        'SCREEN': Fore.MAGENTA,
    }

    def __init__(self, fmt=None, datefmt=None, style="%", use_color=True):
        super().__init__(fmt=fmt, datefmt=datefmt, style=style)
        self.use_color = use_color

    def format(self, record):
        if getattr(record, 'plain', False):
            output = record.getMessage()
            if record.exc_info:
                output = f"{output}\n{self.formatException(record.exc_info)}"
            return output
        original_levelname = record.levelname
        original_levelname_color = getattr(record, 'levelname_color', None)
        original_msg = record.msg
        original_args = record.args
        try:
            context = getattr(record, 'context', '')
            if context:
                ctx_disp = (
                    f"{Fore.LIGHTYELLOW_EX}{context}{Style.RESET_ALL}"
                    if self.use_color else context
                )
                record.msg = f"[{ctx_disp}] {record.getMessage()}"
                record.args = ()
            record.emoji = self.LEVEL_EMOJI.get(original_levelname, '🔹')
            color = self.LEVEL_COLOR.get(original_levelname, '') if self.use_color else ''
            suffix = Style.RESET_ALL if self.use_color and color else ''
            record.levelname_color = f"{color}[{original_levelname}]{suffix}"
            record.levelname = f"[{original_levelname}]"
            pad = 11
            record.levelpad = ' ' * (pad - len(record.levelname))
            record.thread = threading.current_thread().name
            record.thread_disp = '' if record.thread == 'MainThread' else f"[T:{record.thread}]"
            record.call_chain = _extract_call_chain(record)
            if "logger" not in record.pathname.lower():
                filename = Path(record.pathname).name
                record.meta = f"→ 📁 {filename}:{record.lineno} | 🧭 {record.call_chain}"
            else:
                record.meta = ""
            mensagem_formatada = super().format(record)
            if record.meta:
                mensagem_formatada += f" {record.meta}"
            return mensagem_formatada
        finally:
            record.msg = original_msg
            record.args = original_args
            record.levelname = original_levelname
            if original_levelname_color is not None:
                record.levelname_color = original_levelname_color

class AutomaticTracebackLogger(logging.Logger):
    """Logger que captura automaticamente exceptions para incluir stack trace."""
    def error(self, msg, *args, **kwargs):
        exc_info = sys.exc_info()
        if exc_info[0] is not None:
            kwargs['exc_info'] = exc_info
        super().error(msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        kwargs['exc_info'] = True
        self.error(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        exc_info = sys.exc_info()
        if exc_info[0] is not None:
            kwargs['exc_info'] = exc_info
        super().critical(msg, *args, **kwargs)


def _extract_call_chain(record) -> str:
    """Extrai a cadeia de chamadas ignorando funcoes internas."""
    chain = []
    for frame_info in inspect.stack():
        func = frame_info.function.strip("<>")
        module = frame_info.frame.f_globals.get('__name__', '')
        filename = frame_info.filename
        if func in _INTERNAL_FUNCS:
            continue
        if module.startswith(('logging', 'inspect', 'colorama', 'threading')):
            continue
        if module == __name__ or module.startswith('logger.'):
            continue
        if not filename.endswith('.py'):
            continue
        chain.append(func)
    unique: list[str] = []
    for f in reversed(chain):
        if not unique or unique[-1] != f:
            unique.append(f)
    return '>'.join(unique) or record.funcName


def _define_custom_levels():
    """Registra niveis SUCCESS e SCREEN no modulo logging."""
    levels = {25: 'SUCCESS', 35: 'SCREEN'}
    for lvl, name in levels.items():
        if name not in logging._nameToLevel:
            logging.addLevelName(lvl, name)
            def log_for(self, msg, *args, _lvl=lvl, **kwargs):
                if self.isEnabledFor(_lvl):
                    self._log(_lvl, msg, args, **kwargs)
            setattr(Logger, name.lower(), log_for)

