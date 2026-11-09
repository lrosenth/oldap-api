# API/library performance release 1.0.1

Both performance branches were fast-forwarded into main and versioned 1.0.1.
API requires oldaplib >=1.0.1,<2.0.0. The targeted Poetry update retained all
third-party lock versions; it synchronized the previously outdated local venv.

## Distribution

Publish oldaplib to PyPI. Build the API wheel as an input to its Docker image;
API releases do not require PyPI publication. API 1.0.1 had already been uploaded
when the owner clarified this policy. No deletion or further API upload is planned.
Both published distributions were checked against the registry SHA-256 hashes.

## Image build

The isolated build context uses the existing oldap-setup/release/Dockerfile.jena
recipe, exact 1.0.1 wheels, and third-party constraints from the accepted 1.0.0
release. It excludes checkout secrets and does not use the legacy API Dockerfile.
Base image: python@sha256:ae14d4ce8771606477a81446e7ef429edd6762305fc50c84507c1041fa8285d1.

Private artifacts and build logs:
`/Users/rosenth/Library/Application Support/OLDAP-Jena/releases/20261110-performance-1.0.1/`.
The `api-image/release.json` records source revisions and input hashes.

Local image tags: `lrosenth/oldap-api:v1.0.1-amd64` and
`lrosenth/oldap-api:v1.0.1-arm64`. Docker registry publication and deployment
are separate steps. Existing images, latest tags, and running services are unchanged.

## Acceptance

The installed library passes 61 focused tests. Tests are copied outside the
library package because distributions intentionally exclude `oldaplib.test`.
Container acceptance checks both package versions, Jena imports, the existing
UID/GID 100/101 contract, pip dependency consistency, and the same 61 tests.
Full live-service/browser acceptance remains necessary before deployment.

Completed: AMD64 and ARM64 each pass all 61 tests, package/user/import checks,
and pip check. Local image IDs are recorded in the private `built.json`.
AMD64: `sha256:a0d84fd5154e65d93af1d400f5dc1dbdfe69e758aec4132fa8d7760713811954`.
ARM64: `sha256:95f5ec386dd617b99fa1d5bed416ff44201871e706bf7c5399286081ddf28b55`.
No registry push or deployment was performed.
