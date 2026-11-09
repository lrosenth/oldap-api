# API 1.0.1 production deployment — 2026-11-10

Owner-authorized publication and production rollout. Both tested images were
pushed without rebuilding; the new multiarchitecture tag is
`lrosenth/oldap-api:v1.0.1@sha256:7fed616c31b8c298d02778e807bb0713746f0f21cb722662548796d9a573070a`.
Published architecture digests equal the accepted local image IDs recorded in
`performance-release-1.0.1.md`. Existing tags/latest were not overwritten.

Production now runs API and independent identity verifier with API/library 1.0.1.
The guarded rollout pre-pulled the image, acquired the existing maintenance lock,
verified all installed image selections, saved Compose, replaced only the shared
API image reference, and checked readiness. No RDF migration was needed.
Container identity comparison confirms only these two services changed; Jena,
Redis, Caddy, frontends and SALSAH are unchanged. The maintenance lock was released.

## Acceptance and recovery

Both architectures passed 61 focused installed-image tests before publication.
Production post-checks pass: backend readiness, admin/public authentication,
private-route protection, role reads, stories, fulltext and signed image delivery.
Thirty stories and ten fulltext matches were returned. No real upload was made;
media token checks stop at missing-form validation.

Rollback Compose:
`/opt/oldap/compose/docker-compose.yml.before-api-1.0.1-20261110T002006`.
Under the established maintenance lock, restore that file and run
`docker compose up -d --no-deps --wait oldap-jena-identity oldap-api`
in `/opt/oldap/compose`, then repeat readiness/functional checks.
No database restore is required for this client-only rollback.

Private evidence, exact deployment playbook, immutable selections and container
IDs are retained at:
`/Users/rosenth/Library/Application Support/OLDAP-Jena/releases/20261110-performance-1.0.1/`.
Earlier build-only notes describe historical checkpoints. API PyPI publication
is not required for subsequent releases; the existing 1.0.1 upload is retained.

## Browser comparison

Three repeats per case, same production frontend and client path. Visible titles,
tabs and links match before/after; all observed API responses succeed. These are
small warm samples, not a load test or guaranteed latency.

| Case | Before median (ms) | After median (ms) |
|---|---:|---:|
| text | 1845 | 1500 |
| year | 1621 | 1324 |
| image | 1934 | 1478 |
| detail | 2387 | 2289 |

Observed API responses after deployment: 231.
