"""Unit tests for the standalone SMTP delivery diagnostic."""

from argparse import Namespace

from oldap_api import smtp_test


def _args(**overrides):
    values = {
        "host": None,
        "port": None,
        "sender": None,
        "recipient": None,
        "username": None,
        "security": None,
        "timeout": 15.0,
        "non_interactive": True,
    }
    values.update(overrides)
    return Namespace(**values)


def test_collect_config_uses_api_environment_variables():
    config = smtp_test.collect_config(
        _args(),
        {
            "OLDAP_MAIL_HOST": "smtp.example.org",
            "OLDAP_MAIL_PORT": "587",
            "OLDAP_MAIL_FROM": "OLDAP <oldap@example.org>",
            "OLDAP_MAIL_USERNAME": "oldap@example.org",
            "OLDAP_MAIL_PASSWORD": "secret",
            "OLDAP_MAIL_USE_TLS": "true",
            "OLDAP_SMTP_TEST_RECIPIENT": "recipient@example.org",
        },
    )

    assert config.host == "smtp.example.org"
    assert config.port == 587
    assert config.security == "starttls"
    assert config.sender == "OLDAP <oldap@example.org>"
    assert config.recipient == "recipient@example.org"
    assert config.username == "oldap@example.org"
    assert config.password == "secret"


def test_send_test_message_uses_starttls_and_authentication(monkeypatch):
    events = []

    class FakeSmtp:
        def __init__(self, host, port, **kwargs):
            events.append(("connect", host, port, kwargs))

        def __enter__(self):
            return self

        def __exit__(self, *unused):
            events.append(("close",))

        def ehlo(self):
            events.append(("ehlo",))

        def starttls(self, **kwargs):
            events.append(("starttls", bool(kwargs.get("context"))))

        def login(self, username, password):
            events.append(("login", username, password))

        def send_message(self, message):
            events.append(("send", message["To"]))
            return {}

    monkeypatch.setattr(smtp_test.smtplib, "SMTP", FakeSmtp)
    smtp_test.send_test_message(
        smtp_test.SmtpTestConfig(
            host="smtp.example.org",
            port=587,
            security="starttls",
            sender="oldap@example.org",
            recipient="recipient@example.org",
            username="oldap@example.org",
            password="secret",
            timeout=10,
        )
    )

    assert events[0][:3] == ("connect", "smtp.example.org", 587)
    assert [event[0] for event in events] == [
        "connect",
        "ehlo",
        "starttls",
        "ehlo",
        "login",
        "send",
        "close",
    ]


def test_send_test_message_supports_implicit_tls_without_auth(monkeypatch):
    events = []

    class FakeSmtpSsl:
        def __init__(self, host, port, **kwargs):
            events.append(("connect", host, port, bool(kwargs.get("context"))))

        def __enter__(self):
            return self

        def __exit__(self, *unused):
            events.append(("close",))

        def ehlo(self):
            events.append(("ehlo",))

        def send_message(self, message):
            events.append(("send", message["To"]))
            return {}

    monkeypatch.setattr(smtp_test.smtplib, "SMTP_SSL", FakeSmtpSsl)
    smtp_test.send_test_message(
        smtp_test.SmtpTestConfig(
            host="smtp.example.org",
            port=465,
            security="ssl",
            sender="oldap@example.org",
            recipient="recipient@example.org",
            username=None,
            password=None,
            timeout=10,
        )
    )

    assert events == [
        ("connect", "smtp.example.org", 465, True),
        ("ehlo",),
        ("send", "recipient@example.org"),
        ("close",),
    ]
