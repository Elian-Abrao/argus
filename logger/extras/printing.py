"""printing.py - Captura de chamadas print para integracao com o logger."""

import builtins
import sys
from contextlib import contextmanager
from logging import Logger

class PrintCapture:
    """Substitui a funcao print para redirecionar saidas ao logger."""
    def __init__(self):
        self.original_print = None
        self.logger = None
        self.log_level = 'INFO'
        self.prefix = ''
        self.active = False

    def start_capture(self, logger, level='WARNING', prefix='❌ Evite o Uso de Print(): '):
        if self.active:
            return
        self.logger = logger
        self.log_level = level
        self.prefix = prefix
        self.active = True
        if self.original_print is None:
            self.original_print = builtins.print
        def new_print(*args, **kwargs):
            file = kwargs.get('file', sys.stdout)
            sep = kwargs.get('sep', ' ')
            end = kwargs.get('end', '\n')
            flush = kwargs.get('flush', False)
            if file is not sys.stdout:
                return self.original_print(*args, file=file, sep=sep, end=end, flush=flush)
            message = sep.join(str(arg) for arg in args)
            log_method = getattr(self.logger, self.log_level.lower())
            # log_method(f"-------------- ❌ Evite o Uso de Print ❌ --------------")
            log_method(f"{self.prefix}{message}")
            # log_method(f"-------------------------------------------------------")
            if end != '\n':
                self.original_print(*args, sep=sep, end=end, flush=flush)
        builtins.print = new_print

    def stop_capture(self):
        if self.original_print and self.active:
            builtins.print = self.original_print
            self.active = False

print_capture = PrintCapture()

def logger_capture_prints(self: Logger, active: bool = True, level: str = 'INFO', prefix: str = '❌ Evite o Uso de Print(): '):
    if active:
        print_capture.start_capture(self, level=level, prefix=prefix)
    else:
        print_capture.stop_capture()


@contextmanager
def capture_prints(self: Logger, level: str = 'INFO', prefix: str = '❌ Evite o Uso de Print(): '):
    """Capture calls to ``print`` within a context and restore on exit."""
    print_capture.start_capture(self, level=level, prefix=prefix)
    try:
        yield
    finally:
        print_capture.stop_capture()
