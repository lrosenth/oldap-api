"""Bounded read-only GraphDB/current-Jena HTTP comparison on real Fasnacht data.

Uses the owned Jena preview runner and its CLI. Source GraphDB/API are read only:
no cache flush, model change, synthetic population or write workload. Activate
only target fulltext configuration, then compare public results before timing.
Private reports contain aggregates and fingerprints, never tokens or bodies.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
from pathlib import Path
import runpy
import statistics
import subprocess
from threading import Barrier
import time

import requests


def fingerprint(value):
    """Ignore RDF value order inside rows, but preserve result-page order."""
    def canonical(item):
        if isinstance(item, dict):
            return {k: canonical(v) for k, v in sorted(item.items())}
        if isinstance(item, list):
            return sorted((canonical(v) for v in item), key=lambda v: json.dumps(v, sort_keys=True))
        return item
    normalized = [canonical(row) for row in value] if isinstance(value, list) else canonical(value)
    return hashlib.sha256(json.dumps(normalized, sort_keys=True).encode()).hexdigest()


def comparable_fingerprint(value):
    """Ignore engine-specific relevance scores for explicitly title-sorted pages.

    All resource IDs, row order, types and projected RDF values remain checked.
    Per-backend stability still uses the complete fingerprint including scores.
    """
    if isinstance(value, list):
        value = [{k: v for k, v in row.items() if k != 'score'} for row in value]
    return fingerprint(value)


def source_snapshot():
    """Hash the same asserted project export before and after the read workload."""
    response = requests.get('http://localhost:7200/repositories/oldap/statements',
        params=[('context', '<http://fasnacht.digital/ns/' + part + '>') for part in ('data', 'onto', 'shacl', 'lists')] + [('infer', 'false')],
        headers={'Accept': 'application/x-trigstar'}, timeout=60)
    response.raise_for_status()
    return hashlib.sha256(response.content).hexdigest()


def search_cases():
    """The shared six-case real-data workload for timing and profiling."""
    common = {'limit': 100, 'sortBy': ['schema:name|asc'], 'includeProperties': ['schema:name']}
    dated = {**common, 'filter': [{'property': 'fasnacht:dating', 'op': 'overlaps', 'type': 'dating',
                'value': {'dateStart': '1900-01-01', 'dateEnd': '1999-12-31'}}],
             'includeProperties': ['schema:name', 'fasnacht:dating']}
    text = {**common, 'ftfilter': [{'field': 'archiveObjectTitle', 'query': 'Laterne'}]}
    return {'metadata': common, 'count': {**common, 'countOnly': True},
             'dating': dated, 'dating_count': {**dated, 'countOnly': True},
             'fulltext': text, 'fulltext_count': {**text, 'countOnly': True}}


def exercise(call, con, base, output, public, audit):
    """Compare public semantics, then alternate bounded 1/4/8-reader waves.

    Mismatching cases are retained as diagnostics and excluded from speed claims.
    Each timed response must match its own verified pre-load reference. Wave
    throughput includes client startup and is distinct from per-request latency.
    """
    report = {'status': 'running', 'scope': 'Public real-data reads; existing GraphDB/API versus owned configurable-heap Jena/threaded API. Unequal service topology, not an engine-only or production-capacity comparison.',
              'samples': [], 'waves': [], 'comparisons': {}, 'page_size': 100}
    report['java'] = json.loads((output / 'java-process.json').read_text())
    report['java'].pop('pid')
    report_path = output / 'backend-comparison-results.json'
    def save():
        report_path.write_text(json.dumps(report, indent=2) + '\n')
    try:
        report['source_before'] = source_snapshot()
        # The source file must be the same snapshot used to build this target.
        import sys
        source_file = Path(sys.argv[sys.argv.index('--fasnacht-export') + 1])
        if hashlib.sha256(source_file.read_bytes()).hexdigest() != report['source_before']:
            raise AssertionError('Source export changed before comparison')
        tools = Path(__file__).resolve().parents[3] / 'oldap-tools'
        command = [str(tools / '.venv/bin/oldap-tools'), '--api', base, '--user', 'actor',
                   '--password', 'owned-fixture-password', 'ontology', 'load', '-i',
                   str(tools / 'examples/ontology/fasnacht-jena.yaml'), '--fulltext', 'apply', '--no-backup']
        result = subprocess.run(command, capture_output=True, text=True, timeout=180)
        (output / 'comparison-fulltext.log').write_text(result.stdout + result.stderr)
        if result.returncode:
            raise AssertionError('Owned fulltext setup failed')
        login = requests.post('http://localhost:8000/admin/auth/unknown', json={}, timeout=30)
        login.raise_for_status()
        targets = {'graphdb': ('http://localhost:8000', {'Authorization': 'Bearer ' + login.json()['accessToken']}),
                   'jena': (base, public)}
        cases = search_cases()
        path = '/data/search/fasnacht/class/fasnacht:ArchiveObject'
        def request(backend, case, readers=1, barrier=None):
            url, headers = targets[backend]
            if barrier:
                barrier.wait(timeout=15)
            started = time.perf_counter()
            with requests.Session() as session:
                response = session.post(url + path, json=cases[case],
                    headers={**headers, 'Accept': 'application/json; dating=structured'}, timeout=30)
            sample = {'backend': backend, 'case': case, 'readers': readers,
                      'ms': round((time.perf_counter() - started) * 1000, 3),
                      'http_status': response.status_code, 'bytes': len(response.content)}
            body = response.json() if response.status_code == 200 else None
            return sample, body
        references = {}
        eligible = []
        for case in cases:
            replies = {}
            for backend in targets:
                sample, body = request(backend, case)
                replies[backend] = (sample, body)
                references[backend, case] = fingerprint(body)
            same = all(v[0]['http_status'] == 200 for v in replies.values()) and comparable_fingerprint(replies['graphdb'][1]) == comparable_fingerprint(replies['jena'][1])
            report['comparisons'][case] = {'equal_except_engine_score': same, 'full_response_equal': references['graphdb', case] == references['jena', case], 'backends': {backend: {
                'status': sample['http_status'], 'count_or_rows': len(body) if isinstance(body, list) else body.get('count') if isinstance(body, dict) else None,
                'fingerprint': references[backend, case]} for backend, (sample, body) in replies.items()}}
            if same:
                eligible.append(case)
            print('COMPARE', case, 'equal' if same else 'different', flush=True)
        save()
        if not eligible:
            raise AssertionError('No equivalent successful workload cases')
        # All cases get an additional untimed warm-up on each backend.
        for backend in targets:
            for case in eligible:
                sample, body = request(backend, case)
                if sample['http_status'] != 200 or fingerprint(body) != references[backend, case]:
                    raise AssertionError('Warm-up response changed')
        for readers in (1, 4, 8):
            for wave in range(len(eligible) * 2):
                selected = [eligible[(wave * readers + i) % len(eligible)] for i in range(readers)]
                for backend in (list(targets) if wave % 2 == 0 else list(reversed(targets))):
                    barrier = Barrier(readers)
                    started = time.perf_counter()
                    with ThreadPoolExecutor(max_workers=readers) as pool:
                        futures = [pool.submit(request, backend, case, readers, barrier) for case in selected]
                        replies = [future.result(timeout=40) for future in futures]
                    wall = time.perf_counter() - started
                    report['waves'].append({'backend': backend, 'readers': readers, 'seconds': wall, 'requests': readers})
                    for case, (sample, body) in zip(selected, replies):
                        report['samples'].append(sample)
                        if sample['http_status'] != 200 or fingerprint(body) != references[backend, case]:
                            raise AssertionError('Timed response changed or failed')
                    save()
                print('WAVE', readers, wave, 'passed', flush=True)
        report['source_after'] = source_snapshot()
        if report['source_before'] != report['source_after']:
            raise AssertionError('Source export changed during comparison')
        report['status'] = 'passed' if len(eligible) == len(cases) else 'partial: semantic differences excluded'
    except Exception as error:
        report['status'] = 'failed'
        report['failure_type'] = type(error).__name__
        raise
    finally:
        report['summary'] = []
        for backend in ('graphdb', 'jena'):
            for readers in (1, 4, 8):
                values = [s['ms'] for s in report['samples'] if s['backend'] == backend and s['readers'] == readers]
                waves = [w for w in report['waves'] if w['backend'] == backend and w['readers'] == readers]
                if values:
                    report['summary'].append({'backend': backend, 'readers': readers, 'requests': len(values),
                        'median_ms': statistics.median(values), 'p95_ms': sorted(values)[math.ceil(len(values)*.95)-1],
                        'requests_per_second': sum(w['requests'] for w in waves)/sum(w['seconds'] for w in waves)})
        report['case_summary'] = []
        for backend in ('graphdb', 'jena'):
            for case in ('metadata', 'count', 'dating', 'dating_count', 'fulltext', 'fulltext_count'):
                values = [s['ms'] for s in report['samples'] if s['backend'] == backend and s['case'] == case and s['readers'] == 1]
                if values:
                    report['case_summary'].append({'backend': backend, 'case': case,
                        'samples': len(values), 'median_ms': statistics.median(values)})
        save()
        (output / 'browser-stop').touch()


if __name__ == '__main__':
    import sys
    if '--fulltext-preview' not in sys.argv and '--help' not in sys.argv:
        raise SystemExit('Requires --browser-preview --fulltext-preview --fasnacht-export.')
    import check_fasnacht_fulltext
    check_fasnacht_fulltext.check_fasnacht_fulltext = exercise
    runpy.run_path(str(Path(__file__).with_name('probe_api_jena.py')), run_name='__main__')
