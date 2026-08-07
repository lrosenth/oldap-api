"""Focused tests for password-reset URL and multipart mail generation."""

from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

from oldap_api.views import auth_views
from oldap_api import mail

RESET_TOKEN = "header.payload.signature"


def _user():
    """Return the user attributes required by the mail helper."""
    return SimpleNamespace(
        givenName="Test",
        familyName="User",
        userId="testuser",
        email="recipient@example.org",
    )


def test_password_reset_link_encodes_jwt_segment_separators(monkeypatch):
    """Plain-text link detection must not stop at a literal JWT dot."""
    monkeypatch.setenv("OLDAP_PASSWORD_RESET_FRONTEND_URL", "https://fasnacht.digital")

    link = auth_views._password_reset_link(RESET_TOKEN)

    assert link == (
        "https://fasnacht.digital/password-reset?" "token=header%2Epayload%2Esignature"
    )
    assert parse_qs(urlparse(link).query)["token"] == [RESET_TOKEN]


def test_smtp_mail_contains_complete_token_in_plain_and_html_parts(monkeypatch):
    """Both MIME alternatives must retain the complete reset token."""
    sent_messages = []

    class FakeSmtp:
        def __init__(self, host, port):
            assert (host, port) == ("smtp.example.org", 25)

        def __enter__(self):
            return self

        def __exit__(self, *unused):
            return None

        def starttls(self):
            return None

        def send_message(self, message):
            sent_messages.append(message)

    monkeypatch.setenv("OLDAP_PASSWORD_RESET_EMAIL_BACKEND", "smtp")
    monkeypatch.setenv("OLDAP_MAIL_HOST", "smtp.example.org")
    monkeypatch.setenv("OLDAP_MAIL_PORT", "25")
    monkeypatch.setenv("OLDAP_MAIL_FROM", "oldap@example.org")
    monkeypatch.setenv("OLDAP_MAIL_USE_TLS", "true")
    monkeypatch.delenv("OLDAP_MAIL_USERNAME", raising=False)
    monkeypatch.delenv("OLDAP_MAIL_PASSWORD", raising=False)
    monkeypatch.setattr(mail.smtplib, "SMTP", FakeSmtp)

    link = "https://fasnacht.digital/password-reset?token=header%2Epayload%2Esignature"
    auth_views._send_password_reset_email(_user(), link, identified_by_email=True)

    assert len(sent_messages) == 1
    message = sent_messages[0]
    assert message["Subject"] == "Passwort zurücksetzen"
    assert message.get_content_type() == "multipart/alternative"

    plain_body = message.get_body(preferencelist=("plain",)).get_content()
    html_body = message.get_body(preferencelist=("html",)).get_content()
    assert link in plain_body
    assert link in html_body
    assert "Passwort neu setzen" in html_body
    assert "Ihre User-ID lautet: testuser" in plain_body
    assert parse_qs(urlparse(link).query)["token"] == [RESET_TOKEN]
