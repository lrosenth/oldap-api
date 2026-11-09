# Real Fasnacht fulltext acceptance

The owned real-export API rehearsal supports `--fulltext-preview` together with
`--fasnacht-only --fasnacht-export <native-export> --browser-preview`. It runs
against fresh Jena and isolated Redis, provisions the public/audit fixture
identities, and activates the nine fields from
`../oldap-tools/examples/ontology/fasnacht-jena.yaml` through the normal tools
`ontology load --fulltext apply` command. The full model is imported first;
the field-only YAML updates index configuration without replacing the model.
No live GraphDB connector or shared service is modified.

The importer dry-run precedes activation; a repeated unchanged field map must
plan no writes. The rehearsal checks actual title/phrase/prefix/path searches,
deduplicated aliases, counts/paging, public PDF extracted text and internal PDF
visibility. It then creates a disposable model property and pre-existing text,
adds its field to an owned YAML copy, and checks that reconfiguration indexes it
without changing the search code. Removing/restoring an asserted public role edge
must change result/count visibility even while its annotation and index text
remain present. The original nine-field map is restored before browser testing.

Private `fulltext-tools.log` and `fulltext-results.json` retain timings and check
results. Browser readiness follows only after automated checks pass. Stop via
`browser-stop`; the existing 20-minute deadline also closes owned services.
Start the frontend on 127.0.0.1:5179 with API origins from `browser-ready.json`.
This fulltext run need not start image/PDF binary servers; binary display is
covered by the separate media rehearsals.

This is migration acceptance, not a complete proof of analyzer parity or a
production load test. The portable field map does not copy GraphDB connector
language/type/analyzer restrictions. Normal class filters and current root
resource permissions remain enforced by the ordinary API. Configured relation paths now require DATA_VIEW for each referenced resource
as well as the returned root. This closes the reproduced case where a public
media object could be discovered through words in a private linked title.
Membership revocation must hide such hits/counts even if the annotation remains.
Paths through ungranted embedded nodes do not inherit access implicitly.


## Search wording

As explicitly chosen by the user, ordinary words require all words regardless of
order. Separate indexed values of the same configured field may supply them;
quoted phrases must match one indexed value. Field filters still combine using
their explicit AND/OR operators. The current frontend combines field alternatives
with OR: a multiword match must be satisfied within one such configured field,
not by mixing unrelated fields. Arbitrary Lucene expressions remain unsupported.

The real export has extracted text for public PDFs but the first internal PDF
fixture has none. The helper selects existing internal extracted text if present;
otherwise it adds an unmistakably synthetic word to a real internal PDF only in
the disposable target, and records that distinction in its evidence. It does not
claim that missing source PDF text was migrated or extracted by this step.

## Concurrency correction

The first browser run reproduced HTTP 400 during simultaneous searches. The
underlying FULLTEXT_STATE operation requested the same exclusive maintenance lock
as rebuilding an index and returned 409 whenever a reader was active. State
inspection now runs on the engine owner thread without that exclusive lock:
configuration replacement is serialized on that thread, and the query still
validates its configuration revision under the data read lock. FULLTEXT_APPLY
retains its writer/session exclusions. The rehearsal sends four simultaneous
class-filtered searches to cover this browser request pattern. The dedicated
activation/failure/revision suite passes all 46 checks after the correction.

## Recorded acceptance, 2026-10-31

The final owned run `fasnacht-fulltext-04` passes all 26 fulltext checks,
including four concurrent class searches. The normal export/model rehearsal
also passes its 23 checks. Offline library/API/tools tests pass 27/13/21 checks;
the dedicated Java activation/failure/revision suite passes 46 checks.
[Fulltext results](jena-fasnacht-fulltext-results.json) retain the check names and
22 sequential query measurements: median 3,481 ms, maximum 7,552 ms. Initial YAML
apply took 2,525 ms including CLI/HTTP overhead. These are local rehearsal timings,
not pure Lucene benchmarks or production load measurements.

The unchanged archive frontend against the owned API returns 20 public matches
for `Laterne Stamm`: 14 media, five objects and one event. The reverse word order `Stamm Laterne` produces the same displayed counts. The
original parallel request conflict no longer occurs. Browser evidence is kept privately alongside
the run as `browser-fulltext.png`. Image/PDF binary services were deliberately not
started for this search rehearsal; missing thumbnails are not a delivery test.
The export remains unchanged and no production service was updated.

Follow-up: [query placement optimization](jena-fulltext-performance.md) now reduces
representative search HTTP medians to 56–143 ms with equal responses. Next verify
language/analyzer behavior on representative German text. The earlier multi-second measurements above describe the pre-optimization
baseline. Production load and browser-wide readiness still need separate assessment. GraphDB comparison remains deferred.

## Approved spelling tolerance

The shared analyzer now folds Latin accents/umlauts/ß and canonical Unicode
without stemming; wildcard terms use the same normalization. See the
[language contract and rebuild requirement](../../oldaplib/docs/migration/jena-fulltext-language.md).
The current acceptance has 30 fulltext checks, including decomposed text in a
new YAML field and unchanged returned literals. [Latest evidence](jena-fulltext-folding-results.json)
records a local median of 87.5 ms across 26 measured searches. Rebuilding the
managed service index at startup is necessary; identical YAML replay is a no-op.
