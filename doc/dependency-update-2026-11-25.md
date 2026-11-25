# Dependency refresh — 2026-11-25

Updated all resolvable dependencies against live PyPI metadata: 34 locked packages
changed, including oldaplib 1.2.3 → 1.2.5, Redis client 7.4.0 → 8.2.0, Gunicorn 26.0.0 → 27.0.1,
pytest 9.1.1 → 9.2.0, Black 26.3.1 → 26.10.1, coverage 7.14.0 → 7.17.5,
and openapi-spec-validator 0.7.2 → 0.9.0. Raised direct dependency minimums
and updated the Docker builder's Poetry pin from 1.8.3 to 2.5.2.
Flask 3.1.3, Flask-CORS 6.0.5 and Requests 2.34.2 were already locked;
the manifest now requires those versions or newer compatible releases.

The published oldaplib 1.2.5 metadata constrains these exceptions:

| Package | Locked | Latest stable on PyPI | Library constraint |
| --- | --- | --- | --- |
| convertdate | 2.4.1 | 2.5.1 | ==2.4.1 |
| pyshacl | 0.31.0 | 0.40.2 | ==0.31.0 |
| validators | 0.35.0 | 0.36.0 | >=0.35.0,<0.36.0 |

All other locked packages match the latest stable PyPI release. Version-specific
PyPI JSON security metadata reported no known vulnerabilities for all 86 locked
packages. This is a point-in-time advisory check, not a source-code security audit.
Sources: https://pypi.org/pypi/oldaplib/1.2.5/json and
`https://pypi.org/pypi/{package}/{version}/json` for each lock entry.

## Verification

- `poetry check --lock`: passes; existing Poetry metadata deprecation warnings remain.
- `poetry build`: wheel and sdist pass.
- Clean Python 3.13 environment: install locked dependencies and built API wheel;
  `python -m pip check` passes.
- Python 3.13 and 3.14: each passes 493 offline tests and 32 subtests.
  Run with `--noconftest`, socket connect/connect_ex blocked, and the fixture-only
  `OLDAP_IMPORT_SERVICE_JWT_SECRET` from `test_import_internal.SERVICE_SECRET`.
  Select test modules without unresolved shared `client`, `token_headers`, or
  `connection_manager` fixtures. Exclude `test_restart_api`,
  `test_archive_placement_jena`, `test_writer_recovery_views` (services),
  `test_reifier_shapes` (unpackaged library test fixtures), and
  `test_export_phase1_acceptance` (sibling media worker).
  Deselect `test_internal_commit_route_is_claim_bound_and_exactly_replayable`:
  the network guard demonstrated that it requires real Redis.
- `python -m openapi_spec_validator API-def/oldap-api.yaml`: passes with 0.9.0.
  Fixed existing schema syntax: move projectIri's boolean `required` to its
  parent object's required array, quote one null type, and add a missing space
  in another null type. Preserved the pre-existing contract edits.

The repository `.venv` was updated to the lock, replacing its editable oldaplib
installation with published 1.2.5 with Redis client 8.2.0. Its unrelated oldap-tools 0.1.9 installation
still declares oldaplib <0.5.0, so that existing mixed environment fails
`pip check`; the clean API environment above does not. No API source changes,
service restarts, live-data tests, image builds, publication or deployment.

## Published Redis-compatible library integration

oldaplib 1.2.5 is published and its wheel/sdist SHA-256 hashes are verified
against PyPI downloads. API requirements now use `oldaplib>=1.2.5,<2.0.0` and
`redis>=8.2.0,<9.0.0`. The targeted follow-up changes only those two lock
entries; the preceding dependency/contract updates are preserved.
Both Python 3.13 and 3.14 repeat the 493-test / 32-subtest offline acceptance
with the published library and Redis 8.2.0. Library release acceptance adds
73 tests / 9 subtests on isolated AOF Redis, including real cache and recovery
operations. No API release, image build or deployment is included.
