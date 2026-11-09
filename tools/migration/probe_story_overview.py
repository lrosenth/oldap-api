"""Compare the public story overview API dependency chain on owned Jena and GraphDB.

Mirrors the current FasnachtsPage unfiltered overview: concurrent story/keyword
reads, followed by batches of lead-image summaries. Excludes login, image bytes,
viewport capability issuance and browser rendering. Existing source is read-only.
Run with the same CLI as probe_backend_comparison.py; output contains no bodies.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import re
import runpy
import statistics
import sys
import time
from pathlib import Path
from urllib.parse import unquote

import requests
from probe_backend_comparison import fingerprint, source_snapshot

STORIES = {
    'includeProperties': ['fasnacht:storyTitle', 'fasnacht:storyDate',
        'fasnacht:isPublished', 'fasnacht:leadImage', 'fasnacht:leadImageRegion',
        'fasnacht:storyKeywords', 'schema:abstract'],
    'filter': [{'property': 'fasnacht:isPublished', 'op': '==', 'value': True, 'type': 'boolean'}],
    'sortBy': ['fasnacht:storyDate|desc'], 'limit': 1000,
}
MEDIA_PROPERTIES = ['fasnacht:publicationStatus', 'shared:assetId',
                    'shared:serverUrl', 'shared:protocol', 'shared:mediaUrl']


def exercise(call, con, base, output, public, audit):
    """Check content parity, then time 20 alternating warm workflows.

    Keyword requests overlap search and image lookup as in the page effects.
    Summary batches follow search and retain the frontend's 100-IRI batch size.
    Only recreated rubric provenance is excluded from cross-backend comparison.
    Complete responses must remain stable within each backend.
    """
    report = {'status': 'running', 'samples': [], 'scope': __doc__}
    try:
        report['source_before'] = source_snapshot()
        source = Path(sys.argv[sys.argv.index('--fasnacht-export') + 1])
        assert hashlib.sha256(source.read_bytes()).hexdigest() == report['source_before']
        login = requests.post('http://localhost:8000/admin/auth/unknown', json={}, timeout=30)
        login.raise_for_status()
        targets = {'graphdb': ('http://localhost:8000', {'Authorization': 'Bearer ' + login.json()['accessToken']}),
                   'jena': (base, public)}

        raw_keywords = {}

        def workflow(backend):
            url, headers = targets[backend]
            def request(method, path, body=None):
                start = time.perf_counter()
                response = requests.request(method, url + path, json=body, headers=headers, timeout=60)
                response.raise_for_status()
                return response.json(), (time.perf_counter() - start) * 1000
            start = time.perf_counter()
            with ThreadPoolExecutor(max_workers=2) as pool:
                keywords_future = pool.submit(request, 'GET', '/admin/hlist/fasnacht/StoryKeywords')
                stories_future = pool.submit(request, 'POST', '/data/search/fasnacht/class/fasnacht:Story', STORIES)
                stories, search_ms = stories_future.result()
                text_ready_ms = (time.perf_counter() - start) * 1000
                iris = []
                for story in stories:
                    source = next(iter(story.get('fasnacht:leadImage', [])), '')
                    if source.startswith('oldap-media:'):
                        source = unquote(source[len('oldap-media:'):])
                    elif not re.match(r'^(?:urn:\S+|fasnacht:\S+|https?://fasnacht\.digital/ns/\S+)$', source):
                        continue
                    if source not in iris:
                        iris.append(source)
                summaries, summary_ms = [], 0
                for offset in range(0, len(iris), 100):
                    result, elapsed = request('POST', '/data/summaries/fasnacht', {
                        'iris': iris[offset:offset + 100], 'includeProperties': MEDIA_PROPERTIES,
                        'includeMediaDelivery': False})
                    summaries.append(result)
                    summary_ms += elapsed
                media_ready_ms = (time.perf_counter() - start) * 1000
                keywords, keyword_ms = keywords_future.result()
            sample = {'backend': backend, 'search_ms': search_ms, 'keywords_ms': keyword_ms,
                      'summaries_ms': summary_ms, 'text_ready_ms': text_ready_ms,
                      'media_metadata_ready_ms': media_ready_ms,
                      'all_metadata_ready_ms': (time.perf_counter() - start) * 1000}
            raw_keywords[backend] = keywords
            bodies = {'stories': fingerprint(stories), 'keywords': fingerprint(keywords),
                      'summaries': fingerprint(summaries)}
            return sample, bodies, {'stories': len(stories), 'lead_image_iris': len(iris),
                                   'summary_batches': len(summaries)}

        references = {}
        report['first_observed'] = []
        for backend in targets:
            sample, bodies, counts = workflow(backend)
            references[backend] = bodies
            report['first_observed'].append(sample)
            report.setdefault('counts', {})[backend] = counts
        report['parity'] = {key: references['graphdb'][key] == references['jena'][key]
                            for key in references['graphdb']}
        report['fingerprints'] = references
        if not report['parity']['keywords']:
            # Retain only structural difference paths, never private response values.
            def differences(left, right, path=''):
                if type(left) is not type(right):
                    return [path + ':type']
                if isinstance(left, dict):
                    return [p for key in sorted(set(left) | set(right)) for p in
                            (differences(left[key], right[key], path + '/' + key)
                             if key in left and key in right else [path + '/' + key + ':missing'])]
                if isinstance(left, list):
                    return ([path + ':length'] if len(left) != len(right) else
                            [p for i, (a, b) in enumerate(zip(left, right)) for p in differences(a, b, path + '/' + str(i))])
                return [] if left == right else [path]
            report['keyword_difference_paths'] = differences(raw_keywords['graphdb'], raw_keywords['jena'])
        def keyword_content(value):
            # Fresh YAML imports intentionally create new provenance. Keep all
            # node identities, labels, definitions and hierarchy for comparison.
            if isinstance(value, dict):
                return {k: keyword_content(v) for k, v in value.items()
                        if k not in {'creator', 'contributor', 'created', 'modified'}}
            if isinstance(value, list):
                return [keyword_content(v) for v in value]
            return value
        report['keyword_content_equal'] = fingerprint(keyword_content(raw_keywords['graphdb'])) == fingerprint(keyword_content(raw_keywords['jena']))
        assert report['parity']['stories'] and report['parity']['summaries'] and report['keyword_content_equal'], 'Overview content mismatch; no timing claim'
        for backend in targets:
            assert workflow(backend)[1] == references[backend], 'Warm-up changed'
        for iteration in range(20):
            for backend in (list(targets) if iteration % 2 == 0 else list(reversed(targets))):
                sample, bodies, counts = workflow(backend)
                assert bodies == references[backend], 'Timed response changed'
                report['samples'].append(sample)
            print('STORY_WAVE', iteration + 1, 'passed', flush=True)
        report['source_after'] = source_snapshot()
        assert report['source_after'] == report['source_before'], 'Source changed'
        report['summary'] = {backend: {key: statistics.median(s[key] for s in report['samples'] if s['backend'] == backend)
            for key in report['samples'][0] if key != 'backend'} for backend in targets}
        report['java_heap_mib'] = json.loads((output / 'java-process.json').read_text())['maximum_heap_mib']
        report['status'] = 'passed'
    except Exception:
        report['status'] = 'failed'
        raise
    finally:
        (output / 'story-overview-results.json').write_text(json.dumps(report, indent=2) + '\n')
        (output / 'browser-stop').touch()


if __name__ == '__main__':
    import check_fasnacht_fulltext
    check_fasnacht_fulltext.check_fasnacht_fulltext = exercise
    runpy.run_path(str(Path(__file__).with_name('probe_api_jena.py')), run_name='__main__')
