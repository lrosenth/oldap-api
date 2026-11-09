"""Decompose the six real-data HTTP searches on an isolated Jena API.

Use the owned preview CLI, including --fulltext-preview and --fasnacht-export.
No source writes. Timing hooks are sequential and test-only; normal application
code is unchanged. Detailed query texts/profiles stay in the private output.
--compare-dating-precheck performs an ABBA comparison of the new precheck with
the former unconditional factory path, plus live future-field model checks.
--baseline-count-profile replays saved count queries from a private profile;
--baseline-summary-builder loads a trusted objectfactory snapshot;
--baseline-validator loads only XsdValidator from a trusted datatype snapshot.
--baseline-resource-reader loads ResourceClass.read from a trusted snapshot to
compare superclass reconstruction with and without operation-local snapshots.
These alternatives compare complete responses in ABBA order on the same target.
Snapshot inputs are executable local developer artifacts, never user uploads.
"""
import cProfile
from contextlib import ExitStack, nullcontext
import hashlib
import json
from pathlib import Path
import pstats
import runpy
import statistics
import subprocess
import time
from unittest.mock import patch

import requests
from flask import Flask, request as flask_request
from probe_backend_comparison import fingerprint, search_cases, source_snapshot


def exercise(call, con, base, output, public, audit, *, compare_dating=False, baseline_counts=None, baseline_summary=None, baseline_validator=None, baseline_resource_reader=None):
    """Measure transport/server/decoding spans and separately collect CPU profiles.

    Server dispatch includes parse/evaluation/serialization. Transport residual
    includes socket setup, response transfer, scheduling and unmeasured servlet
    work, not just wire time. Nested decoding/hydration spans are not additive.
    cProfile runs are separate because instrumentation materially changes latency.
    """
    from oldaplib.src.jena_connection import JenaConnection
    from oldaplib.src.enums.xsd_datatypes import XsdValidator
    from oldaplib.src import objectfactory
    from oldap_api.views import instance_views
    import sys
    source = Path(sys.argv[sys.argv.index('--fasnacht-export') + 1])
    report = {'status': 'running', 'samples': [], 'profiles': {}, 'source_before': source_snapshot(),
              'java': json.loads((output / 'java-process.json').read_text())}
    report['java'].pop('pid')
    current = None
    try:
        assert hashlib.sha256(source.read_bytes()).hexdigest() == report['source_before']
        tools = Path(__file__).resolve().parents[3] / 'oldap-tools'
        result = subprocess.run([str(tools / '.venv/bin/oldap-tools'), '--api', base, '--user', 'actor',
            '--password', 'owned-fixture-password', 'ontology', 'load', '-i',
            str(tools / 'examples/ontology/fasnacht-jena.yaml'), '--fulltext', 'apply', '--no-backup'],
            capture_output=True, text=True, timeout=180)
        (output / 'profile-fulltext.log').write_text(result.stdout + result.stderr)
        assert result.returncode == 0, 'Owned fulltext setup failed'
        cases = search_cases()
        endpoint = '/data/search/fasnacht/class/fasnacht:ArchiveObject'
        originals = {'http': requests.sessions.Session.request, 'dispatch': Flask.full_dispatch_request,
            'decode': JenaConnection._decode, 'construct': objectfactory.ConstructProcessor.process,
            'dating': instance_views._expand_search_dating, 'resource_query': objectfactory.resource_query, 'summary_builder': objectfactory._build_resource_summaries_query, 'validator': XsdValidator.validate, 'resource_reader': objectfactory.ResourceClass.read}
        def http(session, method, url, **kwargs):
            measured = current is not None and url.startswith(con._jena.url + '/')
            if not measured:
                return originals['http'](session, method, url, **kwargs)
            kwargs['headers'] = {**kwargs.get('headers', {}), 'X-Probe-Timing': 'yes'}
            body = kwargs.get('data', b'')
            if isinstance(body, bytes):
                body = body.decode()
            query_hash = hashlib.sha256(body.encode()).hexdigest()[:16]
            (output / f"request-{query_hash}.txt").write_text(body)
            started = time.perf_counter()
            response = originals['http'](session, method, url, **kwargs)
            elapsed = (time.perf_counter() - started) * 1000
            auth = response.headers.get('X-Probe-Authentication-Nanos')
            dispatch = response.headers.get('X-Probe-Dispatch-Nanos')
            assert auth is not None and dispatch is not None, 'Missing native timing headers'
            current['calls'].append({'operation': url[len(con._jena.url)+1:].split('/')[0],
                'query_hash': query_hash, 'ms': elapsed, 'authentication_ms': int(auth)/1e6,
                'dispatch_ms': int(dispatch)/1e6, 'bytes': len(response.content)})
            return response
        def dispatch(app):
            if current is None or flask_request.path != endpoint:
                return originals['dispatch'](app)
            profiler = cProfile.Profile() if current['phase'] == 'profile' else None
            started = time.perf_counter()
            if profiler:
                profiler.enable()
            try:
                return originals['dispatch'](app)
            finally:
                if profiler:
                    profiler.disable()
                    profiler.dump_stats(str(output / (current['case'] + '.prof')))
                    stats = pstats.Stats(profiler)
                    # Function paths/names only, never locals or request values.
                    entries = [{'function': f'{Path(key[0]).name}:{key[1]}:{key[2]}',
                                'calls': value[1], 'self_ms': value[2]*1000, 'cumulative_ms': value[3]*1000}
                               for key, value in stats.stats.items()]
                    report['profiles'][current['case']] = {
                        'top_self': sorted(entries, key=lambda x: x['self_ms'], reverse=True)[:20],
                        'top_cumulative': sorted(entries, key=lambda x: x['cumulative_ms'], reverse=True)[:20]}
                current['api_dispatch_ms'] = (time.perf_counter()-started)*1000
        def timed(name):
            def wrapped(*args, **kwargs):
                started = time.perf_counter()
                try:
                    return originals[name](*args, **kwargs)
                finally:
                    if current is not None:
                        current[name+'_ms'] = current.get(name+'_ms', 0) + (time.perf_counter()-started)*1000
            return wrapped
        if compare_dating:
            from oldaplib.src.helpers.context import Context
            prefix = Context(name=con.context_name).sparql_context
            # Fresh declarations in the disposable model exercise future fields;
            # normal real-data cases below also verify inherited date hydration.
            triples = """<urn:dating-check:parent> sh:property <urn:dating-check:shape> .
                <urn:dating-check:child> sh:node <urn:dating-check:parent> .
                <urn:dating-check:shape> sh:path <urn:dating-check:future> ; sh:class oldap:Dating .
                <urn:dating-check:inverse> oldap:field <urn:dating-check:reverse> ;
                    sh:path [ sh:inversePath <urn:dating-check:source> ] ; sh:class oldap:Dating ."""
            con.update_query(prefix + 'INSERT DATA { GRAPH fasnacht:shacl { ' + triples + ' } }')
            for prop in ('urn:dating-check:future', 'urn:dating-check:reverse'):
                assert instance_views._search_may_include_dating(con, 'fasnacht', [prop])
            con.update_query(prefix + 'DELETE WHERE { GRAPH fasnacht:shacl { <urn:dating-check:shape> sh:class ?type } }')
            assert not instance_views._search_may_include_dating(con, 'fasnacht', ['urn:dating-check:future'])
            report['live_model_checks'] = 'Future/inherited declaration, inverse field and immediate removal pass'
        def count_query(connection, sparql, *args, **kwargs):
            if baseline_counts and current and current['plan'] == 'baseline' and current['case'] in baseline_counts:
                if 'COUNT(DISTINCT ?res)' in sparql:
                    sparql = baseline_counts[current['case']]
            return originals['resource_query'](connection, sparql, *args, **kwargs)
        def summary_builder(*args, **kwargs):
            implementation = baseline_summary if baseline_summary and current and current['plan'] == 'baseline' else originals['summary_builder']
            return implementation(*args, **kwargs)
        def validate(cls, *args, **kwargs):
            implementation = baseline_validator if baseline_validator and current and current['plan'] == 'baseline' else originals['validator']
            return implementation(*args, **kwargs)
        def resource_reader(cls, *args, **kwargs):
            if baseline_resource_reader and current and current['plan'] == 'baseline':
                return baseline_resource_reader(cls, *args, **kwargs)
            return originals['resource_reader'](*args, **kwargs)
        references = {}
        with ExitStack() as stack:
            stack.enter_context(patch.object(objectfactory.ResourceClass, 'read', classmethod(resource_reader)))
            stack.enter_context(patch.object(XsdValidator, 'validate', classmethod(validate)))
            stack.enter_context(patch.object(objectfactory, 'resource_query', count_query))
            stack.enter_context(patch.object(objectfactory, '_build_resource_summaries_query', summary_builder))
            stack.enter_context(patch.object(requests.sessions.Session, 'request', http))
            stack.enter_context(patch.object(Flask, 'full_dispatch_request', dispatch))
            stack.enter_context(patch.object(JenaConnection, '_decode', staticmethod(timed('decode'))))
            stack.enter_context(patch.object(objectfactory.ConstructProcessor, 'process', staticmethod(timed('construct'))))
            stack.enter_context(patch.object(instance_views, '_expand_search_dating', timed('dating')))
            rounds = ([('warmup', plan) for plan in ('baseline', 'optimized')]
                      + [('timing', plan) for plan in ('baseline', 'optimized', 'optimized', 'baseline') * 2]
                      if compare_dating or baseline_counts or baseline_summary or baseline_validator or baseline_resource_reader else [(phase, 'optimized') for phase in
                        ('warmup', 'timing', 'timing', 'timing', 'timing', 'timing', 'profile')])
            for phase, plan in rounds:
                for case in (list(cases) if len(report['samples']) % 2 == 0 else list(reversed(cases))):
                    current = {'case': case, 'phase': phase, 'plan': plan, 'calls': []}
                    started = time.perf_counter()
                    # Bypass ONLY the new precheck to reproduce the old path;
                    # no model, query, ACL or hydration implementation is replaced.
                    control = patch.object(instance_views, '_search_may_include_dating', lambda *args: True) if compare_dating and plan == 'baseline' else nullcontext()
                    with control:
                        response = requests.post(base + endpoint, json=cases[case],
                            headers={**public, 'Accept': 'application/json; dating=structured'}, timeout=30)
                    current['http_ms'] = (time.perf_counter()-started)*1000
                    assert response.status_code == 200
                    actual = fingerprint(response.json())
                    references.setdefault(case, actual)
                    assert references[case] == actual, 'Profile changed full API response'
                    current['backend_http_ms'] = sum(x['ms'] for x in current['calls'])
                    current['authentication_ms'] = sum(x['authentication_ms'] for x in current['calls'])
                    current['dispatch_ms'] = sum(x['dispatch_ms'] for x in current['calls'])
                    current['transport_residual_ms'] = current['backend_http_ms'] - current['authentication_ms'] - current['dispatch_ms']
                    current['api_other_ms'] = current['api_dispatch_ms'] - current['backend_http_ms']
                    report['samples'].append(current)
                    print('PROFILE',case,phase,round(current['http_ms']),flush=True)
                    current = None
        report['source_after'] = source_snapshot()
        assert report['source_before'] == report['source_after']
        report['status'] = 'passed'
    except BaseException as error:
        report['status'] = 'failed'
        report['failure_type'] = type(error).__name__
        raise
    finally:
        report['summary'] = {}
        for case in search_cases():
            samples = [s for s in report['samples'] if s['phase']=='timing' and s['case']==case and s['plan']=='optimized']
            if samples:
                report['summary'][case] = {key: statistics.median(s.get(key,0) for s in samples) for key in (
                    'http_ms','api_dispatch_ms','backend_http_ms','authentication_ms','dispatch_ms',
                    'transport_residual_ms','api_other_ms','decode_ms','construct_ms','dating_ms')}
                report['summary'][case]['backend_calls'] = [len(s['calls']) for s in samples]
        if compare_dating or baseline_counts or baseline_summary or baseline_validator or baseline_resource_reader:
            report['comparison'] = {case: {plan: {
                'median_ms': statistics.median(s['http_ms'] for s in samples),
                'samples': len(samples), 'backend_calls': [len(s['calls']) for s in samples]}
                for plan in ('baseline', 'optimized')
                if (samples := [s for s in report['samples'] if s['case']==case and s['phase']=='timing' and s['plan']==plan])}
                for case in search_cases()}
        (output / 'backend-profile-results.json').write_text(json.dumps(report,indent=2)+'\n')
        (output / 'browser-stop').touch()


