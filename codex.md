# OLDAP API Codex Context

OLDAP API is a Flask REST API that exposes OLDAP administration, data modelling,
hierarchical list, resource, and instance operations backed by GraphDB through
`oldaplib`.

## Repository State

- Python project managed by Poetry.
- Main package: `oldap_api`.
- OpenAPI contract: `API-def/oldap-api.yaml`.
- Instance search documentation: `doc/search_instance.md`.
- Tests live in `oldap_api/test` and rely on a local GraphDB repository plus
  OLDAP test data from the sibling `oldaplib` repository.
- The lock file currently resolves `oldaplib` to version `0.6.11`.

## Architecture

- `oldap_api.factory.factory()` creates the Flask app and registers all
  blueprints from `oldap_api/views`.
- View modules translate HTTP payloads and query parameters into `oldaplib`
  calls, then serialize OLDAP/XSD values into JSON.
- Instance create/update payloads are documented in `API-def/oldap-api.yaml`
  as ontology-driven maps; `oldap:attachedToRole` is the special instance
  permission map and supports role-to-DataPermission replacement plus `add`/`del`
  patches on update.
- `POST /data/{project}/{instiri}/transform` is the generic resource lifecycle
  endpoint for atomic class transformations that keep the same IRI. It delegates
  the ontology validation and GraphDB transaction to `oldaplib`.
- `oldaplib` owns GraphDB access, domain validation, resource instance classes,
  permissions, and data model interpretation.
- The API should avoid duplicating domain logic from `oldaplib` unless it is
  specifically shaping HTTP response contracts.
- MediaObject lookup endpoints expose the shared media access contract returned
  by `oldaplib`, including `shared:mediaAccessMode` plus optional external
  `shared:mediaUrl` and `shared:thumbnailUrl`.

## Current Conventions

- Code and documentation inside the repository are written in English.
- User communication is in German unless explicitly requested otherwise.
- Keep changes focused and follow existing Flask blueprint patterns.
- Public API changes should update `API-def/oldap-api.yaml` and relevant tests.

## Roadmap / Next Steps

- Keep instance read responses stable while exposing reasoning-derived metadata
  explicitly.
- Continue consolidating duplicated instance-read logic when broader refactoring
  is warranted.
