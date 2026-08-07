"""Small reusable console/SMTP transport for OLDAP multipart email."""

from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage


def deliver_multipart_email(
    *,
    recipient: str,
    subject: str,
    plain_body: str,
    html_body: str,
    backend: str,
    logger: logging.Logger,
) -> None:
    """Deliver one UTF-8 multipart message without domain-specific side effects.

    Args:
        recipient: Destination email address already resolved by the caller.
        subject: Human-readable subject.
        plain_body: Complete plain-text alternative.
        html_body: Complete HTML alternative.
        backend: ``console`` or ``smtp``.
        logger: Application logger used only by the console backend.

    Raises:
        RuntimeError: If configuration is incomplete or the backend is unknown.
        smtplib.SMTPException: If SMTP submission fails.
    """
    normalized_backend = backend.strip().lower()
    if normalized_backend == "console":
        logger.info("Email for %s (%s):\n%s", recipient, subject, plain_body)
        return
    if normalized_backend != "smtp":
        raise RuntimeError(f'Unknown email backend "{backend}".')

    sender = os.getenv("OLDAP_MAIL_FROM")
    host = os.getenv("OLDAP_MAIL_HOST")
    if not sender or not host:
        raise RuntimeError(
            "OLDAP_MAIL_FROM and OLDAP_MAIL_HOST must be configured for SMTP mail."
        )
    try:
        port = int(os.getenv("OLDAP_MAIL_PORT", "587"))
    except ValueError as error:
        raise RuntimeError("OLDAP_MAIL_PORT must be an integer.") from error
    username = os.getenv("OLDAP_MAIL_USERNAME")
    password = os.getenv("OLDAP_MAIL_PASSWORD")
    use_tls = os.getenv("OLDAP_MAIL_USE_TLS", "true").strip().lower() not in {
        "0",
        "false",
        "no",
    }

    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(plain_body)
    message.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(host, port) as smtp:
        if use_tls:
            smtp.starttls()
        if username:
            smtp.login(username, password or "")
        smtp.send_message(message)
