"""Compare fulltext query plans on the disposable Fasnacht API rehearsal.

Accepts the same arguments as probe_api_jena.py; requires --fulltext-preview.
Only this owned process is instrumented. No source data or shared service changes.
"""
import json
from pathlib import Path
import runpy
import statistics
import threading
import time
from unittest.mock import patch


def profile(call, output, public):
    """Compare identical HTTP requests and responses while changing join placement.

    Args:
        call: Owned rehearsal HTTP client with status assertions.
        output: Private run directory for query plans and aggregate timings.
        public: Headers for the disposable public identity.

    Raises:
        AssertionError: Any plan changes response values, scores, or ordering.

    Side effects:
        Temporarily patches query generation only in this owned API process;
        restores methods on exit and writes results after successful comparison.
    """
    from oldaplib.src import objectfactory
    from oldaplib.src.jena_connection import JenaConnection
    original_pattern = JenaConnection._resource_fulltext_pattern
    original_query = objectfactory.resource_query
    local = threading.local()
    mode = 'baseline'
    samples = []

    def pattern(self, *args, **kwargs):
        local.pattern = original_pattern(self, *args, **kwargs)
        return local.pattern

    def query(con, sparql, *args, **kwargs):
        fulltext = getattr(local, 'pattern', None)
        if fulltext and fulltext in sparql:
            sparql = sparql.replace(fulltext, '', 1)
            candidates = fulltext
            if mode == 'grouped':
                candidates = ('{ SELECT ?res (MAX(?candidate_score) AS ?score_raw) WHERE { '
                    + fulltext.replace('?score_raw', '?candidate_score') + ' } GROUP BY ?res }')
            if mode == 'baseline':
                # These fixed cases have no property/list filters: immediately
                # after root grants reproduces the original late text placement,
                # even when the checked-out builder already uses the early plan.
                position = sparql.index('}', sparql.index('?searchGrant')) + 1
            else:
                # Preserve the independent class-set lookup before any bindings.
                position = sparql.index('GRAPH oldap:admin {')
            sparql = sparql[:position] + candidates + '\n' + sparql[position:]
            (output / f'fulltext-plan-{mode}.rq').write_text(sparql)
            return original_query(con, sparql, *args, **kwargs)
        return original_query(con, sparql, *args, **kwargs)

    cases = [
        ('title', None, [{'field': 'archiveObjectTitle', 'query': 'Laterne'}], {}),
        ('title_count', None, [{'field': 'archiveObjectTitle', 'query': 'Laterne'}], {'countOnly': True}),
        ('media_words', 'fasnacht:ArchiveMediaObject', [{'field': 'archiveMediaObjectTitle', 'query': 'Laterne Stamm'}], {}),
        ('linked_words', 'fasnacht:ArchiveMediaObject', [{'field': 'representedArchiveObjectTitle', 'query': 'Laterne Stamm'}], {}),
        ('pdf', None, [{'field': 'archiveMediaObjectText', 'query': 'Stadtbuch'}], {}),
        ('field_union', 'fasnacht:ArchiveMediaObject', [{'field': 'archiveMediaObjectTitle', 'query': 'Laterne Stamm'}, 'OR', {'field': 'representedArchiveObjectTitle', 'query': 'Laterne Stamm'}], {}),
    ]
    expected = {}
    with patch.object(JenaConnection, '_resource_fulltext_pattern', pattern), patch.object(objectfactory, 'resource_query', query):
        for mode in ('baseline', 'early', 'grouped'):
            for name, cls, filters, options in cases:
                times = []
                for repeat in range(3):
                    started = time.perf_counter()
                    response = call('POST', '/data/search/fasnacht' + ('/class/' + cls if cls else ''),
                        {'ftfilter': filters, 'includeProperties': ['schema:name'], 'limit': 5000, **options}, headers=public).json()
                    times.append(round((time.perf_counter() - started) * 1000, 2))
                    if mode == 'baseline' and repeat == 0:
                        expected[name] = response
                    if response != expected[name]:
                        raise AssertionError(f'Fulltext plan changed response: {mode}/{name}')
                samples.append({'mode': mode, 'case': name, 'milliseconds': times, 'median_ms': statistics.median(times)})
                print('PROFILE_FULLTEXT', mode, name, statistics.median(times), flush=True)
    (output / 'fulltext-performance.json').write_text(json.dumps({'responses_equal': True, 'samples': samples}, indent=2) + '\n')


if __name__ == '__main__':
    import sys
    if '--fulltext-preview' not in sys.argv and '--help' not in sys.argv:
        raise SystemExit('Profiling requires --fulltext-preview and its normal rehearsal arguments.')
    import check_fasnacht_fulltext
    original = check_fasnacht_fulltext.check_fasnacht_fulltext

    def checked(call, con, base, output, public, audit):
        original(call, con, base, output, public, audit)
        profile(call, output, public)

    check_fasnacht_fulltext.check_fasnacht_fulltext = checked
    runpy.run_path(str(Path(__file__).with_name('probe_api_jena.py')), run_name='__main__')
