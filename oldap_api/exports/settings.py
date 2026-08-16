"""Validated environment-specific operating policy for ZIP exports."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

from .domain import AUDIT_RETENTION_DAYS, MAX_EXPORT_BYTES, READY_RETENTION_HOURS

MAX_READY_RETENTION_HOURS = 24 * 31
MAX_AUDIT_RETENTION_DAYS = 3650
MAX_ACTIVE_EXPORT_JOBS = 10_000
MAX_RESERVED_EXPORT_BYTES = 5_000_000_000_000


@dataclass(frozen=True, slots=True)
class ExportOperatingPolicy:
    """Bound deployment-specific limits without weakening the v1 hard ceiling."""

    max_archive_bytes: int = MAX_EXPORT_BYTES
    ready_retention_hours: int = READY_RETENTION_HOURS
    audit_retention_days: int = AUDIT_RETENTION_DAYS
    max_active_jobs_per_user: int = 3
    max_active_jobs_total: int = 20
    max_reserved_bytes_per_user: int = 100_000_000_000
    max_reserved_bytes_total: int = 500_000_000_000

    def __post_init__(self) -> None:
        if not 1 <= self.max_archive_bytes <= MAX_EXPORT_BYTES:
            raise ValueError(
                f"OLDAP_EXPORT_MAX_ARCHIVE_BYTES must be between 1 and {MAX_EXPORT_BYTES}."
            )
        if not 1 <= self.ready_retention_hours <= MAX_READY_RETENTION_HOURS:
            raise ValueError(
                "OLDAP_EXPORT_READY_RETENTION_HOURS must be between 1 and "
                f"{MAX_READY_RETENTION_HOURS}."
            )
        if not 1 <= self.audit_retention_days <= MAX_AUDIT_RETENTION_DAYS:
            raise ValueError(
                "OLDAP_EXPORT_AUDIT_RETENTION_DAYS must be between 1 and "
                f"{MAX_AUDIT_RETENTION_DAYS}."
            )
        if not 1 <= self.max_active_jobs_per_user <= MAX_ACTIVE_EXPORT_JOBS:
            raise ValueError(
                "OLDAP_EXPORT_MAX_ACTIVE_JOBS_PER_USER must be between 1 and "
                f"{MAX_ACTIVE_EXPORT_JOBS}."
            )
        if (
            not self.max_active_jobs_per_user
            <= self.max_active_jobs_total
            <= MAX_ACTIVE_EXPORT_JOBS
        ):
            raise ValueError(
                "OLDAP_EXPORT_MAX_ACTIVE_JOBS_TOTAL must be at least the per-user "
                f"limit and at most {MAX_ACTIVE_EXPORT_JOBS}."
            )
        if not 1 <= self.max_reserved_bytes_per_user <= MAX_RESERVED_EXPORT_BYTES:
            raise ValueError(
                "OLDAP_EXPORT_MAX_RESERVED_BYTES_PER_USER must be between 1 and "
                f"{MAX_RESERVED_EXPORT_BYTES}."
            )
        if not (
            self.max_reserved_bytes_per_user
            <= self.max_reserved_bytes_total
            <= MAX_RESERVED_EXPORT_BYTES
        ):
            raise ValueError(
                "OLDAP_EXPORT_MAX_RESERVED_BYTES_TOTAL must be at least the per-user "
                f"limit and at most {MAX_RESERVED_EXPORT_BYTES}."
            )

    @classmethod
    def from_environment(
        cls, environment: Mapping[str, str] | None = None
    ) -> "ExportOperatingPolicy":
        """Parse integer policy values and reject malformed deployment input."""

        env = os.environ if environment is None else environment
        return cls(
            max_archive_bytes=_integer(
                env, "OLDAP_EXPORT_MAX_ARCHIVE_BYTES", MAX_EXPORT_BYTES
            ),
            ready_retention_hours=_integer(
                env, "OLDAP_EXPORT_READY_RETENTION_HOURS", READY_RETENTION_HOURS
            ),
            audit_retention_days=_integer(
                env, "OLDAP_EXPORT_AUDIT_RETENTION_DAYS", AUDIT_RETENTION_DAYS
            ),
            max_active_jobs_per_user=_integer(
                env, "OLDAP_EXPORT_MAX_ACTIVE_JOBS_PER_USER", 3
            ),
            max_active_jobs_total=_integer(
                env, "OLDAP_EXPORT_MAX_ACTIVE_JOBS_TOTAL", 20
            ),
            max_reserved_bytes_per_user=_integer(
                env, "OLDAP_EXPORT_MAX_RESERVED_BYTES_PER_USER", 100_000_000_000
            ),
            max_reserved_bytes_total=_integer(
                env, "OLDAP_EXPORT_MAX_RESERVED_BYTES_TOTAL", 500_000_000_000
            ),
        )


def _integer(environment: Mapping[str, str], name: str, default: int) -> int:
    value = environment.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be an integer.") from error


__all__ = ["ExportOperatingPolicy"]
