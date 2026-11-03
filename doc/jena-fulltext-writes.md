# Fulltext search after real resource writes

## Scope

The normal API/Jena acceptance runner now verifies the complete path from real
resource mutations to `/data/search/<project>` results. It uses the regular
connection factory, managed field configuration and Jena Text index. No search
or connection implementation is replaced. Only Redis object-cache I/O is
suppressed in the owned test environment.

This stage adds acceptance coverage rather than another application abstraction.
The existing implementation must keep committed RDF and search results aligned,
and apply current RDF permissions when producing both hits and counts.

## Checks

`tools/migration/check_fulltext_writes.py` runs after the existing resource stage:

- Activate a field after its text already exists: rebuild makes the old data
  searchable without rewriting the resource.
- Create another resource through the API: it enters search immediately after
  commit; counts and pagination agree.
- Update text: the old term disappears and the new term appears.
- Abort an update or deletion via the existing callback: original hits remain.
- Abort an enclosing transaction after create: pending text never becomes a hit.
- Downgrade an object grant below DATA_VIEW: both hits and counts disappear.
  Restore its permission: visibility returns without rewriting indexed text.
- Add a new modeled text property and then configure its field: existing values
  become searchable without code changes. Unknown fields are rejected first.
- Combine two configured fields with AND and request projected properties.
- Change a field mapping while another connection holds its compiled revision:
  the old connection is rejected; fresh API requests use the new mapping.
- Restore the original mapping, then delete resources: removed text no longer
  contributes hits or counts.

Tokens are synthetic and unique to this fixture. Searches use an ordinary user
with a role membership rather than administrator privileges. Permission
restoration uses the existing creator-aware class read, because the established
factory-read contract requires a visible role grant. Direct Python assignment
uses typed QName/DataPermission values; API request bodies remain unchanged.

Run the owned fixture as documented in `jena-api-startup.md`. The retained
`jena-fulltext-writes-results.json` includes preceding model/list, tools, user and
resource checks as well as this search stage. The runner closes its own server
and dataset; it does not switch or mutate shared services.

## Interpretation and remaining gates

Index visibility follows successful transactions. Search authorization is checked
against current asserted memberships and RDF 1.2 grants, rather than copied into
Lucene documents; consequently revocation does not require a text rebuild.
Field mappings remain project configuration. Their revision is checked by the
service so a compiled search cannot silently run with a changed meaning.

This run does not establish large-dataset latency, concurrent rebuild throughput,
production Redis/cache behavior or restart recovery through the normal API.
Earlier isolated restart/crash probes remain separate evidence. Supported query
syntax and scoring limits documented in the fulltext migration reports still
apply. Remaining legacy bulk/copy/export paths and specialized archive/media
workflows remain separate migration work.
