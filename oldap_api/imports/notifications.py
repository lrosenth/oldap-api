"""User-facing import notification content and delivery."""

from __future__ import annotations

import os
from html import escape

from flask import current_app
from oldaplib.src.user import User

from oldap_api.mail import deliver_multipart_email
from oldap_api.frontend_links import mail_link, mail_display_name

from .domain import ImportJob, ImportState

SUBJECTS = {
    ImportState.READY: "ZIP-Import ist zur Übernahme bereit",
    ImportState.INVALID: "ZIP-Import konnte nicht angenommen werden",
    ImportState.FAILED: "ZIP-Import konnte nicht verarbeitet werden",
    ImportState.IMPORTED: "ZIP-Import wurde übernommen",
}


def deliver_import_notification(connection, job: ImportJob) -> None:
    """Resolve the owner and submit a bounded, token-free status message."""
    if job.notification_for_state not in SUBJECTS:
        raise RuntimeError("No notification template exists for this import state.")
    user = User.read(
        con=connection,
        userId=job.requested_by_user_id,
        ignore_cache=True,
    )
    link = _job_link(job.import_id, job.frontend_id)
    plain, html = _content(
        user, job.notification_for_state, link, mail_display_name(job.frontend_id)
    )
    backend = os.getenv("OLDAP_IMPORT_EMAIL_BACKEND") or os.getenv(
        "OLDAP_PASSWORD_RESET_EMAIL_BACKEND", "console"
    )
    deliver_multipart_email(
        recipient=str(user.email),
        subject=SUBJECTS[job.notification_for_state],
        plain_body=plain,
        html_body=html,
        backend=backend,
        logger=current_app.logger,
    )


def _job_link(import_id: str, frontend_id: str | None = None) -> str:
    """Resolve the durable job destination through trusted server configuration."""
    return mail_link(frontend_id, "import_status", import_id=import_id)


def _content(
    user, state: ImportState, link: str, display_name: str = "OLDAP"
) -> tuple[str, str]:
    application_name = display_name
    display_name = f"{user.givenName} {user.familyName}"
    messages = {
        ImportState.READY: (
            "Die Prüfung Ihres ZIP-Imports ist abgeschlossen. Sie können den Prüfbericht ansehen und die Übernahme bestätigen oder den Import abbrechen."
        ),
        ImportState.INVALID: (
            "Der ZIP-Import enthält mindestens ein blockierendes Problem und wurde verworfen. Der befristete Prüfbericht enthält weitere Informationen."
        ),
        ImportState.FAILED: (
            "Der ZIP-Import konnte wegen eines technischen Problems nicht abgeschlossen werden. Der befristete Statusbericht enthält weitere Informationen."
        ),
        ImportState.IMPORTED: "Der ZIP-Import wurde vollständig in den Staging-Bereich übernommen.",
    }
    message = messages[state]
    plain = (
        f"Guten Tag {display_name}\n\n{message}\n\n"
        f"Import anzeigen: {link}\n\n"
        f"Dieser Link enthält kein Zugriffstoken. Eine Anmeldung bei {application_name} ist erforderlich.\n"
    )
    safe_name = escape(display_name)
    safe_message = escape(message)
    safe_link = escape(link, quote=True)
    html = f"""<!doctype html>
<html lang="de"><body style="font-family: Arial, sans-serif; color: #172033; line-height: 1.5;">
<p>Guten Tag {safe_name}</p><p>{safe_message}</p>
<p><a href="{safe_link}" style="background:#1f5eff;color:#fff;padding:12px 18px;text-decoration:none;border-radius:6px;display:inline-block;">Import anzeigen</a></p>
<p style="font-size:13px;color:#526079;">Der Link enthält kein Zugriffstoken. Eine Anmeldung bei {escape(application_name)} ist erforderlich.</p>
</body></html>"""
    return plain, html
