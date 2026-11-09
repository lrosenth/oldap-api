# Search dating reader integration and calendar decoding

Local branch: `experiment/dating-read-performance` in oldap-api and oldaplib. No deployment, package publication or Git push. Both repositories must be released together: the API now uses a new private library method; existing released oldaplib 1.0.0 does not contain it. Public method signatures and HTTP shapes are unchanged.

## Focused reader

`_expand_search_dating` calls `ResourceInstanceFactory._read_search_dating` for model-resolved date properties. Both this method and public `read_summaries` share bounded input handling, class selection and decoding in `_read_summaries`. Only Jena's date projection uses the focused CONSTRUCT. GraphDB keeps the established general summary query; a live GraphDB comparison was not run.

The production code uses no monkeypatch or mutable global switch. The owned comparison runner temporarily restores the general summary reader for baseline requests, sequentially, while candidate requests exercise the integrated code normally. General summaries continue to include role metadata for authorization/delivery consumers. Search-date results must not be used for that purpose.

The focused query preserves reader/creator ACLs, explicit and ancestor types, modeled property expansion and existing before-chain behavior. Native fixture checks include a narrow subproperty and explicitly asserted ancestor/concrete types. Existing hydration semantics for derived properties remain unchanged; this change does not add recursive linked-resource authorization or general reasoning.

## Independent calendar correction

RDF stores `normalizedStart` and `normalizedEnd` in the Gregorian calendar, with the source calendar and precision separately. Previously `_dating_from_construct` passed those dates through the public string constructor, which defaults strings to Gregorian. This lost calendar metadata and could reject valid normalized Julian decade/century ranges.

The private `Dating._from_storage` restores already validated stored values directly: normalized endpoints remain byte-equivalent dates, display tuples are converted back to the declared calendar and reduced to the stored precision. It retains IRI, verbatim text and before references. Input validation and write behavior stay unchanged. No RDF migration or reification change is required. Structured calendar fields and the calendar name in legacy string output are intentionally corrected for affected data.

Tests cover RDF round trips for day precision in all five supported calendars and month/year/decade/century precision in Gregorian and Julian calendars. These checks do not constitute exhaustive validation of other calendars' coarse-precision write behavior. The previously expected failures now pass normally.

## Verification

- Dating, API serialization/batching and detail fast path: 30 passed.
- Broader existing construct/model/query checks: 13 passed, four reported failures (including subtest reporting) reproduce identically with the original HEAD implementation. They concern existing query string expectations, not this integration. Test logs are retained privately.
- Native run `dating-read-integrated-02`: 24 complete HTTP comparisons, native ACL/date/subproperty/multiple-type fixture group, and all 16 timed response comparisons passed. Julian display metadata is explicitly asserted correct.
- Compilation and whitespace checks pass. An initial runner-only naming collision (baseline callable overwritten by fixture mapping) was corrected before the successful run; runtime code was unaffected.

Historical query-only experiment: [dating-read-experiment.md](dating-read-experiment.md). Its original numbers deliberately remain unchanged; the integration run includes the calendar decoder improvement in both baseline and candidate.

## Integrated measurement

| Search request | Baseline median | Integrated median | Reduction |
| --- | ---: | ---: | ---: |
| Public (437 rows) | 550.6 ms | 413.7 ms | 24.9% |
| Audit (442 rows) | 1102.2 ms | 787.9 ms | 28.5% |

Both variants use the corrected calendar decoder. Each has four measured requests after warmup, in alternating ABBA order. Fifteen backend calls remain per request. Warm local results are not complete-page or production timings, nor a concurrency test. See [sanitized results](dating-read-integration-results.json).

Next release gate: build library and API artifacts together, perform installed-image acceptance, then measure the deployed test environment before production rollout. Existing published 1.0.0 artifacts and production remain untouched. No harvester or oldap-tools public signature migration is necessary.