if __name__ == '__main__':
    import sys
    if '--fulltext-preview' not in sys.argv and '--help' not in sys.argv:
        raise SystemExit('Requires --browser-preview --fulltext-preview --fasnacht-export.')
    import check_fasnacht_fulltext
    from functools import partial
    compare_dating = '--compare-dating-precheck' in sys.argv
    if compare_dating:
        sys.argv.remove('--compare-dating-precheck')
    baseline_counts = None
    if '--baseline-count-profile' in sys.argv:
        index = sys.argv.index('--baseline-count-profile')
        profile = Path(sys.argv[index + 1]).resolve()
        del sys.argv[index:index + 2]
        saved = json.loads((profile / 'backend-profile-results.json').read_text())
        baseline_counts = {}
        for sample in saved['samples']:
            if sample['case'] not in ('count', 'dating_count', 'fulltext_count'):
                continue
            for item in sample['calls']:
                raw = (profile / ('request-' + item['query_hash'] + '.txt')).read_text()
                query = json.loads(raw)['query'] if item['operation'] == 'FULLTEXT_READ' else raw
                if 'COUNT(DISTINCT ?res)' in query:
                    baseline_counts[sample['case']] = query
        assert len(baseline_counts) == 3, 'Incomplete trusted count baseline'
    baseline_summary = None
    if '--baseline-summary-builder' in sys.argv:
        index = sys.argv.index('--baseline-summary-builder')
        snapshot = Path(sys.argv[index + 1]).resolve()
        del sys.argv[index:index + 2]
        # Trusted local snapshot only: runpy executes code, not data.
        baseline_summary = runpy.run_path(str(snapshot))['_build_resource_summaries_query']
    baseline_validator = None
    if '--baseline-validator' in sys.argv:
        index = sys.argv.index('--baseline-validator')
        snapshot = Path(sys.argv[index + 1]).resolve()
        del sys.argv[index:index + 2]
        # Like the summary control, this executes only a trusted local snapshot.
        # Load only the old validator class: importing the old enum definition
        # would replace serializer registrations and invalidate the comparison.
        import ast
        from oldaplib.src.enums import xsd_datatypes
        node = next(n for n in ast.parse(snapshot.read_text()).body
                    if isinstance(n, ast.ClassDef) and n.name == 'XsdValidator')
        namespace = dict(vars(xsd_datatypes))
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(snapshot), 'exec'), namespace)
        baseline_validator = namespace['XsdValidator'].validate
    baseline_resource_reader = None
    if '--baseline-resource-reader' in sys.argv:
        index = sys.argv.index('--baseline-resource-reader')
        snapshot = Path(sys.argv[index + 1])
        del sys.argv[index:index + 2]
        import ast
        from oldaplib.src import resourceclass
        cls = next(n for n in ast.parse(snapshot.read_text()).body
                   if isinstance(n, ast.ClassDef) and n.name == 'ResourceClass')
        node = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'read')
        namespace = dict(vars(resourceclass))
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(snapshot), 'exec'), namespace)
        baseline_resource_reader = namespace['read'].__func__
    check_fasnacht_fulltext.check_fasnacht_fulltext = partial(exercise, compare_dating=compare_dating,
        baseline_counts=baseline_counts, baseline_summary=baseline_summary, baseline_validator=baseline_validator,
        baseline_resource_reader=baseline_resource_reader)
    runpy.run_path(str(Path(__file__).with_name('probe_api_jena.py')),run_name='__main__')
