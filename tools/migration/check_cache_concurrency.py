"""Bounded concurrent HTTP reads across committed permission changes.

Every worker owns a requests.Session. The writer uses the runner's admin client.
Requests overlapping a mutation may observe either committed state; requests
started in the subsequent phase must all observe the new state.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import threading
import time

import requests


def check_cache_concurrency(call, check, base, reader, outsider, detail, search, query, grants, output):
    """Exercise four independent clients through object and role revocation.

    The caller supplies its owned, warm-cache fixture and active access tokens.
    Two clients use the reader identity and two the unrelated identity. Each
    phase performs two search/count/detail cycles per client. Only the writer
    mutates fixture grants; the original state is restored after each scenario.
    Aggregate evidence excludes tokens and response contents.
    """
    records = []

    def worker(index, expected, barrier):
        identity = 'reader' if index % 2 == 0 else 'outsider'
        allowed = expected if identity == 'reader' else 0
        local = []
        with requests.Session() as session:
            session.headers.update(reader if identity == 'reader' else outsider)
            barrier.wait(timeout=15)
            for _ in range(2):
                for kind, method, path, body in (
                    ('search', 'POST', search, query),
                    ('count', 'POST', search, {**query, 'countOnly': True}),
                    ('detail', 'GET', detail, None),
                ):
                    started = time.perf_counter()
                    response = session.request(method, base + path, json=body, timeout=30)
                    finished = time.perf_counter()
                    if kind == 'detail':
                        assert response.status_code in (200, 404), (kind, response.status_code)
                        visible = int(response.status_code == 200)
                    else:
                        assert response.status_code == 200, (kind, response.status_code)
                        data = response.json()
                        visible = len(data) if kind == 'search' else data['count']
                        assert visible in (0, 1), (kind, visible)
                        if kind == 'search' and visible:
                            assert data[0]['iri'] in ('demo:cache-child', 'https://example.org/demo/cache-child')
                    # None permits either snapshot only during the transition.
                    if allowed is not None:
                        assert visible == allowed, (identity, kind, allowed, visible)
                    local.append({'identity': identity, 'kind': kind, 'visible': visible,
                                  'start': started, 'end': finished})
        return local

    def phase(name, expected, mutation=None):
        barrier = threading.Barrier(5)
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(worker, index, expected, barrier) for index in range(4)]
            barrier.wait(timeout=15)
            if mutation:
                mutation_start = time.perf_counter()
                mutation()
                mutation_end = time.perf_counter()
            rows = [row for future in futures for row in future.result()]
        overlap = sum(row['start'] < mutation_end and row['end'] > mutation_start for row in rows) if mutation else 0
        if mutation:
            check(name + ': reads overlap the acknowledged permission change', overlap > 0)
        check(name + ': all concurrent responses obey identity and phase visibility', len(rows) == 24)
        records.append({'phase': name, 'requests': len(rows), 'overlapping_mutation': overlap,
                        'visible_responses': sum(row['visible'] for row in rows),
                        'max_request_ms': round(max(row['end'] - row['start'] for row in rows) * 1000, 3)})

    phase('Warm concurrent baseline', 1)
    for label, revoke, restore in (
        ('Object grant',
         lambda: call('POST', detail, {'oldap:attachedToRole': {
             'demo:CacheReader': 'DATA_RESTRICTED', 'demo:CacheOwner': 'DATA_PERMISSIONS'}}),
         lambda: call('POST', detail, {'oldap:attachedToRole': grants})),
        ('User role',
         lambda: call('POST', '/admin/user/cache-reader', {'hasRole': {}}),
         lambda: call('POST', '/admin/user/cache-reader', {'hasRole': {'demo:CacheReader': 'DATA_VIEW'}})),
    ):
        try:
            phase(label + ' revocation in progress', None, revoke)
            # The preceding mutation has returned HTTP success before any
            # worker in this phase is started: no stale result is permitted.
            phase(label + ' after confirmed revocation', 0)
        finally:
            restore()
        phase(label + ' after confirmed restoration', 1)
    (output / 'cache-concurrency.json').write_text(json.dumps({
        'status': 'passed', 'clients': 4, 'identities': 2,
        'request_count': sum(row['requests'] for row in records), 'phases': records,
        'scope': 'Owned warm Redis/Jena; bounded threaded HTTP acceptance, not production load capacity.',
        'consistency': 'Overlapping requests may see either committed state. All requests started after acknowledged revocation must deny access.'
    }, indent=2) + '\n')
