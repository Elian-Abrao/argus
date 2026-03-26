"""progress.py - Barra de progresso e funcoes utilitarias.
"""

from typing import Iterable, List
from logging import Logger
import sys
import time
from wcwidth import wcswidth

# ---- Funcoes auxiliares ----

def format_block(title: str, lines):
    space = " " * 2
    title_str = f"[{title}]"
    title_w = wcswidth(title_str)
    content_ws = [wcswidth(line) for line in lines] if lines else [0]
    max_content_w = max(content_ws)
    inner_width = max(title_w, max_content_w)
    total_w = inner_width + 4
    pad_total = total_w - title_w - 2
    left = pad_total // 2
    right = pad_total - left
    topo = f"{space}╭{'─'*left}{title_str}{'─'*right}╮"
    corpo = []
    for line, w in zip(lines, content_ws):
        falta = inner_width - w
        corpo.append(f"{space}│ {line}{' '*falta} │")
    base = f"{space}╰{'─'*(total_w-2)}╯"
    return "\n".join([topo] + corpo + [base])

def combine_blocks(blocks: List[str]) -> str:
    """Combine multiple formatted blocks horizontally."""
    split_blocks = [b.split("\n") for b in blocks]
    widths = [max(wcswidth(line) for line in bl) for bl in split_blocks]
    height = max(len(bl) for bl in split_blocks)
    padded = []
    for bl, w in zip(split_blocks, widths):
        pad_lines = [line + " " * (w - wcswidth(line)) for line in bl]
        pad_lines += [" " * w] * (height - len(pad_lines))
        padded.append(pad_lines)
    combined_lines = ["  ".join(parts) for parts in zip(*padded)]
    return "\n".join(combined_lines)

class LoggerProgressBar:
    def __init__(
        self,
        logger: Logger,
        total: int | None = None,
        desc: str = '',
        leave: bool = True,
        unit: str = 'it',
        log_interval: float = 1.0,
        log_level: str = 'INFO',
    ) -> None:
        self.logger = logger
        self.total = total
        self.desc = desc
        self.leave = leave
        self.unit = unit
        self.log_interval = log_interval
        self.log_level = log_level
        self.n = 0
        self.start_time = time.time()
        self.last_log_time = self.start_time
        self.last_print_time = self.start_time
        self.closed = False
        self.last_line_len = 0
        # contexto automatico
        self._ctx_cm = None
        if hasattr(self.logger, "context"):
            ctx_name = self.desc or "Loop"
            self._ctx_cm = self.logger.context(ctx_name)
            self._ctx_cm.__enter__()
        self._log_progress(initial=True)

    def update(self, n: int = 1):
        if self.closed:
            return
        self.n += n
        now = time.time()
        if now - self.last_log_time >= self.log_interval and self.n != self.total:
            self._log_progress()
            self.last_log_time = now
            self._print_progress()
            return
        if self.n == self.total or now - self.last_print_time >= 0.2:
            self._print_progress()
            self.last_print_time = now

    def close(self):
        if not self.closed:
            self.closed = True
            self._log_progress(final=True)
            self._print_progress(final=True)
            if getattr(self.logger, "_active_pbar", None) is self:
                setattr(self.logger, "_active_pbar", None)
            if self._ctx_cm is not None:
                self._ctx_cm.__exit__(None, None, None)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __call__(self, iterable: Iterable) -> Iterable:
        if self.total is None:
            try:
                self.total = len(iterable)  # type: ignore[arg-type]
            except (TypeError, AttributeError):
                try:
                    iterable = list(iterable)
                    self.total = len(iterable)
                except Exception:
                    pass

        for obj in iterable:
            yield obj
            self.update(1)
        self.close()

    # internal helpers
    def _format_bar(self, pct: float, width: int = 20) -> str:
        filled = int(width * pct)
        return '█' * filled + '░' * (width - filled)

    def _get_progress_info(self):
        now = time.time()
        elapsed = now - self.start_time
        if self.total is None or self.total == 0:
            pct = 0
            rate = 0
            remaining = 0
        else:
            pct = self.n / self.total
            rate = self.n / elapsed if elapsed > 0 else 0
            remaining = (self.total - self.n) / rate if rate > 0 else 0
        return {
            'count': self.n,
            'total': self.total,
            'pct': pct * 100,
            'bar': self._format_bar(pct),
            'elapsed': elapsed,
            'remaining': remaining,
            'rate': rate,
            'rate_str': f"{rate:.1f} {self.unit}/s",
        }

    def _log_progress(self, initial: bool = False, final: bool = False):
        info = self._get_progress_info()
        if initial:
            message = f"⏱️ Iniciando: {self.desc} (0/{info['total']} {self.unit})"
        elif final:
            message = f"✅ Concluído: {self.desc} ({info['count']}/{info['total']} {self.unit})"
        else:
            message = (f"📊 {self.desc}: [{info['bar']}] {info['count']}/{info['total']} {self.unit} ({info['pct']:.1f}%)")
        log_method = getattr(self.logger, self.log_level.lower())
        log_method(message)

    def _clear_line(self):
        if not sys.stdout.isatty():
            return
        sys.stdout.write('\r' + ' ' * self.last_line_len + '\r')

    def _print_progress(self, final: bool = False):
        if not sys.stdout.isatty():
            return
        info = self._get_progress_info()
        self._clear_line()
        line = (f"{self.desc}: [{info['bar']}] {info['count']}/{info['total']} ({info['pct']:.1f}%) {info['rate_str']}")
        max_len = 80
        if len(line) > max_len:
            line = line[:max_len-3] + '...'
        self.last_line_len = len(line)
        sys.stdout.write(line)
        sys.stdout.flush()
        if final and self.leave:
            sys.stdout.write('\n')
            sys.stdout.flush()


def logger_progress(
    self: Logger,
    iterable: Iterable | None = None,
    total: int | None = None,
    desc: str = '',
    leave: bool = True,
    unit: str = 'it',
    log_interval: float = 1.0,
    log_level: str = 'INFO',
) -> LoggerProgressBar | Iterable:
    pbar = LoggerProgressBar(
        logger=self,
        total=total,
        desc=desc,
        leave=leave,
        unit=unit,
        log_interval=log_interval,
        log_level=log_level,
    )
    setattr(self, "_active_pbar", pbar)
    if iterable is not None:
        return pbar(iterable)
    return pbar
