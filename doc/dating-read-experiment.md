# Focused search dating read experiment

Historical query-only experiment; superseded by [local integration and calendar correction](dating-read-integration.md). The results below describe the original experiment.

Status at measurement: local experiment on `experiment/dating-read-performance`; runtime callers and production remain unchanged. Public signatures and RDF storage are unchanged.

## Hypothesis and implementation

Archive search expands requested dating fields through the general summary reader. That reader returns permission metadata and combines class, permission and date bindings, although search only consumes the dating fields. The private `_build_search_dating_query` in sibling oldaplib separates class and date branches and filters readable resources once. It retains asserted types as well as ancestors, modeled property resolution, creator/role access and existing `before` traversal. It omits role metadata deliberately and is therefore **not** a replacement for general `read_summaries`.

`tools/migration/experiment_dating_read.py` temporarily selects this query only during search-date expansion on an owned native preview. Its process-global monkeypatch is a sequential experiment mechanism, unsuitable for a deployed or concurrent application. The existing factory, decoder and JSON serializer remain in place, so the experiment isolates the query change.

## Verification and measurement

The runner compares complete ordered responses for public and audit readers across the nine captured overview requests and an additional media search requesting `fasnacht:creationDating`. Dating searches compare both structured and legacy JSON (24 comparisons). Unordered inner RDF value collections are canonicalized; outer search order remains significant.

Synthetic RDF additionally covers shared date nodes, creator access, hidden/restricted resources, a grant without an asserted role link, missing resources/dates, dangling references, decade precision, verbatim uncertainty, calendar metadata and a `before` chain. Candidate date values and resource classes/asserted types must match baseline. Role metadata is intentionally excluded from this private consumer comparison.

Only then does the runner time the CarnivalThing request (437 public / 442 audit rows), alternating baseline/candidate in ABBA order twice, with one warmup each, for both readers. These are warm, sequential local measurements on one older source export; they do not predict production latency, concurrent throughput or complete browser load time. Raw reports and mismatch payloads remain in the private probe directory.

## Separate existing decoder defect

Round-trip tests revealed that reading stored Julian dates loses their calendar: the decoder passes normalized Gregorian date strings to `Dating`, whose string parser assumes Gregorian. Julian decade ranges can additionally raise a precision error. Both baseline and candidate have this behavior. The experiment preserves it rather than mixing a semantic correction into a performance comparison. Two strict expected-failure tests in `oldaplib/test/test_dating_rdf_roundtrip.py` record the defect; Gregorian day and decade controls pass.

Correct calendar reconstruction is a separate follow-up, requiring preservation of both the normalized interval and original calendar/precision. Passing equivalence checks must not be interpreted as proof of Julian calendar correctness.

## Adoption gate

Before runtime adoption, replace the experiment patch with an explicit private dating-reader path, keep general summaries unchanged, cover modeled property inheritance and multi-type edge cases, and validate real installed-image behavior. Measure repeated prefix/model work separately; this experiment does not remove it. No reification or data migration is proposed.

## Results (2026-11-09)

Owned run `dating-read-experiment-04` passed: 24 complete HTTP comparisons, the native fixture group, and all 16 timed response comparisons. Focused Python regressions: 8 passed, 2 strict expected failures for the pre-existing Julian decoder defects. Compilation and diff whitespace checks pass.

| Reader / metric | Baseline median | Candidate median | Reduction |
| --- | ---: | ---: | ---: |
| Public search HTTP | 556.8 ms | 389.8 ms | 30.0% |
| Public Jena dispatch total | 295.5 ms | 192.5 ms | 34.8% |
| Audit search HTTP | 1128.7 ms | 820.8 ms | 27.3% |
| Audit Jena dispatch total | 856.5 ms | 614.7 ms | 28.2% |
| Public backend response bytes | 1,135,935 | 778,711 | 31.4% |

The request still makes 15 backend calls. Fewer returned role triples and less joined intermediate work help both Jena and Python, but repeated factory/model/prefix work remains. The result supports proceeding with an explicit private integration, without changing Dating storage. It does not justify extrapolating a 30% improvement to the entire archive page.

Earlier experiment iterations correctly failed when the candidate omitted asserted types (media-specific date fields disappeared); the final query explicitly retains them. Synthetic Julian cases then exposed the independent existing decoder defects described above. The final equivalence gate compares their baseline behavior, while strict xfails track correctness separately.

Sanitized metrics: [dating-read-experiment-results.json](dating-read-experiment-results.json). Source case payloads and full per-call timing evidence remain private. No changes were deployed or pushed.
