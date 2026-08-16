"""Phase-0 tests for the project-neutral ZIP export boundary."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import jwt

from oldap_api.exports.capabilities import (
    DOWNLOAD_TOKEN_AUDIENCE,
    ExportDownloadCapabilityIssuer,
)
from oldap_api.exports.domain import (
    AUDIT_RETENTION_DAYS,
    MAX_EXPORT_BYTES,
    READY_RETENTION_HOURS,
    ExportKind,
    ExportState,
    ExportStateConflict,
    ExportJob,
    ExportProgress,
    ExportClaim,
    ExportSelectionSnapshot,
    ExportTask,
    ExportVersionConflict,
    allowed_export_transition,
)
from oldap_api.exports.profiles import ExportProfileError, parse_export_profile
from oldap_api.exports.repository import (
    ExportAlreadyExistsError,
    ExportRepositoryConflict,
    InMemoryExportJobRepository,
)

CONTRACT_ROOT = Path(__file__).resolve().parents[2] / "doc" / "zip-export" / "v1"
NOW = datetime(2026, 8, 14, 10, 0, tzinfo=UTC)
SHA = "a" * 64


def fasnacht_profile() -> dict:
    """Return the first real project profile as plain trusted configuration."""

    return {
        "profileId": "fasnacht-v1",
        "profileVersion": "1.0.0",
        "projectShortName": "fasnacht",
        "allowedArchiveMediaClasses": ["fasnacht:ArchiveMediaObject"],
        "metadata": {
            "archiveMedia": [
                {
                    "columnName": "publication_status",
                    "propertyIri": "fasnacht:publicationStatus",
                    "valueShape": "iri",
                    "resolveLabels": True,
                },
                {
                    "columnName": "archive_targets",
                    "propertyIri": "fasnacht:archiveMediaObjectOf",
                    "valueShape": "iri-list",
                    "resolveLabels": True,
                },
            ],
            "archiveUnits": [],
            "stagingMedia": [],
        },
    }


def test_operating_limits_match_approved_phase_zero_values():
    assert MAX_EXPORT_BYTES == 50_000_000_000
    assert READY_RETENTION_HOURS == 24
    assert AUDIT_RETENTION_DAYS == 60


def test_closed_lifecycle_accepts_build_and_cleanup_paths():
    allowed_export_transition(ExportState.QUEUED, ExportState.BUILDING)
    allowed_export_transition(ExportState.BUILDING, ExportState.READY)
    allowed_export_transition(ExportState.READY, ExportState.EXPIRED)
    allowed_export_transition(ExportState.EXPIRED, ExportState.DELETING)
    allowed_export_transition(ExportState.DELETING, ExportState.DELETED)


def test_closed_lifecycle_rejects_ready_to_building():
    with pytest.raises(ExportStateConflict):
        allowed_export_transition(ExportState.READY, ExportState.BUILDING)


def queued_job() -> ExportJob:
    """Return one minimal valid project-neutral queued export."""

    return ExportJob(
        export_id="11111111-1111-4111-8111-111111111111",
        state=ExportState.QUEUED,
        state_version=0,
        created_at=NOW,
        updated_at=NOW,
        requested_by_iri="https://oldap.org/users/alice",
        requested_by_user_id="alice",
        selection=ExportSelectionSnapshot(
            project_short_name="museum",
            kind=ExportKind.ARCHIVE_UNIT,
            selection_iri="urn:uuid:22222222-2222-4222-8222-222222222222",
            display_name="Posters",
            display_path="Collection/Posters",
            profile_id="museum-v1",
            profile_version="1.0.0",
            profile_sha256=SHA,
        ),
        estimated_source_bytes=12_345,
        progress=ExportProgress(files_total=2, bytes_total=12_345),
    )


def ready_job() -> ExportJob:
    """Return a complete READY job through the real transition boundary."""

    building = queued_job().transition(
        ExportState.BUILDING,
        expected_state_version=0,
        now=NOW + timedelta(minutes=1),
        snapshot_at=NOW + timedelta(minutes=1),
        manifest_sha256=SHA,
    )
    return building.transition(
        ExportState.READY,
        expected_state_version=1,
        now=NOW + timedelta(minutes=2),
        ready_at=NOW + timedelta(minutes=2),
        expires_at=NOW + timedelta(hours=24, minutes=2),
        archive_size_bytes=10_000,
        archive_sha256="b" * 64,
        progress=ExportProgress(
            files_done=2,
            files_total=2,
            bytes_done=12_345,
            bytes_total=12_345,
        ),
    )


def test_job_transition_is_immutable_and_optimistically_versioned():
    original = queued_job()
    building = original.transition(
        ExportState.BUILDING,
        expected_state_version=0,
        now=NOW + timedelta(minutes=1),
        snapshot_at=NOW + timedelta(minutes=1),
        manifest_sha256=SHA,
    )
    assert original.state is ExportState.QUEUED
    assert building.state is ExportState.BUILDING
    assert building.state_version == 1
    with pytest.raises(ExportVersionConflict):
        building.transition(ExportState.FAILED, expected_state_version=0)


def test_ready_job_requires_complete_artifact_evidence():
    with pytest.raises(ValueError, match="complete artifact evidence"):
        queued_job().transition(
            ExportState.BUILDING, expected_state_version=0
        ).transition(
            ExportState.READY,
            expected_state_version=1,
        )


def test_ready_job_public_contract_hides_internal_manifest_and_user_id():
    value = ready_job().to_dict(now=NOW + timedelta(minutes=3))
    assert value["canDownload"] is True
    assert value["selection"]["profileId"] == "museum-v1"
    assert "manifestSha256" not in value
    assert "requestedByUserId" not in value


def test_deleting_or_deleted_job_cannot_be_deleted_again():
    deleting = ready_job().transition(
        ExportState.DELETING,
        expected_state_version=2,
        now=NOW + timedelta(minutes=4),
    )
    deleted = deleting.transition(
        ExportState.DELETED,
        expected_state_version=3,
        now=NOW + timedelta(minutes=5),
        deleted_at=NOW + timedelta(minutes=5),
    )
    assert deleting.to_dict()["canDelete"] is False
    assert deleted.to_dict()["canDelete"] is False


def test_worker_claim_payload_depends_on_task():
    build = ExportClaim(
        claim_id="33333333-3333-4333-8333-333333333333",
        export_id=queued_job().export_id,
        task=ExportTask.BUILD,
        state_version=1,
        claimed_at=NOW,
        lease_expires_at=NOW + timedelta(minutes=2),
        manifest_sha256=SHA,
    )
    assert build.to_dict()["manifestSha256"] == SHA
    with pytest.raises(ValueError, match="CLEANUP claims require"):
        ExportClaim(
            claim_id="44444444-4444-4444-8444-444444444444",
            export_id=queued_job().export_id,
            task=ExportTask.CLEANUP,
            state_version=2,
            claimed_at=NOW,
            lease_expires_at=NOW + timedelta(minutes=2),
            manifest_sha256=SHA,
        )


def test_download_capability_is_exact_purpose_and_never_outlives_job():
    secret = "export-download-test-secret-at-least-32-bytes"
    authorization = ExportDownloadCapabilityIssuer(
        secret=secret,
        media_export_base_url="https://media.example.org",
        issuer="https://oldap.example.org",
        ttl_seconds=48 * 60 * 60,
    ).issue(ready_job(), now=NOW + timedelta(minutes=3))
    token = authorization.url.split("token=", maxsplit=1)[1]
    claims = jwt.decode(
        token,
        secret,
        algorithms=["HS256"],
        audience=DOWNLOAD_TOKEN_AUDIENCE,
        issuer="https://oldap.example.org",
        options={"verify_exp": False},
    )
    assert claims["typ"] == "export-download"
    assert claims["exportId"] == ready_job().export_id
    assert datetime.fromtimestamp(claims["exp"], tz=UTC) == ready_job().expires_at
    assert authorization.expires_at == ready_job().expires_at


def test_download_capability_rejects_non_ready_job():
    issuer = ExportDownloadCapabilityIssuer(secret="x" * 32)
    with pytest.raises(ValueError, match="not downloadable"):
        issuer.issue(queued_job(), now=NOW)


def test_download_capability_requires_an_explicit_media_origin(monkeypatch):
    monkeypatch.delenv("OLDAP_MEDIA_EXPORT_URL", raising=False)
    issuer = ExportDownloadCapabilityIssuer(
        secret="export-download-test-secret-at-least-32-bytes"
    )

    with pytest.raises(RuntimeError, match="OLDAP_MEDIA_EXPORT_URL"):
        issuer.issue(ready_job(), now=NOW)


def test_repository_never_overwrites_or_accepts_stale_versions():
    repository = InMemoryExportJobRepository()
    original = queued_job()
    repository.create(original)
    with pytest.raises(ExportAlreadyExistsError):
        repository.create(original)
    building = original.transition(
        ExportState.BUILDING,
        expected_state_version=0,
        snapshot_at=NOW,
        manifest_sha256=SHA,
    )
    repository.save(building, expected_previous_version=0)
    with pytest.raises(ExportRepositoryConflict):
        repository.save(building, expected_previous_version=0)


def test_repository_lists_only_caller_owned_jobs():
    repository = InMemoryExportJobRepository()
    repository.create(queued_job())
    assert repository.list_for_user("https://oldap.org/users/alice") == (queued_job(),)
    assert repository.list_for_user("https://oldap.org/users/bob") == ()


def test_fasnacht_profile_round_trips_canonically():
    profile = parse_export_profile(fasnacht_profile())
    assert profile.profile_id == "fasnacht-v1"
    assert profile.project_short_name == "fasnacht"
    assert profile.to_dict() == fasnacht_profile()


def test_second_project_uses_same_profile_boundary_without_fasnacht_terms():
    profile = parse_export_profile(
        {
            "profileId": "museum-v1",
            "profileVersion": "1.0.0",
            "projectShortName": "museum",
            "allowedArchiveMediaClasses": ["museum:DigitalSurrogate"],
            "metadata": {
                "archiveMedia": [
                    {
                        "columnName": "digitization_method",
                        "propertyIri": "museum:digitizationMethod",
                        "valueShape": "scalar",
                        "resolveLabels": False,
                    }
                ],
                "archiveUnits": [],
                "stagingMedia": [],
            },
        }
    )
    assert profile.allowed_archive_media_classes == ("museum:DigitalSurrogate",)
    assert profile.archive_media[0].column_name == "digitization_method"


@pytest.mark.parametrize("name", ["fasnacht-v1", "museum-v1"])
def test_documented_profile_examples_use_the_runtime_boundary(name):
    path = CONTRACT_ROOT / "examples" / f"{name}.profile.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    assert parse_export_profile(value).to_dict() == value


def test_generic_export_runtime_contains_no_fasnacht_vocabulary():
    package_root = Path(__file__).resolve().parents[1] / "exports"
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in package_root.glob("*.py")
    )
    assert "fasnacht:" not in source


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value.update({"unexpected": True}), "Unknown profile fields"),
        (
            lambda value: value["metadata"]["archiveMedia"][0].update(
                {"columnName": "relative_path"}
            ),
            "reserved metadata column",
        ),
        (
            lambda value: value["metadata"]["archiveMedia"][0].update(
                {"propertyIri": "file:///etc/passwd"}
            ),
            "expected QName or HTTP",
        ),
        (
            lambda value: value["metadata"]["archiveMedia"][0].update(
                {"valueShape": "python-callback"}
            ),
            "Unsupported metadata valueShape",
        ),
        (
            lambda value: value["metadata"]["archiveMedia"][0].update(
                {"propertyIri": "shared:path"}
            ),
            "Security-sensitive metadata property is reserved",
        ),
    ],
)
def test_profile_cannot_extend_security_sensitive_behavior(mutation, message):
    value = fasnacht_profile()
    mutation(value)
    with pytest.raises(ExportProfileError, match=message):
        parse_export_profile(value)


def test_profile_accepts_path_based_http_property_iris():
    value = fasnacht_profile()
    value["metadata"]["archiveMedia"][0]["propertyIri"] = "https://schema.org/name"
    assert (
        parse_export_profile(value).archive_media[0].property_iri
        == "https://schema.org/name"
    )
