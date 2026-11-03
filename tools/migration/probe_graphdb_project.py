"""Rehearse one local GraphDB project migration against an isolated Jena API.

The source is only queried/exported and authenticated. Private output contains
source data and two account hashes: never commit it. No live cache is flushed.
JSON arrays are compared as unordered collections (RDF value order is undefined).
This is an offline rehearsal, not a consistent production cutover snapshot.
"""
import argparse
from collections import Counter
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import secrets
import re
import selectors
import subprocess
import threading
from unittest.mock import patch
from urllib.parse import quote

from dotenv import dotenv_values
from flask import Flask
import requests
from werkzeug.serving import make_server
from check_archive_writes import owned_writer_store
from probe_api_jena import QuietHandler

BASE = 'http://oldap.org/base#'
SHARED = 'http://oldap.org/shared#'
PREFIX = f'PREFIX oldap: <{BASE}> PREFIX xsd: <http://www.w3.org/2001/XMLSchema#> '


def normalized(value):
    """Keep all JSON values/types; ignore object and RDF multivalue ordering."""
    if isinstance(value, dict):
        return {key: normalized(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return sorted((normalized(item) for item in value), key=lambda item: json.dumps(item, sort_keys=True))
    return value


def named_turtle_export(content, graph):
    """Wrap GraphDB's Turtle-star CONSTRUCT output in its original named graph.

    Only the exporter-generated, single-line prefix/base prologue is relocated.
    RDF statements and literal contents are copied byte-for-byte and subsequently
    parsed/verified by the native converter; this is not an RDF syntax converter.
    """
    lines = content.decode('utf-8').splitlines(keepends=True)
    boundary = 0
    for line in lines:
        if not line.strip() or re.fullmatch(r'@(?:prefix|base) [^\r\n]+ \.\s*', line):
            boundary += 1
        else:
            break
    return (''.join(lines[:boundary]) + '<' + graph + '> {\n' + ''.join(lines[boundary:]) + '\n}\n').encode()


def run(args):
    """Export, convert, provision, import, compare and always stop owned services."""
    os.umask(0o077)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    library = Path(__file__).resolve().parents[3] / 'oldaplib'
    config = dotenv_values(args.source_config)
    user = config['OLDAP_AUTH_ADMIN_USER']
    password = config['OLDAP_AUTH_ADMIN_PASSWORD']
    source = requests.Session()
    endpoint = args.graphdb + '/repositories/' + args.repository

    def select(query):
        response = source.post(endpoint, data={'query': PREFIX + query, 'infer': 'false'},
                               headers={'Accept': 'application/sparql-results+json'}, timeout=60)
        response.raise_for_status()
        return response.json()['results']['bindings']

    def export(graphs):
        response = source.get(endpoint + '/statements', params=[('context', '<' + graph + '>') for graph in graphs]
                              + [('infer', 'false')], headers={'Accept': 'application/x-trigstar'}, timeout=60)
        response.raise_for_status()
        return response.content

    def login(base, identity, secret=None):
        response = requests.post(base + '/admin/auth/' + quote(identity, safe=''),
                                 json={} if secret is None else {'password': secret}, timeout=60)
        if response.status_code != 200:
            raise AssertionError(f'Login failed: HTTP {response.status_code}')
        return {'Authorization': 'Bearer ' + response.json()['accessToken']}

    def read(base, path, headers):
        response = requests.get(base + path, headers=headers, timeout=90)
        try:
            body = response.json()
        except ValueError:
            body = response.text
        return {'status': response.status_code, 'body': normalized(body)}

    def convert(path, name):
        result = subprocess.run([args.java, '--class-path', str(args.jar),
            str(library / 'tools/migration/ConvertLegacyRdfStar.java'), str(path), str(output / name)],
            cwd=library, capture_output=True, timeout=90)
        (output / (name + '.log')).write_bytes(result.stdout + result.stderr)
        if result.returncode:
            raise AssertionError(f'Conversion failed: inspect private {name}.log')
        return output / name / 'converted.trig'

    project_rows = select('SELECT ?ns WHERE { GRAPH oldap:admin { ?p oldap:projectShortName '
                          + json.dumps(args.project) + '^^xsd:NCName ; oldap:namespaceIri ?ns } }')
    if len(project_rows) != 1:
        raise ValueError('Project must resolve to exactly one namespace')
    namespace = project_rows[0]['ns']['value']
    parts = ['data', 'onto', 'shacl', 'lists']
    graphs = [namespace + part for part in parts]
    project_bytes = export(graphs)
    (output / 'source-project.trig').write_bytes(project_bytes)
    vocab_graphs = [row['g']['value'] for row in select(
        'SELECT DISTINCT ?g WHERE { GRAPH ?g { ?s ?p ?o } '
        'FILTER(STRSTARTS(STR(?g), "urn:oldap:vocab:")) } ORDER BY ?g')]
    schema_graphs = [BASE + part for part in ('onto', 'shacl')] + [SHARED + part for part in ('onto', 'shacl', 'lists')] + vocab_graphs
    schema_bytes = export(schema_graphs)
    (output / 'source-schema.trig').write_bytes(schema_bytes)
    # Registry objects carry namespaces/role definitions, but no other accounts.
    ids = ' '.join(json.dumps(identity) + '^^xsd:NCName' for identity in (user, 'unknown'))
    admin_query = PREFIX + '''CONSTRUCT { ?s ?p ?o } WHERE { GRAPH oldap:admin {
      { ?s a ?kind ; ?p ?o . VALUES ?kind { oldap:Project oldap:Role oldap:AdminPermission oldap:DataPermission } }
      UNION { ?s oldap:userId ?id ; ?p ?o . VALUES ?id { ''' + ids + ''' } }
      UNION { ?u oldap:userId ?id . VALUES ?id { ''' + ids + ''' }
        << ?u ?membership ?target >> ?p ?o . BIND(<< ?u ?membership ?target >> AS ?s) }
    } }'''
    response = source.post(endpoint, data={'query': admin_query, 'infer': 'false'},
                           headers={'Accept': 'application/x-turtlestar'}, timeout=60)
    response.raise_for_status()
    admin_bytes = named_turtle_export(response.content, BASE + 'admin')
    (output / 'source-admin.trig').write_bytes(admin_bytes)
    resources = select('SELECT DISTINCT ?s ?type WHERE { GRAPH <' + namespace + 'data> { '
                       '?s a ?type . FILTER(isIRI(?s) && ?type != oldap:Dating) } } ORDER BY ?s ?type')
    iris = sorted({row['s']['value'] for row in resources})
    paths = ['/admin/project/' + args.project, '/admin/datamodel/' + args.project]
    paths += ['/data/' + args.project + '/' + quote(args.project + ':' + iri[len(namespace):]
              if iri.startswith(namespace) else iri, safe=':') for iri in iris]
    source_auth = {'admin': login(args.source_api, user, password), 'anonymous': login(args.source_api, 'unknown')}
    baseline = {actor: {path: read(args.source_api, path, auth) for path in paths}
                for actor, auth in source_auth.items()}
    (output / 'source-api.json').write_text(json.dumps(baseline, indent=2))
    namespace_response = source.get(endpoint + '/namespaces',
        headers={'Accept': 'application/sparql-results+json'}, timeout=60)
    namespace_response.raise_for_status()
    namespace_rows = namespace_response.json()['results']['bindings']
    (output / 'source-namespaces.json').write_text(json.dumps(namespace_rows, indent=2))
    # Preserve compact names actually used by the source API, without importing
    # hundreds of unused aliases or changing existing canonical prefixes.
    def used_prefixes(value):
        if isinstance(value, dict):
            return set().union(*(used_prefixes(k) | used_prefixes(v) for k, v in value.items())) if value else set()
        if isinstance(value, list):
            return set().union(*(used_prefixes(v) for v in value)) if value else set()
        if isinstance(value, str) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.-]*:[^/ :]+', value):
            return {value.split(':', 1)[0]}
        return set()
    required_prefixes = used_prefixes(baseline)

    converted = convert(output / 'source-project.trig', 'project-converted')
    admin = convert(output / 'source-admin.trig', 'admin-converted')
    print(f'Exported and converted {len(iris)} resource identities; starting owned Jena.', flush=True)
    settings = {k: v for k, v in os.environ.items() if not k.startswith(('OLDAP_', 'PROBE_'))}
    settings.update(OLDAP_BACKEND='jena', APP_ENV='Dev', UPLOAD_FOLDER=str(output / 'uploads'),
        OLDAP_AUTH_ADMIN_USER=user, OLDAP_AUTH_ADMIN_PASSWORD=password, OLDAP_REFRESH_COOKIE_SECURE='false',
        OLDAP_REDIS_URL='redis://127.0.0.1:1/0', OLDAP_STAGING_LOCK_REDIS_URL='redis://127.0.0.1:1/1')
    for key in ('JENA_SERVICE_KEY', 'JENA_BOOTSTRAP_KEY', 'JENA_FULLTEXT_KEY', 'JENA_IDENTITY_KEY',
                'MEDIA_JWT_SECRET', 'ACCESS_JWT_SECRET', 'REFRESH_JWT_SECRET'):
        settings['OLDAP_' + key] = secrets.token_urlsafe(32)
    httpd = make_server('127.0.0.1', 0, Flask('starting'), threaded=True, request_handler=QuietHandler)
    base = f'http://127.0.0.1:{httpd.server_port}'
    backend_env = dict(settings, PROBE_IDENTITY_URL=base + '/internal/jena/identity',
        PROBE_IDENTITY_SECRET=settings['OLDAP_JENA_IDENTITY_KEY'], PROBE_TRANSPORT_SECRET=settings['OLDAP_JENA_SERVICE_KEY'],
        PROBE_BOOTSTRAP_SECRET=settings['OLDAP_JENA_BOOTSTRAP_KEY'], PROBE_FULLTEXT_ADMIN_SECRET=settings['OLDAP_JENA_FULLTEXT_KEY'],
        PROBE_MANAGED_TEXT='yes', PROBE_SEED_FILES='\n'.join(map(str, [output / 'source-schema.trig', admin])))
    log = (output / 'backend.log').open('w')
    process = subprocess.Popen([args.java, '-Xmx512m', '--class-path', str(args.jar),
        str(library / 'tools/migration/FusekiSessionProbe.java'), str(output / 'dataset'), 'new', '30000'],
        cwd=library, env=backend_env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log)
    thread = None
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            if not selector.select(timeout=60):
                raise TimeoutError('Owned Fuseki did not start')
        settings['OLDAP_JENA_URL'] = f'http://127.0.0.1:{int(process.stdout.readline())}/tx'
        with ExitStack() as stack:
            _, redis_url = stack.enter_context(owned_writer_store(output, name='isolated-redis'))
            settings['OLDAP_REDIS_URL'] = redis_url.replace('?db=1', '?db=0')
            settings['OLDAP_STAGING_LOCK_REDIS_URL'] = redis_url
            stack.enter_context(patch.dict(os.environ, settings, clear=True))
            from oldap_api import create_app
            from oldap_api.backend import create_connection
            httpd.app = create_app()
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            connection = create_connection(userId=user, credentials=password, context_name="DEFAULT")
            from oldaplib.src.helpers.context import Context
            context = Context(name=connection.context_name)
            for row in namespace_rows:
                prefix, namespace = row['prefix']['value'], row['namespace']['value']
                if prefix in required_prefixes and context.get(prefix) is None:
                    context[prefix] = namespace
            connection._project_graph_import(args.project, parts, converted.read_text())
            target_auth = {'admin': login(base, user, password), 'anonymous': login(base, 'unknown')}
            target = {actor: {path: read(base, path, auth) for path in paths}
                      for actor, auth in target_auth.items()}
            (output / 'target-api.json').write_text(json.dumps(target, indent=2))
            differences = [{'actor': actor, 'path': path, 'source': baseline[actor][path], 'target': target[actor][path]}
                           for actor in baseline for path in paths if baseline[actor][path] != target[actor][path]]
            (output / 'differences.json').write_text(json.dumps(differences, indent=2))
            extra_cases = {
                'summaries': ('POST', f'/data/summaries/{args.project}', {'iris': iris,
                    'includeProperties': ['schema:name', 'schema:hasPart', args.project + ':hasKnowledgeContribution']}),
                'superclass-search': ('GET', f'/data/search/{args.project}/class/schema:Thing', None),
                'equivalent-search': ('GET', f'/data/search/{args.project}/class/foaf:Person', None),
                'inverse-search': ('POST', f'/data/search/{args.project}', {
                    'filter': [{'property': args.project + ':hasKnowledgeContribution', 'op': 'EQ', 'type': 'qname', 'value': args.project + ':Annotation_IMG_0171_2026_08_21'}],
                    'includeProperties': [args.project + ':hasKnowledgeContribution']}),
            }
            extra_results = []
            for actor in source_auth:
                for label, (method, path, body) in extra_cases.items():
                    pair = []
                    for endpoint_base, auth in [(args.source_api, source_auth[actor]), (base, target_auth[actor])]:
                        reply = requests.request(method, endpoint_base + path, json=body, headers=auth, timeout=90)
                        pair.append({'status': reply.status_code, 'body': normalized(reply.json())})
                    extra_results.append({'actor': actor, 'case': label, 'source': pair[0], 'target': pair[1],
                        'matches': pair[0] == pair[1] and pair[0]['status'] == 200})
            (output / 'extra-comparisons.json').write_text(json.dumps(extra_results, indent=2))

            if args.benchmark:
                from benchmark_project_reads import benchmark_reads
                timings = benchmark_reads(base, target_auth['admin'], settings['OLDAP_REDIS_URL'], args.project, iris)
                (output / 'timings.json').write_text(json.dumps(timings, indent=2))
                if args.scaled_benchmark:
                    from benchmark_project_reads import add_synthetic_people
                    add_synthetic_people(connection, args.project)
                    scaled = benchmark_reads(base, target_auth['admin'], settings['OLDAP_REDIS_URL'], args.project, iris)
                    (output / 'timings-scaled.json').write_text(json.dumps(scaled, indent=2))
                    from benchmark_project_reads import compare_class_cost
                    controlled = compare_class_cost(base, target_auth['admin'], args.project)
                    (output / 'timings-class-control.json').write_text(json.dumps(controlled, indent=2))

            if args.entailment_checks:
                from check_bounded_entailment import check_entailment
                entailment_checks = check_entailment(connection)
                (output / 'entailment-checks.json').write_text(json.dumps(entailment_checks, indent=2))
            # Conservative byte equality: changed serializer order also fails this guard.
            stable_export = export(graphs) == project_bytes
            admin_after = source.post(endpoint, data={'query': admin_query, 'infer': 'false'},
                headers={'Accept': 'application/x-turtlestar'}, timeout=60)
            admin_after.raise_for_status()
            stable_admin = named_turtle_export(admin_after.content, BASE + 'admin') == admin_bytes
            stable_schema = export(schema_graphs) == schema_bytes
            after = {actor: {path: read(args.source_api, path, auth) for path in paths}
                     for actor, auth in source_auth.items()}
            report = {'project': args.project, 'resourceIdentities': len(iris), 'resourceTypes': len({r['type']['value'] for r in resources}),
                'comparisons': len(paths) * len(baseline), 'differences': len(differences),
                'extraComparisons': len(extra_results), 'extraDifferences': sum(not row['matches'] for row in extra_results),
                'statusDifferences': sum(row['source']['status'] != row['target']['status'] for row in differences),
                'differenceFields': dict(Counter(key for row in differences
                    if isinstance(row['source']['body'], dict) and isinstance(row['target']['body'], dict)
                    for key in row['source']['body'].keys() | row['target']['body'].keys()
                    if row['source']['body'].get(key) != row['target']['body'].get(key))),
                'vocabularyGraphs': vocab_graphs, 'sourceSchemaBytes': len(schema_bytes),
                'targetCache': 'owned Redis, separate cache and coordination databases',
                'sourceExportByteStable': stable_export, 'sourceSchemaByteStable': stable_schema,
                'sourceApiStable': baseline == after, 'sourceAdminByteStable': stable_admin, 'sourceProjectBytes': len(project_bytes),
                'sourceProjectSha256': hashlib.sha256(project_bytes).hexdigest(),
                'statusCounts': {actor: {str(status): sum(r['status'] == status for r in replies.values())
                    for status in sorted({r['status'] for r in replies.values()})} for actor, replies in baseline.items()},
                'projectConversion': json.loads((converted.parent / 'report.json').read_text()),
                'adminConversion': json.loads((admin.parent / 'report.json').read_text())}
            (output / 'results.json').write_text(json.dumps(report, indent=2))
            print(json.dumps({k: v for k, v in report.items() if not k.endswith('Conversion')}, indent=2), flush=True)
            if differences or any(not row['matches'] for row in extra_results) or not (stable_export and stable_schema and stable_admin and baseline == after):
                raise AssertionError('Comparison or source stability check failed; inspect private artifacts')
    finally:
        if thread:
            httpd.shutdown()
            thread.join(timeout=5)
        httpd.server_close()
        process.stdin.close()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        process.stdout.close()
        log.close()
        source.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--java', required=True)
    parser.add_argument('--jar', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-config', type=Path, required=True)
    parser.add_argument('--graphdb', default='http://localhost:7200')
    parser.add_argument('--repository', default='oldap')
    parser.add_argument('--source-api', default='http://localhost:8000')
    parser.add_argument('--project', default='chama')
    parser.add_argument('--benchmark', action='store_true')
    parser.add_argument('--entailment-checks', action='store_true')
    parser.add_argument('--scaled-benchmark', action='store_true')
    run(parser.parse_args())
