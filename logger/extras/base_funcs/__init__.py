"""Coleção de funções auxiliares adicionadas ao ``Logger``.

Ao importar este pacote, todas as funções presentes nos módulos
internos são carregadas automaticamente para facilitar a extensão.
"""

from importlib import import_module
import pkgutil

__all__ = []

for info in pkgutil.iter_modules(__path__):
    module = import_module(f"{__name__}.{info.name}")
    if hasattr(module, "__all__"):
        for name in module.__all__:
            globals()[name] = getattr(module, name)
            __all__.append(name)
