# Developer Guide
[Voltar ao indice](README.md)

## Estrutura
```
logger/
  core/        # configuracao e bootstrap
  extras/      # utilitarios (timer, progress, lifecycle)
  handlers/    # handlers customizados
  formatters/  # formatadores
remote_api/
remote_dashboard/
```

## Padroes
- Formatacao: `ruff` (lint) e `black` (quando aplicavel)
- Tipagem: `mypy`
- Testes: `pytest`

## Fluxo sugerido
1. Crie uma branch a partir de `main`.
2. Implemente e adicione testes.
3. Execute:
   ```bash
   ruff check .
   mypy .
   pytest
   ```
4. Abra o PR com contexto e prints (se for UI).

## Versao
SemVer, controlado em `pyproject.toml`.
