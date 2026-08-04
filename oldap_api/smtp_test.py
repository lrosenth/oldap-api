"""Interactive SMTP connectivity and delivery diagnostic for OLDAP deployments.

The command uses the same ``OLDAP_MAIL_*`` environment variables as the
password-reset mailer. It can therefore run inside the API container and use
the deployed values as interactive defaults without printing credentials.

Run it with::

    python -m oldap_api.smtp_test

The diagnostic sends one plain-text message. It does not read or modify OLDAP
data and never accepts the SMTP password as a command-line argument.
"""

from __future__ import annotations

import argparse
import getpass
import os
import smtplib
import socket
import ssl
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from email.message import EmailMessage
from typing import Mapping, Sequence

SECURITY_MODES = ("starttls", "ssl", "plain")


@dataclass(frozen=True)
class SmtpTestConfig:
    """Connection and message settings for one SMTP delivery test.

    Attributes:
        host: SMTP server hostname or IP address.
        port: SMTP server TCP port.
        security: ``starttls``, ``ssl`` (implicit TLS), or ``plain``.
        sender: Envelope and message sender address.
        recipient: Recipient of the diagnostic message.
        username: Optional SMTP authentication username.
        password: Optional SMTP authentication password.
        timeout: Socket timeout in seconds.
    """

    host: str
    port: int
    security: str
    sender: str
    recipient: str
    username: str | None
    password: str | None
    timeout: float


def _env_bool(value: str | None, *, default: bool) -> bool:
    """Parse the boolean spelling used by the API mail configuration."""
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no"}


def _prompt(label: str, default: str | None = None, *, required: bool = True) -> str:
    """Prompt for a value, optionally displaying and accepting a default."""
    suffix = f" [{default}]" if default else ""
    while True:
        value = input(f"{label}{suffix}: ").strip()
        if value:
            return value
        if default:
            return default
        if not required:
            return ""
        print(f"{label} is required.", file=sys.stderr)


def _prompt_port(default: int) -> int:
    """Prompt until a valid TCP port number is supplied."""
    while True:
        value = _prompt("SMTP port", str(default))
        try:
            port = int(value)
        except ValueError:
            print("SMTP port must be an integer.", file=sys.stderr)
            continue
        if 1 <= port <= 65535:
            return port
        print("SMTP port must be between 1 and 65535.", file=sys.stderr)


def _prompt_security(default: str) -> str:
    """Prompt until a supported SMTP transport security mode is supplied."""
    while True:
        value = _prompt("Security (starttls/ssl/plain)", default).lower()
        if value in SECURITY_MODES:
            return value
        print(f"Security must be one of: {', '.join(SECURITY_MODES)}.", file=sys.stderr)


def _required(value: str | None, name: str) -> str:
    """Return a stripped required value or raise a configuration error."""
    normalized = (value or "").strip()
    if not normalized:
        raise ValueError(f"{name} is required in non-interactive mode.")
    return normalized


def collect_config(
    args: argparse.Namespace,
    environ: Mapping[str, str] | None = None,
) -> SmtpTestConfig:
    """Build the diagnostic configuration from arguments, environment, and prompts.

    Args:
        args: Parsed command-line arguments.
        environ: Environment mapping, injectable for tests.

    Returns:
        Complete SMTP connection and test-message configuration.

    Raises:
        ValueError: If required non-interactive settings are missing or invalid.
    """
    env = os.environ if environ is None else environ
    env_host = env.get("OLDAP_MAIL_HOST")
    env_sender = env.get("OLDAP_MAIL_FROM")
    env_username = env.get("OLDAP_MAIL_USERNAME")
    env_password = env.get("OLDAP_MAIL_PASSWORD")
    env_recipient = env.get("OLDAP_SMTP_TEST_RECIPIENT")

    try:
        env_port = int(env.get("OLDAP_MAIL_PORT", "587"))
    except ValueError as error:
        raise ValueError("OLDAP_MAIL_PORT must be an integer.") from error

    env_security = (
        "starttls"
        if _env_bool(env.get("OLDAP_MAIL_USE_TLS"), default=True)
        else "plain"
    )

    if args.non_interactive:
        host = _required(args.host or env_host, "SMTP host")
        sender = _required(args.sender or env_sender, "Sender")
        recipient = _required(args.recipient or env_recipient, "Recipient")
        port = args.port if args.port is not None else env_port
        security = (args.security or env_security).lower()
        username = (args.username or env_username or "").strip() or None
        password = env_password if username else None
    else:
        print("OLDAP SMTP delivery diagnostic")
        print("Press Enter to accept a displayed default.\n")
        host = _prompt("SMTP host", args.host or env_host)
        port = args.port if args.port is not None else _prompt_port(env_port)
        security = (
            args.security.lower() if args.security else _prompt_security(env_security)
        )
        sender = _prompt("From address", args.sender or env_sender)
        recipient = _prompt("Test recipient", args.recipient or env_recipient)
        username_value = _prompt(
            "SMTP username",
            args.username or env_username,
            required=False,
        )
        username = username_value or None
        password = None
        if username:
            password_prompt = "SMTP password"
            if env_password:
                password_prompt += " (Enter uses OLDAP_MAIL_PASSWORD)"
            entered_password = getpass.getpass(f"{password_prompt}: ")
            password = entered_password or env_password

    if not 1 <= port <= 65535:
        raise ValueError("SMTP port must be between 1 and 65535.")
    if security not in SECURITY_MODES:
        raise ValueError(f"Security must be one of: {', '.join(SECURITY_MODES)}.")
    if username and password is None:
        raise ValueError("SMTP password is required when a username is configured.")
    if args.timeout <= 0:
        raise ValueError("Timeout must be greater than zero.")

    return SmtpTestConfig(
        host=host,
        port=port,
        security=security,
        sender=sender,
        recipient=recipient,
        username=username,
        password=password,
        timeout=args.timeout,
    )


