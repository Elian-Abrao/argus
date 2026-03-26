# Quickstart
[Voltar ao indice](README.md)

Comece com o basico: criar um logger, registrar mensagens e usar a barra de progresso.

## 1) Instale
```bash
pip install -e .[dev]
```

## 2) Crie um logger
```python
from logger import start_logger

logger = start_logger("Demo")
logger.info("Processo iniciado")
```

## 3) Progresso e timer
```python
from logger import start_logger
import time

logger = start_logger("Batch")
with logger.timer("etapa-1"):  # type: ignore[attr-defined]
    for i in logger.progress(range(5), desc="Trabalhando"):  # type: ignore[attr-defined]
        time.sleep(0.2)
        logger.success(f"item={i}")  # type: ignore[attr-defined]
```

## 4) Captura de prints
```python
from logger import start_logger

logger = start_logger("Capture", capture_prints=True)
print("Vai para o log")
```

## 5) Captura automatica de emails (smtplib)
```python
from logger import start_logger
import smtplib

logger = start_logger("Mailer", capture_emails=True)

with smtplib.SMTP("smtp.office365.com", 587) as server:
    # qualquer sendmail/send_message passa a gerar evento EMAIL_CAPTURE
    pass
```

## 6) Modo servidor
```python
logger = start_logger("API", server_mode=True)
```

Proximos passos:
- [Examples](examples.md)
- [Advanced Config](advanced_config.md)
- [Remote API](remote_api.md)
