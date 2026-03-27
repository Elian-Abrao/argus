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
from email.message import EmailMessage
import os
import smtplib

logger = start_logger("Mailer", capture_emails=True)
smtp_user = "rpa2@teste.com.br"
smtp_password = os.getenv("SMTP_PASSWORD")
smtp_server = "smtp.office365.com"
porta = 587

msg = EmailMessage()
msg["From"] = smtp_user
msg["To"] = "destinatario@teste.com.br"
msg["Subject"] = "Teste SMTP Office 365"
msg.set_content("Mensagem de teste")

with smtplib.SMTP(smtp_server, porta) as server:
    server.starttls()
    if smtp_password:
        server.login(smtp_user, smtp_password)
    # qualquer sendmail/send_message passa a gerar evento EMAIL_CAPTURE
    server.send_message(msg)
```

## 6) Modo servidor
```python
logger = start_logger("API", server_mode=True)
```

Proximos passos:
- [Examples](examples.md)
- [Advanced Config](advanced_config.md)
- [Remote API](remote_api.md)
