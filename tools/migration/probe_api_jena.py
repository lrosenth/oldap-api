"""Run normal create_app/backend selection and real model/list API writes on owned Jena.

No Connection factory is mocked. Redis object-cache I/O is suppressed unless --cache-only selects owned real Redis.
All HTTP listeners, JWT keys, users and RDF data belong to this acceptance run.
"""
import argparse
from contextlib import ExitStack, contextmanager
import json
import os
from pathlib import Path
import secrets
import selectors
import subprocess
import sys
import threading
import zipfile
from unittest.mock import patch

import bcrypt
import requests
from flask import Flask
from werkzeug.serving import make_server, WSGIRequestHandler
from oldaplib.src.cachesingleton import CacheSingletonRedis


class QuietHandler(WSGIRequestHandler):
    def log(self, *args, **kwargs):
        pass



@contextmanager
def owned_identity_verifier(settings, output):
    """Run the real identity blueprint in an independent disposable process.

    Match the deployed callback isolation: model reads in the API must not
    compete with token verification in the same Python worker. Only synthetic
    access-verification settings are passed; no database credentials are needed.
    The child binds an OS-selected loopback port and is stopped on every exit.
    """
    code = """
from flask import Flask
from werkzeug.serving import make_server, WSGIRequestHandler
from oldap_api.views.jena_identity_views import jena_identity_bp
class Quiet(WSGIRequestHandler):
    def log(self, *args, **kwargs): pass
app = Flask('owned-identity')
app.register_blueprint(jena_identity_bp)
server = make_server('127.0.0.1', 0, app, threaded=True, request_handler=Quiet)
print(server.server_port, flush=True)
server.serve_forever()
"""
    environment = {key: value for key, value in settings.items()
                   if not key.startswith('OLDAP_')}
    for key in ('OLDAP_BACKEND', 'OLDAP_JENA_IDENTITY_KEY', 'OLDAP_ACCESS_JWT_SECRET'):
        environment[key] = settings[key]
    with (output / 'identity.log').open('w') as log:
        process = subprocess.Popen([sys.executable, '-u', '-c', code],
            cwd=Path(__file__).resolve().parents[2], env=environment,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=log)
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                if not selector.select(timeout=15):
                    raise TimeoutError('Owned identity verifier did not start')
            port = int(process.stdout.readline())
            if not 0 < port < 65536 or process.poll() is not None:
                raise RuntimeError('Owned identity verifier is unavailable')
            yield f'http://127.0.0.1:{port}/internal/jena/identity'
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            process.stdout.close()


