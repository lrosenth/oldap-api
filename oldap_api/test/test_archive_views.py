"""HTTP contract tests for read-only Staging archive YAML downloads."""

from flask import Flask

from oldap_api import authentication
from oldap_api.views import archive_views
from oldap_api.archive_workflow import apply_archive_upload
from oldap_api import archive_workflow
from oldaplib.src.archive_yaml import ArchiveDocument, ArchiveUnit
from oldaplib.src.helpers.oldaperror import OldapErrorNoPermission
from oldaplib.src.staging_archive import ArchiveProposal, ArchiveProposalWarning
from oldaplib.src.xsd.xsd_qname import Xsd_QName


class FakeConnection:
    """Authenticated request identity used without external services."""

    def __init__(self, **_kwargs) -> None:
        pass


def _client(monkeypatch, proposal_builder):
    monkeypatch.setattr(authentication, "Connection", FakeConnection)
    monkeypatch.setattr(archive_views, "build_visible_staging_archive_proposal", proposal_builder)
    app = Flask(__name__)
    app.register_blueprint(archive_views.archive_workflow_bp)
    app.config["TESTING"] = True
    return app.test_client()


def test_download_requires_authentication(monkeypatch):
    client = _client(monkeypatch, lambda *_args: None)

    response = client.get(
        "/archive/fasnacht/staging-proposal?stagingAreaIri=urn:uuid:00000000-0000-0000-0000-000000000001"
    )

    assert response.status_code == 401


