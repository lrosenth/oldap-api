"""Bounded growth/concurrent-reader rehearsal on the owned real-export API.

Run with probe_api_jena.py options including --browser-preview --fulltext-preview.
Only the disposable target receives synthetic data. Uses independent HTTP
sessions per request; never writes tokens or response contents to the report.
The preview is stopped automatically after the checks, including on failure.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import math
from pathlib import Path
import runpy
import statistics
from threading import Barrier
import time

import requests


def seed_load_resources(con, previous, size):
    """Append a synthetic growth stage to the caller-owned disposable dataset.

    The caller seeds date nodes separately. Titles deliberately tie; permissions
    include internal, orphaned, restricted and duplicate grants. A single commit
    per stage keeps the probe engine's completed-transaction budget bounded.
    """
    from oldaplib.src.helpers.context import Context
    prefix = Context(name=con.context_name).sparql_context
    # One transaction per stage avoids the probe's finite completed-ID
    # budget. Updates remain bounded; publication/indexing happens once.
    con.transaction_start()
    try:
        for start in range(previous, size, 100):
            triples = []
            for i in range(start, min(start + 100, size)):
                iri = f'<urn:oldap-load:item:{i:05d}>'
                role = 'oldap:WriterRecoveryOperator' if i % 8 in (4, 5) else 'oldap:Unknown'
                permission = 'DATA_RESTRICTED' if i % 8 == 7 else 'DATA_VIEW'
                triples.append(f'{iri} a fasnacht:ArchiveObject ; schema:name "oldaploadprobe Group {i // 4:05d}" ; '
                               f'schema:identifier "oldaploadprobe" ; fasnacht:dating <urn:oldap-load:date:{1900 + i % 100}> .')
                if i % 8 != 6:  # Orphan reifiers must not confer access.
                    triples.append(f'{iri} oldap:attachedToRole {role} .')
                triples.append(f'<urn:oldap-load:grant:{i}> rdf:reifies <<( {iri} oldap:attachedToRole {role} )>> ; oldap:hasDataPermission oldap:{permission} .')
                if i % 16 == 0:
                    triples.append(f'<urn:oldap-load:duplicate:{i}> rdf:reifies <<( {iri} oldap:attachedToRole {role} )>> ; oldap:hasDataPermission oldap:{permission} .')
            con.transaction_update(prefix + 'INSERT DATA { GRAPH fasnacht:data { ' + '\n'.join(triples) + ' } }')
        con.transaction_commit()
    except Exception:
        if con.in_transaction():
            con.transaction_abort()
        raise


def exercise(con, base, output, public, audit):
    """Seed three sizes, verify independent expected IDs, then overlap readers.

    All inserted subjects use urn:oldap-load:. The owning runner destroys the
    disposable dataset/processes; source files and shared services are untouched.
    A failed HTTP/semantic check is retained and stops further load escalation.
    """
    from oldaplib.src.helpers.context import Context
    from oldaplib.src.xsd.dating import Dating
    prefix = Context(name=con.context_name).sparql_context
    report = {'status': 'running', 'samples': [], 'checks': [], 'stages': [],
              'page_size': 100, 'readable_dates': True,
              'scope': 'Owned 512 MiB Java fixture, local threaded API, real Redis; bounded synthetic load, not production capacity.'}
    identities = {'public': public, 'audit': audit}
    marker = {'property': 'schema:identifier', 'op': '==', 'type': 'string', 'value': 'oldaploadprobe'}
    dates = {'property': 'fasnacht:dating', 'op': 'overlaps', 'type': 'dating',
             'value': {'dateStart': '1900-01-01', 'dateEnd': '1949-12-31'}}
    common = {'filter': [marker], 'sortBy': ['schema:name|asc'], 'includeProperties': ['schema:name'], 'limit': 100}
    cases = {
        'count': {**common, 'countOnly': True},
        'page': common,
        'date_count': {**common, 'filter': [marker, 'AND', dates], 'countOnly': True},
        'date_page': {**common, 'filter': [marker, 'AND', dates], 'includeProperties': ['schema:name', 'fasnacht:dating']},
        'text_page': {**common, 'ftfilter': [{'field': 'archiveObjectTitle', 'query': 'oldaploadprobe'}]},
    }

    def save():
        (output / 'search-load-results.json').write_text(json.dumps(report, indent=2) + '\n')

    def check(label, condition):
        if not condition:
            raise AssertionError(label)
        report['checks'].append(label)
        print('PASS LOAD', label, flush=True)

    def expected(size, identity, dated=False):
        return [f'urn:oldap-load:item:{i:05d}' for i in range(size)
                if i % 8 < (4 if identity == 'public' else 6) and (not dated or i % 100 < 50)]

    def request(size, identity, case, body, readers=1, barrier=None, phase="growth"):
        if barrier:
            barrier.wait(timeout=15)
        started = time.perf_counter()
        # A fresh session avoids sharing cookies/connection state across readers.
        with requests.Session() as session:
            response = session.post(base + '/data/search/fasnacht/class/fasnacht:ArchiveObject',
                json=body, headers={**identities[identity], 'Accept': 'application/json; dating=structured'}, timeout=30)
        elapsed = round((time.perf_counter() - started) * 1000, 2)
        sample = {'size': size, 'identity': identity, 'case': case, 'readers': readers,
                  'phase': phase, 'ms': elapsed, 'http_status': response.status_code, 'bytes': len(response.content)}
        if response.status_code != 200:
            return sample, None
        return sample, response.json()

    def validate(rows, size, identity, case, body):
        wanted = expected(size, identity, case.startswith('date'))
        if body.get('countOnly'):
            return isinstance(rows, dict) and rows.get('count') == len(wanted)
        offset = body.get('offset', 0)
        if not isinstance(rows, list) or [r['iri'] for r in rows] != wanted[offset:offset + body['limit']]:
            return False
        if case == 'date_page':
            # Validate real date hydration independently, not just a response
            # that silently omitted unreadable date references.
            for row in rows:
                value = row.get('fasnacht:dating')
                year = 1900 + int(row['iri'].rsplit(':', 1)[1]) % 100
                if not value or not isinstance(value[0], dict) or value[0].get('dateStart') != [year]:
                    return False
        return True

    try:
        date_triples = []
        for year in range(1900, 2000):
            iri = f'<urn:oldap-load:date:{year}>'
            date_triples.append(f'{iri} a oldap:Dating ; {Dating((year,)).toRdf} ; oldap:attachedToRole oldap:Unknown .')
            date_triples.append(f'<urn:oldap-load:date-grant:{year}> rdf:reifies <<( {iri} oldap:attachedToRole oldap:Unknown )>> ; oldap:hasDataPermission oldap:DATA_VIEW .')
        con.update_query(prefix + 'INSERT DATA { GRAPH fasnacht:data { ' + '\n'.join(date_triples) + ' } }')
        previous = 0
        for size in (1000, 4000, 12000):
            seed_load_resources(con, previous, size)
            previous = size
            report['stages'].append({'size': size, 'public': len(expected(size, 'public')), 'audit': len(expected(size, 'audit'))})
            for identity in identities:
                for name, body in cases.items():
                    sample, rows = request(size, identity, name, body)
                    report['samples'].append(sample)
                    check(f'{size}/{identity}/{name}: exact IDs/count and ordering', validate(rows, size, identity, name, body))
            save()

        # Traverse beyond the frontend's 5000-result window, independently of it.
        for identity in identities:
            seen = []
            for offset in range(0, len(expected(size, identity)) + 500, 500):
                body = {**common, 'limit': 500, 'offset': offset}
                sample, rows = request(size, identity, 'traversal', body)
                report['samples'].append(sample)
                check(f'{identity}/page {offset}: stable tied-title order', validate(rows, size, identity, 'page', body))
                seen.extend(row['iri'] for row in rows)
            check(f'{identity}: complete traversal without duplicates or denied records', seen == expected(size, identity))
        sample, rows = request(size, 'public', 'window5000', {**common, 'limit': 5000})
        report['samples'].append(sample)
        check('5000 window is explicitly incomplete versus 6000 total', validate(rows, size, 'public', 'page', {**common, 'limit': 5000}) and len(rows) == 5000)
        save()

        # A first text page alone cannot detect an early index-hit cutoff.
        # Require complete totals and a late page before starting reader waves.
        for identity in identities:
            body = {**cases['text_page'], 'countOnly': True}
            sample, rows = request(size, identity, 'text_count', body)
            report['samples'].append(sample)
            check(f'{identity}: fulltext total covers all authorized matches', validate(rows, size, identity, 'text_count', body))
            body = {**cases['text_page'], 'offset': len(expected(size, identity)) - 100}
            sample, rows = request(size, identity, 'text_tail', body)
            report['samples'].append(sample)
            check(f'{identity}: last fulltext page is complete', validate(rows, size, identity, 'text_tail', body))

        references = {}
        for identity in identities:
            for name, body in cases.items():
                sample, rows = request(size, identity, name, body)
                report['samples'].append(sample)
                check(f'Pre-concurrency {identity}/{name}', validate(rows, size, identity, name, body))
                references[identity, name] = rows
        workload = [(identity, name) for identity in identities for name in cases]
        for readers in (1, 4, 8):
            for wave in range(10):
                barrier = Barrier(readers)
                selected = [workload[(wave * readers + i) % len(workload)] for i in range(readers)]
                with ThreadPoolExecutor(max_workers=readers) as pool:
                    futures = [pool.submit(request, size, identity, name, cases[name], readers, barrier, "concurrent") for identity, name in selected]
                    replies = [future.result(timeout=40) for future in futures]
                for (identity, name), (sample, rows) in zip(selected, replies):
                    report['samples'].append(sample)
                    check(f'{readers} readers/wave {wave}/{identity}/{name}: full response parity', rows == references[identity, name])
                save()
        # Revoke a public assertion after readers finish; leave the orphan grant.
        con.update_query(prefix + 'DELETE DATA { GRAPH fasnacht:data { <urn:oldap-load:item:00000> oldap:attachedToRole oldap:Unknown . } }')
        for identity in identities:
            sample, rows = request(size, identity, 'revoked_count', cases['count'])
            report['samples'].append(sample)
            check(f'{identity}: subsequent count observes revocation', rows['count'] == len(expected(size, identity)) - 1)
        report['status'] = 'passed'
    except Exception as error:
        report['status'] = 'failed'
        # Do not retain response bodies, credentials or arbitrary request details.
        report['failure'] = {'type': type(error).__name__, 'message': str(error) if isinstance(error, AssertionError) else 'Request/setup failed; see owned process logs.'}
        raise
    finally:
        report['latency_by_readers'] = {str(n): {'samples': len(values), 'median_ms': statistics.median(values), 'maximum_ms': max(values), 'p95_ms': sorted(values)[math.ceil(len(values) * .95) - 1]}
            for n in (1, 4, 8) if (values := [s['ms'] for s in report['samples'] if s['readers'] == n and s['phase'] == 'concurrent'])}
        save()
        (output / 'browser-stop').touch()


if __name__ == '__main__':
    import sys
    if '--fulltext-preview' not in sys.argv and '--help' not in sys.argv:
        raise SystemExit('Requires the owned --browser-preview --fulltext-preview fixture.')
    import check_fasnacht_fulltext
    original = check_fasnacht_fulltext.check_fasnacht_fulltext

    def checked(call, con, base, output, public, audit):
        original(call, con, base, output, public, audit)
        exercise(con, base, output, public, audit)

    check_fasnacht_fulltext.check_fasnacht_fulltext = checked
    runpy.run_path(str(Path(__file__).with_name('probe_api_jena.py')), run_name='__main__')
