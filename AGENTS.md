# Repository instructions

- Keep `API-def/oldap-api.yaml` synchronized with route validation and serializers in `oldap_api/views`; clients in sibling repositories generate code from this contract.
- Use isolated fixtures for API tests. Do not run tests that mutate configured Jena, Redis, or external services without confirming a disposable target.
- Follow `doc/reification-model.md` and `doc/reification-instances.md` for model and instance annotation contracts.