def test_download_returns_canonical_yaml_and_safe_attachment(monkeypatch):
    calls = []

    def build(connection, project, staging_area_iri):
        calls.append((connection, project, staging_area_iri))
        return ArchiveProposal(
            ArchiveDocument(1, "de", (ArchiveUnit("root", "Fonds", "Archiv"),)),
            (ArchiveProposalWarning("EMPTY_FOLDER", "Review the empty folder."),),
        )

    client = _client(monkeypatch, build)
    response = client.get(
        "/archive/fasnacht/staging-proposal?stagingAreaIri=urn:uuid:00000000-0000-0000-0000-000000000001",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    assert response.mimetype == "application/yaml"
    assert response.headers["Content-Disposition"] == (
        'attachment; filename="archive-structure-proposal-fasnacht.yaml"'
    )
    assert response.headers["X-Archive-Proposal-Warnings"] == "1"
    assert response.headers["Cache-Control"] == "no-store"
    assert "archive:\n" in response.text
    assert "Archive levels are suggestions" in response.text
    assert len(calls) == 1


def test_download_hides_permission_failures_as_not_found(monkeypatch):
    def denied(*_args):
        raise OldapErrorNoPermission("secret")

    client = _client(monkeypatch, denied)
    response = client.get(
        "/archive/fasnacht/staging-proposal?stagingAreaIri=urn:uuid:00000000-0000-0000-0000-000000000001",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 404
    assert "secret" not in response.text


def test_download_rejects_missing_staging_area_iri_without_calling_service(monkeypatch):
    called = False

    def build(*_args):
        nonlocal called
        called = True

    client = _client(monkeypatch, build)
    response = client.get(
        "/archive/fasnacht/staging-proposal",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 400
    assert not called


def test_preflight_requires_authentication_and_performs_no_apply(monkeypatch):
    client = _client(monkeypatch, lambda *_args: None)
    applied = False

    def prepare(_connection, project, yaml_text):
        assert project == "fasnacht"
        assert yaml_text == "archive: {}"
        return object()

    def plan_json(_prepared):
        return {"documentHash": "a" * 64, "unitCount": 0, "units": []}

    monkeypatch.setattr(archive_views, "prepare_archive_upload", prepare)
    monkeypatch.setattr(archive_views, "archive_plan_json", plan_json)
    monkeypatch.setattr(
        archive_views,
        "apply_archive_upload",
        lambda *_args: globals().update(),
    )

    unauthenticated = client.post(
        "/archive/fasnacht/imports/preflight", json={"yaml": "archive: {}"}
    )
    response = client.post(
        "/archive/fasnacht/imports/preflight",
        json={"yaml": "archive: {}"},
        headers={"Authorization": "Bearer test-token"},
    )

    assert unauthenticated.status_code == 401
    assert response.status_code == 200
    assert response.json["documentHash"] == "a" * 64
    assert response.headers["Cache-Control"] == "no-store"
    assert not applied


def test_preflight_rejects_oversized_upload_and_missing_admin_create(monkeypatch):
    client = _client(monkeypatch, lambda *_args: None)
    oversized = client.post(
        "/archive/fasnacht/imports/preflight",
        json={"yaml": "x" * (archive_views.MAX_ARCHIVE_YAML_BYTES + 1)},
        headers={"Authorization": "Bearer test-token"},
    )
    assert oversized.status_code == 413

    def denied(*_args):
        raise OldapErrorNoPermission("missing ADMIN_CREATE")

    monkeypatch.setattr(archive_views, "prepare_archive_upload", denied)
    denied_response = client.post(
        "/archive/fasnacht/imports/preflight",
        json={"yaml": "archive: {}"},
        headers={"Authorization": "Bearer test-token"},
    )
    assert denied_response.status_code == 403


def test_apply_requires_confirmation_and_returns_created_iris(monkeypatch):
    client = _client(monkeypatch, lambda *_args: None)
    prepared = type("Prepared", (), {"document_hash": "b" * 64})()
    calls = []

    def apply(connection, project, yaml_text, expected_hash):
        calls.append((connection, project, yaml_text, expected_hash))
        return prepared, ("fasnacht:root", "fasnacht:child")

    monkeypatch.setattr(archive_views, "apply_archive_upload", apply)
    unconfirmed = client.post(
        "/archive/fasnacht/imports/apply",
        json={"yaml": "archive: {}", "documentHash": "b" * 64},
        headers={"Authorization": "Bearer test-token"},
    )
    response = client.post(
        "/archive/fasnacht/imports/apply",
        json={"yaml": "archive: {}", "documentHash": "b" * 64, "confirm": True},
        headers={"Authorization": "Bearer test-token"},
    )

    assert unconfirmed.status_code == 400
    assert response.status_code == 201
    assert response.json["createdCount"] == 2
    assert response.json["createdIris"] == ["fasnacht:root", "fasnacht:child"]
    assert len(calls) == 1


def test_apply_rejects_document_hash_mismatch_before_project_access():
    try:
        apply_archive_upload(None, "fasnacht", "archive: {}", "0" * 64)
    except ValueError as error:
        assert "does not match" in str(error)
    else:
        raise AssertionError("hash mismatch was accepted")


def test_staging_service_uses_only_visible_search_results_and_never_writes(monkeypatch):
    class VisibleAreaClass:
        name = Xsd_QName("fasnacht:StagingArea", validate=False)
        superclass = {Xsd_QName("shared:StagingArea", validate=False): None}

    class VisibleArea(VisibleAreaClass):
        pass

    factory = type("Factory", (), {"read": lambda self, _iri: VisibleArea()})()
    monkeypatch.setattr(archive_workflow, "ResourceInstanceFactory", lambda **_kwargs: factory)
    calls = []

    def search(**kwargs):
        calls.append(kwargs)
        if str(kwargs["resClass"]) == "shared:StagingFolder":
            return [
                {"iri": ["urn:top"], "schema:name": ["top"]},
                {
                    "iri": ["urn:series"],
                    "schema:name": ["Serie"],
                    "shared:inStagingFolder": ["urn:top"],
                },
            ]
        return [{"iri": ["urn:media"], "shared:inStagingFolder": ["urn:series"]}]

    monkeypatch.setattr(archive_workflow.ResourceInstance, "search", search)
    proposal = archive_workflow.build_visible_staging_archive_proposal(
        object(), "fasnacht", "urn:uuid:00000000-0000-0000-0000-000000000001"
    )

    assert proposal.document.units[0].title == "Serie"
    assert proposal.document.units[0].level == "File"
    assert len(calls) == 2
    assert all(call["limit"] > 0 for call in calls)
