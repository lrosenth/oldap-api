"""Token-free user notification content for completed ZIP exports."""

from __future__ import annotations

import os
from html import escape
from urllib.parse import quote
from zoneinfo import ZoneInfo

from flask import current_app
from oldaplib.src.user import User

from oldap_api.mail import deliver_multipart_email

from .domain import ExportJob, ExportState

SUBJECTS = {
    ExportState.READY: "ZIP-Export ist zum Download bereit",
    ExportState.FAILED: "ZIP-Export konnte nicht erstellt werden",
}


def deliver_export_notification(connection, job: ExportJob) -> None:
    """Resolve the owner and submit one bounded, token-free status message."""

    state = job.notification_for_state
    if state not in SUBJECTS:
        raise RuntimeError("No notification template exists for this export state.")
    user = User.read(
        con=connection,
        userId=job.requested_by_user_id,
        ignore_cache=True,
    )
    link = _job_link(job.export_id)
    plain, html = _content(user, job, state, link)
    backend = os.getenv("OLDAP_EXPORT_EMAIL_BACKEND") or os.getenv(
        "OLDAP_PASSWORD_RESET_EMAIL_BACKEND", "console"
    )
    deliver_multipart_email(
        recipient=str(user.email),
        subject=SUBJECTS[state],
        plain_body=plain,
        html_body=html,
        backend=backend,
        logger=current_app.logger,
    )


def _job_link(export_id: str) -> str:
    base_url = os.getenv("OLDAP_PUBLIC_APP_URL")
    if not base_url:
        raise RuntimeError("OLDAP_PUBLIC_APP_URL must be configured for export email.")
    return f"{base_url.rstrip('/')}/exports/{quote(export_id, safe='')}"


def _content(user, job: ExportJob, state: ExportState, link: str) -> tuple[str, str]:
    """Return escaped German plain-text and HTML alternatives."""

    display_name = f"{user.givenName} {user.familyName}"
    selection = job.selection.display_name
    if state is ExportState.READY:
        if job.expires_at is None:
            raise RuntimeError("READY export notification requires an expiry.")
        expires = job.expires_at.astimezone(ZoneInfo("Europe/Zurich"))
        message = (
            f"Der ZIP-Export für „{selection}“ ist fertig. Sie können ihn bis "
            f"{expires.strftime('%d.%m.%Y %H:%M')} herunterladen."
        )
    else:
        message = (
            f"Der ZIP-Export für „{selection}“ konnte nicht abgeschlossen werden. "
            "Die Statusseite enthält weitere Informationen."
        )
    plain = (
        f"Guten Tag {display_name}\n\n{message}\n\n"
        f"Export anzeigen: {link}\n\n"
        "Dieser Link enthält kein Download-Ticket. Eine Anmeldung ist erforderlich.\n"
    )
    safe_name = escape(display_name)
    safe_message = escape(message)
    safe_link = escape(link, quote=True)
    html = f"""<!doctype html>
<html lang="de"><body style="font-family: Arial, sans-serif; color: #172033; line-height: 1.5;">
<p>Guten Tag {safe_name}</p><p>{safe_message}</p>
<p><a href="{safe_link}" style="background:#1f5eff;color:#fff;padding:12px 18px;text-decoration:none;border-radius:6px;display:inline-block;">Export anzeigen</a></p>
<p style="font-size:13px;color:#526079;">Der Link enthält kein Download-Ticket. Eine Anmeldung ist erforderlich.</p>
</body></html>"""
    return plain, html
