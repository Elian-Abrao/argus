# Testes
[Voltar ao indice](README.md)

## Suite principal
```bash
pytest
```

## Cobertura
```bash
pytest --cov=logger
```

## Qualidade
```bash
ruff check .
mypy .
bandit -r logger
```
