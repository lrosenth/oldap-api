"""Measure archive search and structured-date hydration on an owned API target.

Uses probe_api_jena.py arguments and requires --fulltext-preview. Captures only
aggregate timing and generated query plans in the private probe directory.
Optional --baseline-construct-processor PATH compares a trusted pre-edit Python
processor snapshot with the current processor, keeping current SPARQL in both.
Never load an untrusted snapshot: it is executed as Python code.
"""
import json
from pathlib import Path
import re
import runpy
import time
from unittest.mock import patch


def profile(call, output, public, baseline_processor=None):
    """Measure fixed metadata/date requests without changing data or query semantics."""
    from oldap_api.views import instance_views
    from oldaplib.src import objectfactory
    original_process = objectfactory.ConstructProcessor.process
    original_expand = instance_views._expand_search_dating
    original_query = objectfactory.resource_query
    current = {}
    mode = 'baseline'

    def expand(*args, **kwargs):
        started = time.perf_counter()
        try:
            return original_expand(*args, **kwargs)
        finally:
            current['dating_ms'] = round((time.perf_counter() - started) * 1000, 2)

    def process(context, graph):
        started = time.perf_counter()
        try:
            implementation = baseline_processor if mode == 'baseline' and baseline_processor else original_process
            return implementation(context, graph)
        finally:
            current.setdefault('construct_processing_ms', []).append(round((time.perf_counter() - started) * 1000, 2))

    def query(con, sparql, *args, **kwargs):
        root_search = 'SELECT DISTINCT ?res ?resclass' in sparql or 'COUNT(DISTINCT ?res)' in sparql
        if baseline_processor is None and mode == 'baseline' and root_search and current['case'] != 'dating_text':
            assert '?accessTriple' in sparql, 'Optimized root access plan is missing'
        if baseline_processor is None and mode == 'baseline' and '?accessTriple' in sparql:
            # Reconstruct the former root ACL only; leave filters/projection intact.
            # The fixed probe deliberately fails if this implementation marker changes.
            access = re.compile(
                r'\{ SELECT DISTINCT \?res \?searchResclass WHERE \{\s*'
                r'(GRAPH oldap:admin \{[^{}]*\})\s*'
                r'GRAPH fasnacht:data \{[^{}]*\?accessTriple[^{}]*\}\s*\} \}')
            def previous_access(match):
                return match[1] + """
                    GRAPH fasnacht:data {
                        ?res rdf:type ?searchResclass ; oldap:attachedToRole ?role .
                        ?searchGrant rdf:reifies <<( ?res oldap:attachedToRole ?role )>> ;
                                     oldap:hasDataPermission ?DataPermission .
                    }
                """
            sparql, replacements = access.subn(previous_access, sparql, count=1)
            assert replacements == 1, 'Root access plan marker changed'
        started = time.perf_counter()
        try:
            return original_query(con, sparql, *args, **kwargs)
        finally:
            if 'CONSTRUCT' in sparql:
                current.setdefault('construct_queries_ms', []).append(round((time.perf_counter() - started) * 1000, 2))
            if root_search:
                current.setdefault('search_queries_ms', []).append(round((time.perf_counter() - started) * 1000, 2))
                (output / f"metadata-{mode}-{current['case']}.rq").write_text(sparql)

    media_props = ['fasnacht:archiveMediaObjectOf', 'fasnacht:contributingAgent', 'shared:assetId',
                   'shared:serverUrl', 'shared:protocol', 'shared:mediaAccessMode', 'shared:mediaUrl',
                   'shared:thumbnailUrl', 'shared:originalMimeType', 'schema:position', 'dcterms:type']
    object_props = ['schema:name', 'dcterms:type', 'fasnacht:dating', 'fasnacht:location',
                    'fasnacht:associatedOrganisation', 'fasnacht:currentCustodian',
                    'fasnacht:externalSource', 'dcterms:provenance', 'schema:identifier']
    dating = [{'property': 'fasnacht:dating', 'op': 'overlaps', 'type': 'dating',
               'value': {'dateStart': '1910-01-01', 'dateEnd': '1911-12-31'}}]
    cases = [
        ('media', 'ArchiveMediaObject', {'includeProperties': media_props}),
        ('objects', 'CarnivalThing', {'includeProperties': object_props, 'sortBy': ['schema:name|asc']}),
        ('sources', 'ArchiveObject', {'includeProperties': ['fasnacht:externalSource']}),
        ('dating', 'CarnivalThing', {'includeProperties': object_props, 'filter': dating, 'sortBy': [{'property': 'fasnacht:dating', 'kind': 'dating', 'direction': 'desc'}]}),
        ('dating_count', 'CarnivalThing', {'filter': dating, 'countOnly': True}),
        ('dating_text', 'ArchiveObject', {'includeProperties': object_props, 'filter': dating, 'ftfilter': [{'field': 'archiveObjectTitle', 'query': 'Laterne'}]}),
    ]
    samples = []
    with patch.object(instance_views, '_expand_search_dating', expand), \
            patch.object(objectfactory, 'resource_query', query), \
            patch.object(objectfactory.ConstructProcessor, 'process', process):
        expected = {}
        for mode in ('baseline', 'optimized'):
            for name, cls, body in cases:
                for repeat in range(2):
                    current = {'mode': mode, 'case': name, 'repeat': repeat}
                    started = time.perf_counter()
                    rows = call('POST', '/data/search/fasnacht/class/fasnacht:' + cls,
                                {'limit': 5000, **body}, headers={**public, 'Accept': 'application/json; dating=structured'}).json()
                    if mode == 'baseline' and repeat == 0:
                        expected[name] = rows
                    assert rows == expected[name], f'Response changed: {mode}/{name}'
                    current['total_ms'] = round((time.perf_counter() - started) * 1000, 2)
                    current['count'] = rows.get('count') if isinstance(rows, dict) else len(rows)
                    samples.append(current)
                    print('PROFILE_METADATA', json.dumps(current), flush=True)
    (output / 'metadata-performance.json').write_text(json.dumps(samples, indent=2) + '\n')


if __name__ == '__main__':
    import sys
    baseline_processor = None
    if '--baseline-construct-processor' in sys.argv:
        # Load a trusted local snapshot made before editing the processor. This
        # compares only Python hydration; both modes use current runtime SPARQL.
        index = sys.argv.index('--baseline-construct-processor')
        snapshot = Path(sys.argv[index + 1]).resolve()
        del sys.argv[index:index + 2]
        baseline_processor = runpy.run_path(str(snapshot))['ConstructProcessor'].process
    if '--fulltext-preview' not in sys.argv and '--help' not in sys.argv:
        raise SystemExit('Profiling requires --fulltext-preview.')
    import check_fasnacht_fulltext
    original = check_fasnacht_fulltext.check_fasnacht_fulltext

    def checked(call, con, base, output, public, audit):
        original(call, con, base, output, public, audit)
        profile(call, output, public, baseline_processor)

    check_fasnacht_fulltext.check_fasnacht_fulltext = checked
    runpy.run_path(str(Path(__file__).with_name('probe_api_jena.py')), run_name='__main__')