def send_test_message(config: SmtpTestConfig) -> None:
    """Connect, optionally authenticate, and send one SMTP diagnostic message.

    Args:
        config: Validated connection and message configuration.

    Raises:
        OSError: If name resolution or the TCP connection fails.
        ssl.SSLError: If TLS negotiation or certificate validation fails.
        smtplib.SMTPException: If the SMTP server rejects a protocol operation.
    """
    message = EmailMessage()
    message["From"] = config.sender
    message["To"] = config.recipient
    message["Subject"] = "OLDAP SMTP delivery test"
    message.set_content(
        "This is an SMTP delivery test from an OLDAP API deployment.\n\n"
        f"Host: {socket.gethostname()}\n"
        f"UTC time: {datetime.now(UTC).isoformat()}\n"
        f"Transport security: {config.security}\n"
    )

    tls_context = ssl.create_default_context()
    smtp_class = smtplib.SMTP_SSL if config.security == "ssl" else smtplib.SMTP

    print(f"Connecting to {config.host}:{config.port} ({config.security}) ...")
    connection_kwargs: dict[str, object] = {"timeout": config.timeout}
    if config.security == "ssl":
        connection_kwargs["context"] = tls_context

    with smtp_class(config.host, config.port, **connection_kwargs) as smtp:
        smtp.ehlo()
        print("SMTP greeting accepted.")

        if config.security == "starttls":
            smtp.starttls(context=tls_context)
            smtp.ehlo()
            print("STARTTLS negotiation and certificate validation succeeded.")

        if config.username:
            smtp.login(config.username, config.password or "")
            print("SMTP authentication succeeded.")
        else:
            print("SMTP authentication skipped (no username configured).")

        refused = smtp.send_message(message)
        if refused:
            raise smtplib.SMTPRecipientsRefused(refused)
        print("SMTP server accepted the test message for delivery.")


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line parser for the diagnostic utility."""
    parser = argparse.ArgumentParser(
        description=(
            "Test SMTP connectivity, TLS, authentication, and message submission "
            "using OLDAP mail environment variables as defaults."
        )
    )
    parser.add_argument("--host", help="SMTP hostname (default: OLDAP_MAIL_HOST)")
    parser.add_argument(
        "--port", type=int, help="SMTP port (default: OLDAP_MAIL_PORT or 587)"
    )
    parser.add_argument("--sender", help="From address (default: OLDAP_MAIL_FROM)")
    parser.add_argument(
        "--recipient",
        help="Test recipient (default: OLDAP_SMTP_TEST_RECIPIENT)",
    )
    parser.add_argument(
        "--username",
        help="SMTP username (default: OLDAP_MAIL_USERNAME)",
    )
    parser.add_argument("--security", choices=SECURITY_MODES)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Do not prompt; require missing values through arguments or environment.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the SMTP diagnostic and return a process exit status."""
    args = build_parser().parse_args(argv)
    try:
        config = collect_config(args)
        send_test_message(config)
    except (ValueError, OSError, ssl.SSLError, smtplib.SMTPException) as error:
        print(f"SMTP test failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 1

    print("Test completed successfully. Check the recipient inbox and spam folder.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