def run(java, jar, output, *, fasnacht_only=False, fasnacht_export=None, profile_parts=False, cache_only=False, browser_preview=False, media_root=None, asset_service_root=None, fulltext_preview=False, java_heap_mb=512):
    """Run disposable API acceptance with an explicit server heap ceiling.

    Args:
        java_heap_mb: Maximum heap in MiB for the owned Fuseki Java process.
            The default preserves earlier probes; conversion subprocesses and
            existing/shared services are unaffected. This sets Xmx, not Xms.

    Raises:
        ValueError: If the heap limit is not positive.
    """
    if java_heap_mb <= 0:
        raise ValueError("Java heap must be positive (MiB)")
    os.umask(0o077)
    output.mkdir(parents=True, exist_ok=False)
    library = Path(__file__).resolve().parents[3] / 'oldaplib'
    password = 'owned-fixture-password'
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode()
    fixture = output / 'admin.trig'
    fixture.write_text('''@prefix oldap: <http://oldap.org/base#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix schema: <https://schema.org/> .
@prefix dcterms: <http://purl.org/dc/terms/> .
oldap:admin {
 oldap:DATA_RESTRICTED oldap:permissionValue 1 .
 oldap:DATA_VIEW oldap:permissionValue 2 .
 oldap:DATA_EXTEND oldap:permissionValue 3 .
 oldap:DATA_UPDATE oldap:permissionValue 4 .
 oldap:DATA_DELETE oldap:permissionValue 5 .
 oldap:DATA_PERMISSIONS oldap:permissionValue 6 .
 oldap:SystemProject a oldap:Project ; oldap:projectShortName "oldap"^^xsd:NCName ;
    oldap:namespaceIri <http://oldap.org/base#> ; oldap:projectStart "2024-01-01"^^xsd:date .
 oldap:SharedProject a oldap:Project ; oldap:projectShortName "shared"^^xsd:NCName ;
    oldap:namespaceIri <http://oldap.org/shared#> ; oldap:projectStart "2024-01-01"^^xsd:date .
 <https://example.org/project/demo> a oldap:Project ; oldap:projectShortName "demo"^^xsd:NCName ;
    oldap:namespaceIri <https://example.org/demo/> ; oldap:projectStart "2024-01-01"^^xsd:date .
 <https://example.org/actor> a oldap:User ; oldap:userId "actor"^^xsd:NCName ;
    dcterms:creator <https://example.org/actor> ; schema:familyName "Probe" ; schema:givenName "Actor" ;
    schema:email "actor@example.org" ; oldap:credentials "''' + hashed + '''" ; oldap:isActive true ;
    oldap:inProject oldap:SystemProject .
 <https://example.org/rootgrant> rdf:reifies <<( <https://example.org/actor> oldap:inProject oldap:SystemProject )>> ;
    oldap:hasAdminPermission oldap:ADMIN_OLDAP .
 <https://example.org/unknown> a oldap:User ; oldap:userId "unknown"^^xsd:NCName ;
    dcterms:creator <https://example.org/actor> ; schema:familyName "Probe" ; schema:givenName "Unknown" ;
    schema:email "unknown@example.org" ; oldap:credentials "unused" ; oldap:isActive true .
}
''')
    settings = {k: v for k, v in os.environ.items() if not k.startswith(('OLDAP_', 'PROBE_'))}
    settings.update(OLDAP_BACKEND='jena', APP_ENV='Dev', UPLOAD_FOLDER=str(output / 'uploads'),
        OLDAP_JENA_SERVICE_KEY=secrets.token_urlsafe(32), OLDAP_JENA_BOOTSTRAP_KEY=secrets.token_urlsafe(32),
        OLDAP_JENA_FULLTEXT_KEY=secrets.token_urlsafe(32), OLDAP_JENA_IDENTITY_KEY=secrets.token_urlsafe(32),
        OLDAP_MEDIA_JWT_SECRET=secrets.token_urlsafe(32), OLDAP_ACCESS_JWT_SECRET=secrets.token_urlsafe(32), OLDAP_REFRESH_JWT_SECRET=secrets.token_urlsafe(32),
        OLDAP_AUTH_ADMIN_USER='actor', OLDAP_AUTH_ADMIN_PASSWORD=password, OLDAP_REFRESH_COOKIE_SECURE='false',
        OLDAP_REDIS_URL='redis://127.0.0.1:1/0', OLDAP_STAGING_LOCK_REDIS_URL='redis://127.0.0.1:1/1')
    if browser_preview:
        settings['OLDAP_AUTH_ALLOWED_ORIGINS'] = 'http://127.0.0.1:5179'
    with owned_identity_verifier(settings, output) as identity_url:
        httpd = make_server('127.0.0.1', 0, Flask('starting'), threaded=True, request_handler=QuietHandler)
        base = f'http://127.0.0.1:{httpd.server_port}'
        backend_environment = dict(settings, PROBE_IDENTITY_URL=identity_url,
            PROBE_IDENTITY_SECRET=settings['OLDAP_JENA_IDENTITY_KEY'], PROBE_TRANSPORT_SECRET=settings['OLDAP_JENA_SERVICE_KEY'],
            PROBE_BOOTSTRAP_SECRET=settings['OLDAP_JENA_BOOTSTRAP_KEY'], PROBE_FULLTEXT_ADMIN_SECRET=settings['OLDAP_JENA_FULLTEXT_KEY'],
            PROBE_MANAGED_TEXT='yes', PROBE_SEED_FILES='\n'.join(map(str, [library / 'oldaplib/ontologies/oldap.trig',
            library / 'oldaplib/ontologies/shared.trig', fixture])))
        if fasnacht_export is not None:
            from prepare_fasnacht_export import prepare_export
            seed = prepare_export(fasnacht_export, output, library, java, jar)
            backend_environment['PROBE_SEED_FILES'] += '\n' + str(seed)
        log = (output / 'backend.log').open('a')
        process = subprocess.Popen([java, f'-Xmx{java_heap_mb}m', '--class-path', str(jar),
            str(library / 'tools/migration/FusekiSessionProbe.java'), str(output / 'dataset'), 'new', '30000'],
            env=backend_environment, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log)
        (output / 'java-process.json').write_text(json.dumps({'pid': process.pid, 'maximum_heap_mib': java_heap_mb}) + '\n')
        thread = None
        checks = []
        client = requests.Session()

        def check(name, condition):
            if not condition:
                raise AssertionError(name)
            checks.append(name)
            print('PASS', name, flush=True)

        def call(method, path, body=None, status=200, headers=None):
            response = client.request(method, base + path, json=body, timeout=60, headers=headers)
            if response.status_code != status:
                raise AssertionError(f'{method} {path}: HTTP {response.status_code}: {response.text[:1500]}')
            return response

        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                if not selector.select(timeout=30):
                    raise TimeoutError('Owned Fuseki did not start')
            port = int(process.stdout.readline())
            settings['OLDAP_JENA_URL'] = f'http://127.0.0.1:{port}/tx'
            with ExitStack() as stack:
                if cache_only or browser_preview:
                    from check_archive_writes import owned_writer_store
                    _, writer_url = stack.enter_context(owned_writer_store(output, name='cache-redis'))
                    settings['OLDAP_REDIS_URL'] = writer_url.replace('?db=1', '?db=0')
                    settings['OLDAP_STAGING_LOCK_REDIS_URL'] = writer_url
                stack.enter_context(patch.dict(os.environ, settings, clear=True))
                if not (cache_only or browser_preview):
                    for method in ('__init__', 'get', 'set', 'delete'):
                        stack.enter_context(patch.object(CacheSingletonRedis, method, return_value=None))
                from oldap_api import create_app
                from oldap_api.backend import create_connection
                from oldaplib.src.jena_connection import JenaConnection
                app = create_app()
                httpd.app = app
                thread = threading.Thread(target=httpd.serve_forever, daemon=True)
                thread.start()
                check('Regular API startup selects Jena and bootstraps namespaces', isinstance(create_connection(), JenaConnection))
                check('Health reports Jena without contacting GraphDB', call('GET', '/health').json()['services'] == {'jena': 'reachable'})
                call('POST', '/internal/jena/identity', {'token': 'invalid'}, status=401)
                check('Private identity verification requires its service credential', True)
                call('POST', '/admin/auth/actor', {'password': 'wrong'}, status=403)
                login = call('POST', '/admin/auth/actor', {'password': password}).json()
                client.headers['Authorization'] = 'Bearer ' + login['accessToken']
                check('Refresh cookie reloads user permissions through Jena', call('POST', '/admin/auth/refresh').status_code == 200)
                check('Existing credential login issues a token accepted by the Jena service', call('GET', '/admin/project/demo').status_code == 200)
                if cache_only:
                    from check_cache_reads import check_cache_reads
                    check_cache_reads(call, check, create_connection, output, base)
                    (output / 'results.json').write_text(json.dumps({'status': 'passed', 'checks': checks}, indent=2) + '\n')
                    return
                if fasnacht_only:
                    from check_fasnacht_model import check_fasnacht_model
                    check_fasnacht_model(call, check, create_connection, base, password, output, real_export=fasnacht_export is not None)
                    if browser_preview:
                        from hold_browser_preview import hold_browser_preview
                        hold_browser_preview(call, create_connection, base, output, login['accessToken'], media_root=media_root, asset_service_root=asset_service_root, fulltext_preview=fulltext_preview)
                    if profile_parts:
                        from profile_parts_search import profile_parts_search
                        profile_parts_search(call, check, output)
                    (output / 'results.json').write_text(json.dumps({'status': 'passed', 'checks': checks}, indent=2) + '\n')
                    return
                call('PUT', '/admin/datamodel/demo')
                check('Existing API creates an empty model through real Jena transactions', call('GET', '/admin/datamodel/demo').json()['project'] == 'demo')
                call('PUT', '/admin/datamodel/demo/demo:Book', {'label': ['Book@en'], 'properties': [
                    {'iri': 'demo:title', 'datatype': 'xsd:string', 'name': ['Title@en'], 'maxCount': 1}]})
                model = call('GET', '/admin/datamodel/demo').json()
                check('Resource class and property read back through the regular API', any(r['iri'] == 'demo:Book' for r in model['resources']))
                call('POST', '/admin/datamodel/demo/demo:Book', {'label': ['Changed book@en']})
                check('Model update succeeds with optimistic timestamp checks', 'Changed book@en' in json.dumps(call('GET', '/admin/datamodel/demo').json()))
                call('POST', '/admin/datamodel/demo/demo:Book/demo:title', {'maxCount': 2})
                check('Property modification persists through Jena', any(prop.get('maxCount') == 2 for resource in call('GET', '/admin/datamodel/demo').json()['resources'] for prop in resource['properties']))
                call('PUT', '/admin/hlist/demo/Topics', {'prefLabel': ['Topics@en']})
                check('Hierarchical list creation reads back', call('GET', '/admin/hlist/demo/Topics').status_code == 200)
                call('PUT', '/admin/hlist/demo/Topics/root', {'prefLabel': ['Root@en'], 'position': 'root'})
                call('PUT', '/admin/hlist/demo/Topics/child', {'prefLabel': ['Child@en'], 'position': 'belowOf', 'refnode': 'root'})
                check('Real list root and child insertion preserve readable nodes', call('GET', '/admin/hlist/demo/Topics/child').status_code == 200)
                call('POST', '/admin/hlist/demo/Topics/child', {'prefLabel': ['Changed child@en']})
                check('List node update is visible', 'Changed child' in call('GET', '/admin/hlist/demo/Topics/child').text)
                call('PUT', '/admin/hlist/demo/Topics/second', {'prefLabel': ['Second@en'], 'position': 'rightOf', 'refnode': 'child'})
                for direction, reference in [('rightOf', 'second'), ('leftOf', 'second'), ('belowOf', 'second'), ('belowOf', 'root')]:
                    call('POST', '/admin/hlist/demo/Topics/child/move', {direction: reference})
                    check(f'List move {direction} {reference} succeeds', call('GET', '/admin/hlist/demo/Topics/child').status_code == 200)
                    bounds = create_connection(userId='actor', credentials=password).query(
                        'SELECT ?node ?left ?right WHERE { GRAPH <https://example.org/demo/lists> {'
                        ' ?node <http://oldap.org/base#leftIndex> ?left; <http://oldap.org/base#rightIndex> ?right }}')['results']['bindings']
                    indices = sorted(int(row[side]['value']) for row in bounds for side in ('left', 'right'))
                    check(f'List indices remain unique and contiguous after {direction} {reference}',
                          len(bounds) == 3 and indices == list(range(1, 7)) and
                          all(int(row['left']['value']) < int(row['right']['value']) for row in bounds))
                    expected = {('rightOf', 'second'): (4, 5), ('leftOf', 'second'): (2, 3),
                                ('belowOf', 'second'): (3, 4), ('belowOf', 'root'): (4, 5)}
                    child = next(row for row in bounds if row['node']['value'].endswith('child'))
                    check(f'Child occupies the requested position after {direction} {reference}',
                          tuple(int(child[side]['value']) for side in ('left', 'right')) == expected[(direction, reference)])
                call('POST', '/admin/hlist/demo/Topics/root/move', {'belowOf': 'child'}, status=409)
                check('Invalid descendant move rolls back and releases its transaction', True)
                call('DELETE', '/admin/hlist/demo/Topics/second')
                call('DELETE', '/admin/hlist/demo/Topics/child')
                call('GET', '/admin/hlist/demo/Topics/child', status=404)
                check('List node deletion persists', True)
                call('DELETE', '/admin/hlist/demo/Topics/root')
                call('DELETE', '/admin/hlist/demo/Topics')
                check('Empty list deletion succeeds', True)
                state = call('GET', '/admin/fulltext/demo').json()
                active = call('PUT', '/admin/fulltext/demo', {'configuration': {'graph': 'https://example.org/demo/data',
                    'fields': {'title': ['https://example.org/demo/title']}}, 'expectedRevision': state['revision']}).json()
                check('Managed fulltext works without replacing the API Connection factory', active['status'] == 'active')
                call('DELETE', '/admin/datamodel/demo/demo:Book/demo:title')
                call('DELETE', '/admin/datamodel/demo/demo:Book')
                call('DELETE', '/admin/datamodel/demo')
                check('Property, class and whole-model deletion complete over Jena', True)
                # Exercise the real tools CLI in its own environment, including the
                # field-map activation that must run after successful model writes.
                tools_cli = library.parent / 'oldap-tools/.venv/bin/oldap-tools'
                ontology = {'ontology': {'project': {'shortname': 'demo', 'namespace': 'https://example.org/demo/'},
                    'classes': {'demo:Note': {'label': {'en': 'Note'}, 'properties': [
                        {'iri': 'demo:text', 'datatype': 'xsd:string', 'name': {'en': 'Text'}, 'max_count': 1}]}},
                    'fulltext': {'fields': {'title': ['demo:text']}}}}
                source = output / 'ontology.yaml'
                source.write_text(json.dumps(ontology))

                def tools_command(*arguments):
                    result = subprocess.run([str(tools_cli), '--api', base, '--user', 'actor', '--password', password,
                        'ontology', *map(str, arguments)], capture_output=True, text=True, timeout=90)
                    with (output / 'tools.log').open('a') as tool_log:
                        tool_log.write(result.stdout + result.stderr)
                    if result.returncode:
                        raise AssertionError('Tools CLI failed; inspect owned tools.log')
                    return result.stdout

                tools_command('load', '-i', source, '--fulltext', 'apply', '--backup-out', output / 'before.zip')
                check('Real tools import creates model and activates its field map',
                      call('GET', '/admin/fulltext/demo').json()['configuration']['fields'] == {'title': ['https://example.org/demo/text']})
                ontology['ontology']['classes']['demo:Note']['label'] = {'en': 'Updated note'}
                source.write_text(json.dumps(ontology))
                tools_command('load', '-i', source, '--fulltext', 'apply', '--backup-out', output / 'existing.zip')
                with zipfile.ZipFile(output / 'existing.zip') as backup:
                    check('Tools backup includes previous fulltext configuration',
                          json.loads(backup.read('fulltext.json'))['configuration']['fields'] ==
                          {'title': ['https://example.org/demo/text']})
                replay = tools_command('load', '-i', source, '--fulltext', 'apply', '--dry-run')
                check('Unchanged tools import plans no writes', 'Planned 0' in replay)
                exported = output / 'exported.yaml'
                tools_command('dump', 'demo', '--search-backend', 'jena', '--out', exported)
                replay = tools_command('load', '-i', exported, '--fulltext', 'apply', '--dry-run')
                check('Tools Jena dump round-trips without writes', 'Planned 0' in replay)
                from check_user_writes import check_user_writes
                check_user_writes(call, check, create_connection)
                from check_resource_writes import check_resource_writes
                check_resource_writes(call, check, create_connection)
                from check_archive_assignment import check_archive_assignment
                check_archive_assignment(call, check, create_connection, tools_command, output)
                from check_fulltext_writes import check_fulltext_writes
                check_fulltext_writes(call, check, create_connection)
                from check_bulk_reads import check_bulk_reads
                check_bulk_reads(call, check, create_connection)
                from check_publication import check_publication
                check_publication(call, check, create_connection)
                from check_archive_reads import check_archive_reads
                check_archive_reads(call, check, create_connection)
                from check_archive_writes import check_archive_writes
                check_archive_writes(call, check, create_connection, output)
                from check_media_inventory import check_media_inventory
                check_media_inventory(call, check, create_connection, output)
                from check_project_transfer import check_project_transfer
                check_project_transfer(call, check, create_connection, output)
                (output / 'results.json').write_text(json.dumps({'status': 'passed', 'checks': checks}, indent=2) + '\n')
        finally:
            client.close()
            if thread is not None:
                httpd.shutdown()
                thread.join(timeout=10)
            httpd.server_close()
            if process.poll() is None:
                process.stdin.close()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            process.stdout.close()
            log.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--java', required=True)
    parser.add_argument('--java-heap-mb', type=int, default=512, help='Maximum owned Java heap in MiB; default 512, use 8192 for 8 GiB')
    parser.add_argument('--jar', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--fasnacht-only', action='store_true', help='Run complete Fasnacht model/parts acceptance on the owned target')
    parser.add_argument('--fasnacht-export', type=Path, help='Private legacy export for --fasnacht-only instance rehearsal')
    parser.add_argument('--profile-parts', action='store_true', help='Diagnostic query controls after real-export rehearsal')
    parser.add_argument('--cache-only', action='store_true', help='Check search/detail authorization with isolated real Redis')
    parser.add_argument('--browser-preview', action='store_true', help='Keep real-export target with owned Redis alive for browser acceptance')
    parser.add_argument('--media-root', type=Path, help='Copy one real image into owned SIPI for --browser-preview')
    parser.add_argument('--asset-service-root', type=Path, help='Media service repository for owned PDF/original browser acceptance')
    parser.add_argument('--fulltext-preview', action='store_true', help='Activate YAML fields and exercise real-export fulltext before browser preview')
    args = parser.parse_args()
    if args.fulltext_preview and not args.browser_preview:
        parser.error('--fulltext-preview requires --browser-preview')
    if args.asset_service_root and not args.media_root:
        parser.error('--asset-service-root requires --media-root')
    if args.media_root and not args.browser_preview:
        parser.error('--media-root requires --browser-preview')
    if args.browser_preview and (not args.fasnacht_export or args.cache_only):
        parser.error('--browser-preview requires --fasnacht-export and excludes --cache-only')
    if args.cache_only and (args.fasnacht_only or args.fasnacht_export or args.profile_parts):
        parser.error('--cache-only is a separate focused fixture')
    if args.profile_parts and not args.fasnacht_export:
        parser.error('--profile-parts requires --fasnacht-export')
    if args.fasnacht_export and not args.fasnacht_only:
        parser.error('--fasnacht-export requires --fasnacht-only')
    run(args.java, args.jar, args.output.resolve(), fasnacht_only=args.fasnacht_only, fasnacht_export=args.fasnacht_export, profile_parts=args.profile_parts, cache_only=args.cache_only, browser_preview=args.browser_preview, media_root=args.media_root, asset_service_root=args.asset_service_root, fulltext_preview=args.fulltext_preview, java_heap_mb=args.java_heap_mb)
