# Examples
[Voltar ao indice](README.md)

## Basico
```python
from logger import start_logger

logger = start_logger("Demo")
logger.info("Inicio")
logger.success("Tudo ok")  # type: ignore[attr-defined]
```

## Progress + timer
```python
from logger import start_logger
import time

logger = start_logger("Batch")
with logger.timer("importacao"):  # type: ignore[attr-defined]
    for i in logger.progress(range(3), desc="Processando"):  # type: ignore[attr-defined]
        time.sleep(0.3)
        logger.debug(f"linha={i}")
```

## Captura de prints
```python
from logger import start_logger

logger = start_logger("Capture", capture_prints=True)
print("Mensagem capturada")
```

## Config JSON
```python
from logger import start_logger_from_config

logger = start_logger_from_config("logger_config.json")
logger.info("Rodando com config externa")
```

## Rotacao de arquivos
```python
from logger import start_logger

logger = start_logger(
    "Service",
    rotation_interval=1,
    rotation_unit="days",
)
```

## Remote sink (API)
```python
from logger import start_logger

logger = start_logger(
    "Bot",
    remote_sink={
        "enabled": True,
        "endpoint": "http://localhost:8100/api",
        "automation": {"code": "InvoiceBot", "name": "Invoice Bot"},
        "client": {"name": "Cliente XPTO", "external_code": "XPTO"},
        "host": {"environment": "prod"},
        "deployment_tag": "prod-01",
        "batch_size": 25,
        "flush_interval": 0.5,
    },
)
logger.info("Este log vai para a API")
```
