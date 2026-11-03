# Search pages of 100 resources

## Contract and implementation

`ResourceInstance.search` already defaults to `limit=100, offset=0`. The API
passes explicitly supplied limits/offsets through; public signatures and response
formats are unchanged. No global maximum of 100 is introduced: existing callers
can still explicitly request larger pages.

Selection, permission checks, filtering and ordering run before the resource
page is selected. Property projection and structured-date hydration then run on
that page. The resource IRI breaks sorting ties. This avoids splitting a resource
with multiple property values across pages. `countOnly=true` returns the complete
distinct matching count regardless of limit and offset.

Counts now omit the optional sort-value joins. Sorting cannot change a distinct
resource count, but resolving ordinary or structured-date sort keys previously
added work. Filters and permission checks are retained. This small common query
builder change also applies to GraphDB; its live countertest remains deferred.
There is no result/permission cache and no new query-planning abstraction.

## Fulltext completeness correction

The first run (`search-pagination-01`) exposed a missing fulltext page at offset
5000, despite successful metadata/date pages. Omitting the index limit silently
uses Jena Text's 10000-document window; denied hits consume that window too.
The former growth test checked only the first fulltext page, and its complete
traversal covered metadata, so it did not establish deep fulltext completeness.

Every generated Jena text lookup now explicitly requests Java's maximum positive
integer (`2147483647`). This covers the Lucene document domain, rather than
replacing 10000 with another arbitrary application cap. The installed Lucene
IndexSearcher bounds its collector by the actual index document count. The
collector can scale with index size and matching candidates are materialized;
production-size memory/load measurement remains necessary. This fix is
correctness, not a claim of streaming or constant-space text search.
Resource-level filtering, permissions and LIMIT/OFFSET remain authoritative.
No index rebuild, model update, public signature or GraphDB text-query change.

Verified against the installed 6.2.0 jar and the upstream
[Jena TextIndexLucene source](https://raw.githubusercontent.com/apache/jena/jena-6.2.0/jena-text/src/main/java/org/apache/jena/query/text/TextIndexLucene.java):
`MAX_N=10000`, and nonpositive limits use it too. Thus `-1` is not a fix.
The final fixture includes a same-target control that removes the explicit limit
only inside its test query hook and reproduces the incomplete count.

## Acceptance and measurements

`tools/migration/probe_search_pagination.py` reuses the load fixture's resource
seeding on an owned real-export Jena/API/Redis stack. It adds 12000 synthetic
objects with tied titles, duplicate grants, internal objects, restricted grants
and orphan reifiers. Dates have explicit readable grants. Expected IDs and totals
are computed independently in Python.

For public and audit identities, metadata, date-filtered structured results and
fulltext results are compared at limits 100, 1000 and 5000, twice in opposite
size order. The complete first 100 response objects must agree across sizes.
Boundary checks cover the next page, offset 5000, the last page and the empty
page after the end. Counts with title/date sorts must ignore pagination and omit
sort joins. Removing one asserted role link must refill the first 100-row page
without returning the revoked object. This is a sequential page-size experiment,
not another concurrency or complete-traversal run.

Reproduce with the same `--java`, `--jar`, fresh `--output`, `--fasnacht-only`,
`--fasnacht-export`, `--browser-preview`, `--fulltext-preview` arguments as the
[load rehearsal](jena-search-load.md). The wrapper stops its preview automatically
on success/failure. Its aggregate report contains timings and assertions, not
credentials or response bodies.

The corrected `search-pagination-02` passes **214 assertions across 76 HTTP
requests**, plus the ordinary fixture's 30 fulltext and 23 export/API checks.
The native model/search fixture passes 189 checks, including missing and
multivalued sort keys in counts. 83 offline regressions pass (42 entailment,
connection, construct/date tests plus 41 fulltext configuration tests).

Median HTTP times (two samples each, local sequential workload):

| Identity / request | LIMIT 100 | LIMIT 1000 | LIMIT 5000 |
| --- | ---: | ---: | ---: |
| public / metadata | 2.97 s | 2.98 s | 3.11 s |
| public / dating | 5.25 s | 6.30 s | 8.83 s |
| public / fulltext | 3.23 s | 3.24 s | 3.38 s |
| audit / metadata | 3.95 s | 3.98 s | 4.07 s |
| audit / dating | 7.20 s | 8.63 s | 14.29 s |
| audit / fulltext | 4.82 s | 4.87 s | 5.01 s |

The date-filtered totals are 3000 public / 4500 audit, so LIMIT 5000 returns that
many actual records, not 5000. Unfiltered/fulltext totals are 6000 / 9000.
The same-target legacy text controls return only 5000 / 7500; corrected counts
return 6000 / 9000 and late 100-row pages agree with independent expectations.

For the public metadata request, response size falls from 765003 to 15303 bytes.
For public structured dating it falls from 1221003 to 40703 bytes. At LIMIT 100,
the date-filtered root query still takes roughly 5 seconds; the date-expansion
phase is about 0.2 seconds, versus about 3.7 seconds for the larger result.
This identifies work before pagination as the remaining dominant cost. These
samples do not establish a meaningful speedup for ordinary metadata/text pages,
or independently quantify the count-join optimization against its former code.

[Aggregate samples and assertions](jena-search-pagination-results.json) retain
query/hydration times, response sizes and actual result counts. The source export
SHA-256 is unchanged; owned API/Jena/Redis processes are stopped. The first failed
run remains in the private probe directory as diagnostic evidence.


## Scope and next optimization

The frontend is intentionally unchanged. Its grouping of media and propagation
of linked fulltext hits occur after several searches. Replacing its 5000 limits
with 100 would silently lose matches, change grouped counts and sort partial
results. Correct frontend pagination needs the page boundary after those domain
operations, with matching totals; that is a separate step.

A smaller page bounds projection, hydration and transfer costs. It does not
eliminate scanning/filtering/sorting all eligible candidates. Large OFFSET values
also require selecting/skipping earlier matches. Profile these candidate and
property/date joins separately before adding more query complexity. No production
capacity claim follows from this local 512 MiB Java/development-API fixture.

Between requests, writes or changed permissions can shift offset boundaries.
Stable tie ordering does not provide a multi-request snapshot. Totals can be
reused while navigating an unchanged search for presentation, but should be
refreshed on a new search/identity change; every page must authorize current reads.

Follow-up: [schema-first candidate joins](jena-search-candidates.md) compare the
same 100-row results with a simpler join order and substantially reduce the
root-query cost measured above. These page-size timings remain historical.
