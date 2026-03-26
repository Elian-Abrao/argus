"""pause.py - Pausa interativa para o logger."""

from logging import Logger
from threading import Thread
from typing import Optional

__all__ = ["pause"]


def _get_input(result: list[str | None], msg: str) -> None:
    try:
        result.append(input(msg))
    except EOFError:
        result.append(None)


def pause(
    self: Logger,
    msg: str = "Digite algo para continuar... ",
    timeout: Optional[float] = None,
) -> Optional[str]:
    """Exibe mensagem e aguarda entrada do usuário.

    Se ``timeout`` for informado e nenhuma entrada ocorrer nesse período,
    retorna ``None``.
    """
    resp: str | None
    if timeout is None:
        resp = input(msg)
        self.debug(f"Resposta do usuário: {resp}")
        return resp

    result: list[str | None] = []
    thread = Thread(target=_get_input, args=(result, msg))
    thread.daemon = True
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        self.debug("Entrada não recebida dentro do tempo limite")
        return None
    resp = result[0]
    if resp is None:
        self.debug("Entrada não recebida")
        return None
    self.debug(f"Resposta do usuário: {resp}")
    return resp
