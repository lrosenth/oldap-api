# Broad metadata and dating search performance

## Decision and query structure

For Jena searches without text or mandatory relationship candidates, build a
small readable-resource relation from RDF 1.2 grants. Read `rdf:reifies` as a
whole triple term, check its predicate, and extract the resource and role with
`SUBJECT`/`OBJECT`. Require the user's current role, permission >= VIEW, and the
same asserted resource-role membership. Project distinct resource/type pairs
before property/date joins. A reifier alone never grants access.

This is one local branch in `ResourceInstance.search.append_access_patterns`,
shared by count and result queries. Ordinary date comparisons, subproperties,
class hierarchy, sorting, paging and returned values retain their semantics.
No cache, index, storage migration, public API or library signature changes.
GraphDB keeps its existing query. Harvesters and oldap-tools require no change.

Text and mandatory IRI-relationship searches keep their existing direct grant
lookup. Relationship candidate detection is shared with ACL planning to avoid
two diverging eligibility rules. This distinction is important: extracting all
grants after an already bound candidate set regressed the 1000-child fixture
past its 10-second timeout. Preserving its existing plan restores passing growth
checks. Merely grouping the former ACL was also measured and rejected because
it produced little improvement.

## Same-target measurements

The profiler compares the previous root ACL with the runtime plan on the same
owned Fasnacht export target. Every complete JSON response (including ordering,
values and counts) must agree across two repetitions of each of six cases.
Generated queries remain in private probe output. HTTP times below include
structured dating hydration, not browser rendering or media delivery.

| Request | Previous median ms | Optimized median ms |
| --- | ---: | ---: |
| media | 1857 | 234 |
| objects | 2841 | 1626 |
| sources | 1182 | 161 |
| dating | 1875 | 829 |
| dating_count | 1257 | 202 |
| dating_text | 189 | 179 |

Media returns 665 resources, objects 437, sources 422, dating 13, and dating
with title text two. The date interval is 1910–1911. `dating` includes descending
date sorting; `dating_count` exercises the same predicate without projection.
`dating_text` intentionally uses the unchanged selective text plan; its small
timing difference is ordinary measurement variation.

These are local indicative measurements with uncontrolled host load, not
production concurrency or capacity guarantees. Native acceptance ran separately
on an owned process during part of this interval. See the
[retained samples and acceptance](jena-metadata-performance-results.json).

## Validation

- 207 native checks pass, including the 1000-child growth suite, permissions,
  revocation, rollback, subclass/subproperty behavior, paging and multivalues.
- Six additional dating cases verify inclusive overlap boundaries, strict
  before/after and equality/inequality, each checking results and counts.
- An additional adversarial grant test rejects wrong predicates, non-triple
  reification values and unheld roles; malformed grants cannot expose resources.
- 30 fulltext and 23 real-export API checks pass on the normal runtime adapter.
- 36 offline entailment/connection and four dating serialization tests pass.
- All 24 comparative HTTP responses match. Source export SHA-256 is unchanged;
  all owned probe processes have stopped. No shared services were changed.

## Reproduce and remaining work

Run `tools/migration/profile_archive_metadata.py` with the ordinary
`probe_api_jena.py` options: `--java`, `--jar`, a fresh `--output`,
`--fasnacht-only`, `--fasnacht-export`, `--browser-preview`, `--fulltext-preview`.
Stop its owned preview by creating `browser-stop` in that output directory.
The baseline wrapper reconstructs only the former root ACL and fails when its
expected plan marker changes. It is fixed to these Fasnacht measurement cases,
not a production query rewriting facility.

Run `oldaplib/tools/migration/probe_model_reads.py` with `--relationship-growth`
for native validation. Its output is also private and disposable.

Follow-up: [local namespace resolution](jena-dating-hydration.md) reduces hydration
to about 0.76 s without changing queries. The following finding describes the
pre-follow-up measurement.

Structured date hydration remains significant for the full 437-object list
(about one second), while main search/projection takes about half a second.
This is the next measurable optimization target; the 13-result date query needs
only about 0.10–0.15 seconds for hydration. Keep bounded batch hydration and its
permission behavior when optimizing. Production load, the deferred GraphDB
comparison, and browser end-to-end timing remain separate acceptance work.
