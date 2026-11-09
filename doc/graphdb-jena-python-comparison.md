# GraphDB/Jena comparison after Python and summary-payload optimizations

## Method

Two repeats of the existing real Fasnacht workload: six public ArchiveObject
page/count cases, 100-row pages, title ordering, structured dates, and alternating
backend waves with 1/4/8 synchronized readers. Both backends are measured anew.
Each Jena target uses 8192 MiB heap and a fresh owned API/Redis/dataset. No profiler
or overlapping test workload runs during timing. Existing GraphDB/API are not
changed; this remains an unequal-deployment application comparison, not an
engine-only benchmark or production capacity test.

The source is the same immutable asserted export as the
[previous comparison](graphdb-jena-precheck-comparison.md). The current Jena
checkout includes datatype schema reuse, trusted read handling, scoped model
reconstruction and the smaller summary CONSTRUCT graph.

## Mixed-workload medians

All values are milliseconds. Both complete runs are retained so that transient
GraphDB tails in run 1 cannot create a misleading Jena speed claim.

| Readers | GraphDB run 1 | Jena run 1 | GraphDB run 2 | Jena run 2 | Jena/GraphDB, run 2 | Previous Jena |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 56 | 73 | 57 | 73 | 1.28 | 118 |
| 4 | 142 | 137 | 117 | 139 | 1.19 | 270 |
| 8 | 199 | 256 | 203 | 250 | 1.23 | 488 |

Jena medians are stable across the repeats. Compared with the previous separate
run they are approximately 38%, 49% and 49% lower (run 2); host/JIT variation
means these percentages must not be attributed exactly to individual changes.
The preceding same-target ABBA studies provide the stronger causal evidence.
GraphDB remains ahead in run 2, but the mixed-median gap is now roughly 19–28%,
compared with factors 2.05–2.46 in the previous comparison.

| Readers | GraphDB p95 run 1 / run 2 | Jena p95 run 1 / run 2 | GraphDB requests/s run 2 | Jena requests/s run 2 |
|---:|---:|---:|---:|---:|
| 1 | 152 / 148 | 279 / 282 | 15.32 | 9.52 |
| 4 | 713 / 238 | 308 / 313 | 15.63 | 15.64 |
| 8 | 907 / 408 | 500 / 496 | 19.15 | 17.55 |

GraphDB's slow tail in run 1 did not recur; its cause was not instrumented.
Do not claim Jena has a better tail from that single run. Throughput is bounded
wave throughput, including client startup, not sustained server capacity.

## Serial search cases

Run 2, two samples per case/backend; these numbers indicate remaining hotspots,
not precise individual-case ratios.

| Case | GraphDB median | Jena median |
|---|---:|---:|
| Metadata | 80 | 87 |
| Count | 33 | 61 |
| Dating | 148 | 262 |
| Dating count | 38 | 115 |
| Fulltext | 71 | 62 |
| Fulltext count | 21 | 43 |

Metadata/fulltext pages are close; GraphDB still has a substantial advantage in
counts and dated searches. The mixed median must not hide those slower cases.
The next comparison should keep those cases separate when assessing priorities.

## Correctness and reproducibility

All six cases agree in both runs: IDs, row order, metadata, structured dates and
counts. Only engine-specific relevance scores are excluded from cross-backend
comparison on the explicitly title-sorted fulltext page. Every backend's timed
responses remain stable including its own scores. All 624 timed requests return
HTTP 200 (312 per backend across both runs). Each run also performs untimed
semantic comparisons and warm-up requests.

Source export SHA-256 remains
237fcf17a601db3ff25a784d9166bbfe6f94003069025ab0bd0f81978ead80d6.
Owned test services stopped; source data, original GraphDB checkout/deployment
and runtime code are unchanged by this measurement step.
[Complete aggregate evidence](graphdb-jena-python-comparison-results.json).

Reproduce with tools/migration/probe_backend_comparison.py, --java-heap-mb 8192,
--fasnacht-only, --browser-preview, --fulltext-preview and the same
--fasnacht-export snapshot, using a new private --output directory. This run's
private directories are backend-comparison-payload-01 and -02. No new benchmark
implementation was introduced. Larger paired datasets, authenticated role mixes,
writes/soak and equal-deployment measurements remain separate work.


## Story overview comparison — 2026-11-02

The public `/geschichten` page was traced in FasnachtsPage source. Its initial
unfiltered workflow starts story search and StoryKeywords retrieval concurrently,
then resolves distinct lead-image references through summaries in batches of 100.
Text can render before lead-image metadata arrives. The probe reproduces this API
dependency chain; it does not execute a browser or download image bytes.

The exact search uses `fasnacht:Story`, `isPublished == true`, descending story
date, limit 1000 and the seven properties used by the page. Summaries request
publication status, asset ID, server URL, protocol and media URL with
`includeMediaDelivery=false`. Both backends return 28 stories and 28 distinct
lead-image references, requiring one summary request per overview.

Twenty alternating, warmed workflows per backend produce 120 successful timed
HTTP requests. Medians in milliseconds:

| Measurement | GraphDB | Jena/Fuseki |
| --- | ---: | ---: |
| Story search | 56.8 | 86.1 |
| Rubric list (overlaps search) | 53.2 | 11.1 |
| Lead-image summaries (after search) | 77.4 | 69.8 |
| Text metadata ready | 57.0 | 86.3 |
| All overview metadata ready | 134.2 | 157.5 |

The complete API workflow is about 17% slower on Jena, an absolute difference
of 23 ms. Story search is the slower Jena step; rubric and summary reads do not
explain its extra latency. These are application-level observations, not an
engine-only attribution. Parallel step medians must not simply be added.

All story fields and ordering, and all summary response fields, agree. Rubric
content (including node identities, labels and hierarchy) agrees after excluding
only creator/contributor/created/modified: the owned target recreates taxonomies
through YAML import. Two preliminary runs stopped at this provenance mismatch;
no timings from them are used above. Each backend's complete response, including
its own provenance, stays stable throughout warm-up and all measured repetitions.
Source export SHA-256 before/after equals the existing baseline. The owned target
uses 8192 MiB Java heap and its isolated API/Redis; existing GraphDB/API remain
untouched. Owned services stop on completion.

This is an already-authenticated public-reader, warm-cache API comparison on the
current small real export. It excludes login, JS/CSS loading, rendering, viewport
image capabilities, image delivery and cold starts. The first observed request
in the JSON is not a controlled cold-cache measurement. Existing GraphDB and
owned Jena deployment topologies differ. It does not establish whole-browser
page-load time or production capacity; no runtime optimization was made.

Reproduce using `tools/migration/probe_story_overview.py` with the existing
preview runner flags: `--fasnacht-only --browser-preview --fulltext-preview`,
`--java-heap-mb 8192`, Java/Fuseki jar paths, an unchanged `--fasnacht-export`
and a fresh private `--output`. The fulltext hook is reused to run the workload;
this unfiltered test does not configure or exercise fulltext. Private successful
run: `stories-comparison-03`; export: `stories-source-01/source.trig`.
[Aggregate evidence](graphdb-jena-story-overview-results.json).
