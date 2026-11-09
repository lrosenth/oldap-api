"""Measure 100-row API pages on an owned 12000-resource Jena dataset.

Uses probe_api_jena.py arguments with --browser-preview --fulltext-preview.
Reuses the growth fixture, not a production connection. Reports aggregate
latencies/query timings only; credentials and response bodies stay out of reports.
Optional --baseline-entailment PATH compares a trusted pre-edit helper snapshot
in ABBA order at 100 rows, with whole-response parity and private query plans.
"""
import json
from pathlib import Path
import runpy
import time
from unittest.mock import patch

import requests

from probe_search_load import seed_load_resources


def exercise(con, base, output, public, audit, baseline_pattern=None):
    """Verify page boundaries, full projections, counts and current permissions.

    Compare 100/1000/5000-row requests with identical filters and order. Independent
    Python expectations include denied resources and title ties. Timing hooks run
    only around sequential requests on this owned in-process HTTP fixture.
    """
    from oldap_api.views import instance_views
    from oldaplib.src import objectfactory
    from oldaplib.src.helpers.context import Context
    from oldaplib.src.xsd.dating import Dating

    original_pattern = objectfactory.property_pattern
    plan = 'optimized'
    size = 12000
    prefix = Context(name=con.context_name).sparql_context
    report = {'status': 'running', 'size': size, 'page_size': 100, 'checks': [], 'samples': []}
    current = {}
    original_query = objectfactory.resource_query
    original_expand = instance_views._expand_search_dating
    marker = {'property': 'schema:identifier', 'op': '==', 'type': 'string', 'value': 'oldaploadprobe'}
    dates = {'property': 'fasnacht:dating', 'op': 'overlaps', 'type': 'dating',
             'value': {'dateStart': '1900-01-01', 'dateEnd': '1949-12-31'}}
    common = {'filter': [marker], 'sortBy': ['schema:name|asc'], 'includeProperties': ['schema:name']}
    cases = {
        'metadata': common,
        'dating': {**common, 'filter': [marker, 'AND', dates], 'includeProperties': ['schema:name', 'fasnacht:dating']},
        'fulltext': {**common, 'ftfilter': [{'field': 'archiveObjectTitle', 'query': 'oldaploadprobe'}]},
    }

    def save():
        (output / 'search-pagination-results.json').write_text(json.dumps(report, indent=2) + '\n')

    def check(label, condition):
        if not condition:
            raise AssertionError(label)
        report['checks'].append(label)
        print('PASS PAGINATION', label, flush=True)

    def query(connection, sparql, *args, **kwargs):
        started = time.perf_counter()
        try:
            if baseline_pattern and ('SELECT DISTINCT ?res ?resclass' in sparql or 'COUNT(DISTINCT ?res)' in sparql):
                (output / f"candidates-{plan}-{current['identity']}-{current['case']}-{current['phase']}.rq").write_text(sparql)
            if 'COUNT(DISTINCT ?res)' in sparql:
                check('Count query omits sort-value joins', '?sort_' not in sparql)
            if current.get('phase') == 'legacy-window':
                # Reproduce the former omitted-limit behavior on this same
                # target; never enable this diagnostic in application code.
                assert ' 2147483647)' in sparql
                sparql = sparql.replace(' 2147483647)', ')')
            return original_query(connection, sparql, *args, **kwargs)
        finally:
            kind = 'construct_ms' if 'CONSTRUCT' in sparql else 'query_ms'
            current.setdefault(kind, []).append(round((time.perf_counter() - started) * 1000, 2))

    def expand(*args, **kwargs):
        started = time.perf_counter()
        try:
            return original_expand(*args, **kwargs)
        finally:
            current['dating_ms'] = round((time.perf_counter() - started) * 1000, 2)

    def request(identity, case, body, phase):
        nonlocal current
        current = {'identity': identity, 'case': case, 'phase': phase,
                   'limit': body.get('limit'), 'offset': body.get('offset', 0), 'plan': plan}
        started = time.perf_counter()
        implementation = baseline_pattern if plan == 'baseline' else original_pattern
        with patch.object(objectfactory, 'property_pattern', implementation), requests.Session() as session:
            response = session.post(base + '/data/search/fasnacht/class/fasnacht:ArchiveObject',
                json=body, headers={**{'public': public, 'audit': audit}[identity],
                                    'Accept': 'application/json; dating=structured'}, timeout=90)
        current.update(ms=round((time.perf_counter() - started) * 1000, 2),
                       bytes=len(response.content), http_status=response.status_code)
        report['samples'].append(current)
        check(f'{identity}/{case}/{phase}/{body.get("limit")}/{body.get("offset", 0)} HTTP 200', response.status_code == 200)
        rows = response.json()
        current['returned_count'] = rows.get('count') if isinstance(rows, dict) else len(rows)
        return rows

    def expected(identity, case):
        return [f'urn:oldap-load:item:{i:05d}' for i in range(size)
                if i % 8 < (4 if identity == 'public' else 6)
                and (case != 'dating' or i % 100 < 50)]

    try:
        # Unlike the original load-only fixture, dates are readable too: exercise
        # actual structured date projection, not only reference removal.
        triples = []
        for year in range(1900, 2000):
            iri = f'<urn:oldap-load:date:{year}>'
            triples.append(f'{iri} a oldap:Dating ; {Dating((year,)).toRdf} ; oldap:attachedToRole oldap:Unknown .')
            triples.append(f'<urn:oldap-load:date-grant:{year}> rdf:reifies <<( {iri} oldap:attachedToRole oldap:Unknown )>> ; oldap:hasDataPermission oldap:DATA_VIEW .')
        con.update_query(prefix + 'INSERT DATA { GRAPH fasnacht:data { ' + '\n'.join(triples) + ' } }')
        seed_load_resources(con, 0, size)
        with patch.object(objectfactory, 'resource_query', query), patch.object(instance_views, '_expand_search_dating', expand):
            for identity in ('public', 'audit'):
                legacy = request(identity, 'fulltext', {**cases['fulltext'], 'countOnly': True}, 'legacy-window')
                check(f'{identity}: omitted Jena text limit reproduces incomplete count',
                      legacy['count'] < len(expected(identity, 'fulltext')))
                for case, body in cases.items():
                    wanted = expected(identity, case)
                    first_page = None
                    references = {}
                    # Optional trusted snapshot comparison isolates query planning
                    # on the same dataset. ABBA order reduces warm-up/order bias;
                    # 100 rows focus the comparison on work before hydration.
                    rounds = ([(mode, (100,)) for mode in ('baseline', 'optimized', 'optimized', 'baseline')]
                              if baseline_pattern else [('optimized', (100, 1000, 5000)), ('optimized', (5000, 1000, 100))])
                    for plan, limits in rounds:
                        for limit in limits:
                            rows = request(identity, case, {**body, 'limit': limit}, 'page-size')
                            check(f'{identity}/{case}/{limit}: exact sorted resource IDs',
                                  [row['iri'] for row in rows] == wanted[:limit])
                            if first_page is None:
                                first_page = rows
                            if limit not in references:
                                references[limit] = rows
                            check(f'{identity}/{case}/{limit}/{plan}: full response parity', rows == references[limit])
                            check(f'{identity}/{case}/{limit}: full first-page response parity', rows[:100] == first_page)
                            if case == 'dating':
                                check(f'{identity}/dating/{limit}: structured dates remain readable',
                                      all(row.get('fasnacht:dating') and isinstance(row['fasnacht:dating'][0], dict) for row in rows))
                            save()
                    plan = 'optimized'
                    for offset in sorted({100, 5000, ((len(wanted) - 1) // 100) * 100, len(wanted)}):
                        rows = request(identity, case, {**body, 'limit': 100, 'offset': offset}, 'page-boundary')
                        check(f'{identity}/{case}/{offset}: correct 100-row boundary including empty end',
                              [row['iri'] for row in rows] == wanted[offset:offset + 100])
                    for sort in (body['sortBy'], [{'property': 'fasnacht:dating', 'kind': 'dating', 'direction': 'desc'}]):
                        counted = request(identity, case, {**body, 'sortBy': sort, 'countOnly': True, 'limit': 100, 'offset': 5000}, 'count')
                        check(f'{identity}/{case}: total independent of page and sort', counted == {'count': len(wanted)})
                    save()
            con.update_query(prefix + 'DELETE DATA { GRAPH fasnacht:data { <urn:oldap-load:item:00000> oldap:attachedToRole oldap:Unknown . } }')
            for identity in ('public', 'audit'):
                rows = request(identity, 'metadata', {**common, 'limit': 100}, 'revocation')
                check(f'{identity}: fresh first page excludes revoked assertion and refills to 100',
                      [row['iri'] for row in rows] == expected(identity, 'metadata')[1:101])
        report['status'] = 'passed'
    except Exception as error:
        report['status'] = 'failed'
        report['failure'] = {'type': type(error).__name__, 'message': str(error) if isinstance(error, AssertionError) else 'See owned process logs.'}
        raise
    finally:
        save()
        (output / 'browser-stop').touch()


if __name__ == '__main__':
    import sys
    baseline_pattern = None
    if '--baseline-entailment' in sys.argv:
        index = sys.argv.index('--baseline-entailment')
        snapshot = Path(sys.argv[index + 1]).resolve()
        del sys.argv[index:index + 2]
        # The snapshot is executable Python: only use a trusted local file saved
        # before the change. Never accept an uploaded/untrusted source here.
        baseline_pattern = runpy.run_path(str(snapshot))['property_pattern']
    if '--fulltext-preview' not in sys.argv and '--help' not in sys.argv:
        raise SystemExit('Requires the owned --browser-preview --fulltext-preview fixture.')
    import check_fasnacht_fulltext
    original = check_fasnacht_fulltext.check_fasnacht_fulltext

    def checked(call, con, base, output, public, audit):
        original(call, con, base, output, public, audit)
        exercise(con, base, output, public, audit, baseline_pattern)

    check_fasnacht_fulltext.check_fasnacht_fulltext = checked
    runpy.run_path(str(Path(__file__).with_name('probe_api_jena.py')), run_name='__main__')
