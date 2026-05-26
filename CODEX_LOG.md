### Update 2026-05-26 14:45
- Decisions: Keep `rdf:type` backward compatible by returning only explicit resource type assertions from the project data graph. Expose reasoning-derived types separately as `virtual:inferredTypes`.
- Implementation: Updated instance read response shaping, OpenAPI `InstanceData`, and the read-instance regression test.
- Open: None.
- Risks/Assumptions: Assumes explicit `rdf:type` assertions in the project data graph represent the API-compatible resource class contract.
