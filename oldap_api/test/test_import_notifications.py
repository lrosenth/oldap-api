"""Content-safety tests for import status notifications."""

from types import SimpleNamespace

from oldap_api.imports.domain import ImportState
from oldap_api.imports.notifications import _content


def test_invalid_mail_contains_authenticated_link_but_no_file_details():
    user = SimpleNamespace(givenName="Alice", familyName="Example")
    link = "https://fasnacht.digital/imports/11111111-1111-4111-8111-111111111111"

    plain, html = _content(user, ImportState.INVALID, link)

    assert link in plain
    assert link in html
    assert "Zugriffstoken" in plain
    assert "password.zip" not in plain
    assert "password.zip" not in html
    assert "Bearer" not in plain
