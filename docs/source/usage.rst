Uso Básico
==========

Para iniciar um logger configurado execute::

    from logger import start_logger
    
    logger = start_logger("Demo")
    logger.info("Processo iniciado")

Captura de e-mails enviados via ``smtplib`` (ativo por padrão)::

    logger = start_logger(
        "Mailer",
        capture_emails=True,
        email_retention_days=7,
    )

Com ``remote_sink`` habilitado, os eventos de e-mail e anexos são enviados para a
Remote API e podem ser consultados no dashboard.

Para exemplos completos consulte :mod:`main`.
