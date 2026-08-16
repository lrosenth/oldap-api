"""Content-safety tests for token-free export status notifications."""

from dataclasses import replace
from datetime import timedelta

from oldap_api.exports.domain import ExportNotificationStatus, ExportState
from oldap_api.exports.notifications import (
    _content,
    _job_link,
    deliver_export_notification,
)
from oldap_api.test.test_export_manifest import NOW, bound_job


class User:
    """Minimal notification recipient with deliberately unsafe display data."""

    givenName = "Alice <Admin>"
    familyName = "Example & Co."
    email = "alice@example.org"


def test_ready_notification_escapes_html_and_contains_no_capability(monkeypatch):
    job, _ = bound_job()
    ready = replace(
        job,
        state=ExportState.READY,
        ready_at=NOW,
        expires_at=NOW + timedelta(hours=24),
        archive_size_bytes=123,
        archive_sha256="b" * 64,
        notification_status=ExportNotificationStatus.PENDING,
        notification_for_state=ExportState.READY,
    )
    monkeypatch.setenv("OLDAP_PUBLIC_APP_URL", "https://fasnacht.example/")
    link = _job_link(ready.export_id)

    plain, html = _content(User(), ready, ExportState.READY, link)

    assert link == f"https://fasnacht.example/exports/{ready.export_id}"
    assert "token" not in link.lower()
    assert "download" not in link.lower()
    assert "Alice <Admin>" in plain
    assert "Alice &lt;Admin&gt;" in html
    assert "Example &amp; Co." in html
    assert "15.08.2026 14:00" in plain


def test_failed_notification_is_project_neutral():
    job, _ = bound_job()
    failed = replace(
        job,
        state=ExportState.FAILED,
        failure_code="SOURCE_CHANGED",
        notification_status=ExportNotificationStatus.PENDING,
        notification_for_state=ExportState.FAILED,
    )

    plain, _ = _content(
        User(),
        failed,
        ExportState.FAILED,
        f"https://example.org/exports/{failed.export_id}",
    )

    assert failed.selection.display_name in plain
    assert "fasnacht:" not in plain


def test_ready_notification_uses_real_console_transport_without_token(
    monkeypatch, caplog
):
    job, _ = bound_job()
    ready = replace(
        job,
        state=ExportState.READY,
        ready_at=NOW,
        expires_at=NOW + timedelta(hours=24),
        archive_size_bytes=123,
        archive_sha256="b" * 64,
        notification_status=ExportNotificationStatus.PENDING,
        notification_for_state=ExportState.READY,
    )
    monkeypatch.setenv("OLDAP_PUBLIC_APP_URL", "https://fasnacht.example")
    monkeypatch.setenv("OLDAP_EXPORT_EMAIL_BACKEND", "console")
    monkeypatch.setattr(
        "oldap_api.exports.notifications.User.read",
        lambda **kwargs: User(),
    )

    from flask import Flask

    with Flask(__name__).app_context(), caplog.at_level("INFO"):
        deliver_export_notification(object(), ready)

    output = caplog.text
    assert f"https://fasnacht.example/exports/{ready.export_id}" in output
    assert "alice@example.org" in output
    assert "token=" not in output
