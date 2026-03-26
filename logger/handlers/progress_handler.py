import logging
from logging import StreamHandler

class ProgressStreamHandler(StreamHandler):
    """StreamHandler que mantém a barra de progresso visível durante logs."""
    def emit(self, record: logging.LogRecord) -> None:
        logger = logging.getLogger(record.name)
        pbar = getattr(logger, "_active_pbar", None)
        if pbar:
            pbar._clear_line()
        super().emit(record)
        if pbar and not pbar.closed:
            pbar._print_progress()

