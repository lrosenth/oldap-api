# Resolve schema relationships before instance joins

## Change

The shared Jena `property_pattern` now resolves inverse-field definitions,
legacy inverse-property axioms and subproperty paths before joining instance
data. The same triple patterns, graph scopes and protective filters remain.
No inference rule, access check, public signature or GraphDB query changes.

Previously the inverse/subproperty UNION branches could start with instance
links or types, then check whether a corresponding schema rule existed. Even
when no rule matched, that order made broad candidate filtering and sorting
expensive. Starting with the small schema side lets an absent rule stop its
branch without visiting instance links for each candidate. This is a uniform
query-order change, not a schema cache or special handling of particular fields.

The helper is shared by search, resource reads and summaries. Its existing
asserted-only protection remains first; modeled inverse overrides, project/shared
schema scope and protected-property exclusions are unchanged.

## Reproduction and acceptance

The existing `tools/migration/probe_search_pagination.py` accepts an optional
`--baseline-entailment PATH` pointing to a trusted pre-edit copy of
`jena_entailment.py`. The snapshot executes as Python; never supply untrusted
code. It compares the two `property_pattern` implementations within the same
owned API process/dataset, preserving current fulltext and count corrections.
Use the normal Java/jar/output/real-export/browser-preview/fulltext-preview flags
from the [paging rehearsal](jena-search-pagination.md).

This comparison selects 100 rows in baseline/optimized/optimized/baseline order
for each of three request shapes and two identities. Entire response objects
must agree, as must independently computed resource IDs. Root query and dating
expansion times are captured separately; generated query plans stay in the
private output directory. Deep-page boundaries, current counts, the legacy text
cutoff control and post-revocation reads remain checked with the new plan.

The 12000 synthetic objects include public/internal/restricted/orphaned grants,
duplicate grants, tied titles and shared readable dates. The native model/search
probe additionally exercises existing inverse/subproperty rules and 1000 linked
children; those cases must not regress while optimizing rule-free branches.

The owned `search-candidates-01` run passes **198 assertions across
64 HTTP requests**, including 24 complete baseline/optimized response
comparisons, independent page/count expectations and post-revocation page refill.
Normal real-export checks also pass (30 fulltext and 23 API checks). The native
relationship-growth/model suite passes 208 checks; 24 focused entailment/construct
tests pass. No signature or data-format changes.

Median HTTP times (two samples per plan/shape):

| Identity / 100-row request | Former order | Schema first |
| --- | ---: | ---: |
| public / metadata | 3.31 s | 0.53 s |
| public / dating | 5.59 s | 1.27 s |
| public / fulltext | 3.34 s | 0.77 s |
| audit / metadata | 4.23 s | 1.66 s |
| audit / dating | 7.50 s | 2.62 s |
| audit / fulltext | 4.99 s | 2.42 s |

For public date pages, the root query falls from about 5.38 to 1.06 seconds;
whole HTTP response time falls from 5.59 to 1.27 seconds. Thus the gain is in
candidate matching/sorting, not a smaller page or omitted date hydration.
The 100-row response, filters, explicit full-index text candidate limit and
permission checks are the same in both plans.

[Aggregate evidence](jena-search-candidates-results.json) includes root/construct
query timings, date expansion, bytes, actual counts and helper snapshot hashes.
The source TriG SHA-256 remains
`237fcf17a601db3ff25a784d9166bbfe6f94003069025ab0bd0f81978ead80d6`.
All owned processes have stopped. No shared service restart or deployment.


## Limits and next steps

Two samples per plan/shape on a local 512 MiB Java and development API are not
production capacity measurements. Counts/boundaries run on the new plan only;
this experiment does not quantify their baseline speedup. No concurrent writer
runs during the comparison. The source export and shared services are untouched.

Fulltext still materializes its candidate hits, and its full-index collector can
scale with index size. Larger production memory/concurrency tests remain open.
The frontend's grouping/pagination and GraphDB countertest are separate work.
Keep permission checks before resource paging; do not trade completeness for an
index-side top-N limit. No index rebuild or data migration is required here.

Follow-up: [concurrent readers](jena-search-load-optimized.md) verifies these
changes with 100-row pages at 1/4/8 simultaneous requests and current permissions.
