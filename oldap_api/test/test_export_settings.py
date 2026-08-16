"""Deployment-policy tests for project-neutral ZIP exports."""

import pytest

from oldap_api.exports.domain import MAX_EXPORT_BYTES
from oldap_api.exports.settings import ExportOperatingPolicy


def test_export_policy_uses_approved_defaults() -> None:
    policy = ExportOperatingPolicy.from_environment({})

    assert policy.max_archive_bytes == MAX_EXPORT_BYTES
    assert policy.ready_retention_hours == 24
    assert policy.audit_retention_days == 60


def test_export_policy_accepts_bounded_environment_overrides() -> None:
    policy = ExportOperatingPolicy.from_environment(
        {
            "OLDAP_EXPORT_MAX_ARCHIVE_BYTES": "1000000",
            "OLDAP_EXPORT_READY_RETENTION_HOURS": "48",
            "OLDAP_EXPORT_AUDIT_RETENTION_DAYS": "90",
            "OLDAP_EXPORT_MAX_ACTIVE_JOBS_PER_USER": "4",
            "OLDAP_EXPORT_MAX_ACTIVE_JOBS_TOTAL": "40",
            "OLDAP_EXPORT_MAX_RESERVED_BYTES_PER_USER": "2000000",
            "OLDAP_EXPORT_MAX_RESERVED_BYTES_TOTAL": "9000000",
        }
    )

    assert policy == ExportOperatingPolicy(
        1_000_000, 48, 90, 4, 40, 2_000_000, 9_000_000
    )


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("OLDAP_EXPORT_MAX_ARCHIVE_BYTES", "0"),
        ("OLDAP_EXPORT_MAX_ARCHIVE_BYTES", str(MAX_EXPORT_BYTES + 1)),
        ("OLDAP_EXPORT_READY_RETENTION_HOURS", "0"),
        ("OLDAP_EXPORT_READY_RETENTION_HOURS", "745"),
        ("OLDAP_EXPORT_AUDIT_RETENTION_DAYS", "0"),
        ("OLDAP_EXPORT_AUDIT_RETENTION_DAYS", "3651"),
        ("OLDAP_EXPORT_AUDIT_RETENTION_DAYS", "sixty"),
        ("OLDAP_EXPORT_MAX_ACTIVE_JOBS_PER_USER", "0"),
        ("OLDAP_EXPORT_MAX_ACTIVE_JOBS_TOTAL", "0"),
        ("OLDAP_EXPORT_MAX_RESERVED_BYTES_PER_USER", "0"),
        ("OLDAP_EXPORT_MAX_RESERVED_BYTES_TOTAL", "0"),
    ],
)
def test_export_policy_rejects_unsafe_or_malformed_values(
    name: str, value: str
) -> None:
    with pytest.raises(ValueError, match=name):
        ExportOperatingPolicy.from_environment({name: value})
