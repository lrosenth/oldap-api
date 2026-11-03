"""Native project transfer acceptance on owned Jena data and isolated Redis."""
import os
from pathlib import Path
import subprocess
from unittest.mock import patch

from check_archive_writes import owned_writer_store
from oldaplib.src.helpers.oldaperror import OldapError
from oldaplib.src.resource_transaction import resource_transaction


def check_project_transfer(call, check, create_connection, output):
    """Exercise real CLI gzip round-trip, RDF 1.2 identity and atomic refusal."""
    admin = create_connection(userId='actor', credentials='owned-fixture-password')
    writer = create_connection(userId='writer', credentials='owned-writer-password')
    prefix = 'PREFIX p: <https://example.org/transfer/> PREFIX oldap: <http://oldap.org/base#> PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> '
    admin.update_query(prefix + '''INSERT DATA { GRAPH oldap:admin {
        <https://example.org/project/transfer> a oldap:Project ; oldap:projectShortName "transfer"^^<http://www.w3.org/2001/XMLSchema#NCName> ;
            oldap:namespaceIri <https://example.org/transfer/> . }
        GRAPH p:data { p:item p:label "Grüezi"@de ; p:link _:shared ; oldap:attachedToRole p:Reader .
            _:grant rdf:reifies <<( p:item oldap:attachedToRole p:Reader )>> ; oldap:hasDataPermission oldap:DATA_VIEW . }
        GRAPH p:lists { _:shared p:value "same node" . }
        GRAPH p:onto { p:Type a <http://www.w3.org/2002/07/owl#Class> . }
        GRAPH p:shacl { p:Shape a <http://www.w3.org/ns/shacl#NodeShape> . } }''')
    parts = ['data', 'lists', 'onto', 'shacl']
    dump = admin._project_graph_export('transfer', parts)
    check('Native project export includes RDF 1.2 reification without administrative graphs',
          'reifies' in dump and 'Grüezi' in dump and 'http://oldap.org/base#admin' not in dump)
    for operation in (lambda: writer._project_graph_export('transfer', parts),
                      lambda: writer._project_graph_import('transfer', parts, dump)):
        try:
            operation()
        except OldapError:
            pass
        else:
            raise AssertionError('Non-root raw transfer was accepted')
    check('Raw export and import reject ordinary project writers', True)
    tools_cli = Path(__file__).resolve().parents[3] / 'oldap-tools/.venv/bin/oldap-tools'
    file = output / 'transfer.trig.gz'
    with owned_writer_store(output, name='project-transfer-redis') as (_, url), patch.dict(os.environ, {
            'OLDAP_REDIS_URL': url.replace('?db=1', '?db=0'), 'OLDAP_STAGING_LOCK_REDIS_URL': url}):
        def cli(*args):
            result = subprocess.run([str(tools_cli), '--user', 'actor', '--password', 'owned-fixture-password',
                'project', *map(str, args)], capture_output=True, text=True, timeout=90)
            (output / 'transfer-tools.log').write_text(result.stdout + result.stderr)
            if result.returncode:
                raise AssertionError('Project CLI failed; inspect transfer-tools.log')
        cli('dump', 'transfer', '--no-admin', '--out', file)
        admin.update_query(prefix + ' ; '.join('CLEAR GRAPH p:' + part for part in parts))
        cli('load', '--inf', file)
    check('Real project dump/load CLI restores gzip RDF 1.2 across four graphs', admin.query(prefix + '''ASK {
        GRAPH p:data { p:item p:label "Grüezi"@de ; p:link ?node ; oldap:attachedToRole p:Reader .
            ?grant rdf:reifies <<( p:item oldap:attachedToRole p:Reader )>> ; oldap:hasDataPermission oldap:DATA_VIEW . }
        GRAPH p:lists { ?node p:value "same node" }
        GRAPH p:onto { p:Type a <http://www.w3.org/2002/07/owl#Class> }
        GRAPH p:shacl { p:Shape a <http://www.w3.org/ns/shacl#NodeShape> }
    }''')['boolean'])
    try:
        with resource_transaction(admin):
            admin._project_graph_import('transfer', ['data'], prefix + 'p:data { p:rollback p:value "pending" }')
            check('Joined import is visible inside its owning transaction',
                  'pending' in admin._project_graph_export('transfer', ['data']))
            raise RuntimeError('owned rollback')
    except RuntimeError:
        pass
    check('Outer rollback removes the complete imported payload',
          not admin.query(prefix + 'ASK { GRAPH p:data { p:rollback ?p ?o } }')['boolean'])
    for body in (prefix + 'p:data { p:invalid p:value "partial" } p:lists { p:invalid p:value "foreign" }',
                 prefix + 'p:data { p:invalid p:value "partial" . BROKEN',
                 prefix + 'p:invalid p:value "default" .',
                 prefix + '<urn:probe:http-commits> { p:invalid p:value "reserved" }'):
        try:
            admin._project_graph_import('transfer', ['data'], body)
        except OldapError:
            pass
        else:
            raise AssertionError('Invalid transfer accepted')
    check('Malformed, out-of-scope, default and reserved graphs leave no partial writes',
          not admin.query(prefix + 'ASK { GRAPH p:data { p:invalid ?p ?o } }')['boolean'])
    # Native quad insertion must use the managed dataset, not bypass its index.
    call('PUT', '/data/demo/demo:IndexedRecord', {'iri': 'transferindex', 'demo:body': 'transfer body',
        'oldap:attachedToRole': {'demo:Writer': 'DATA_VIEW'}})
    text = 'PREFIX demo: <https://example.org/demo/> demo:data { demo:transferindex demo:caption "transfernativeword" }'
    admin._project_graph_import('demo', ['data'], text)
    def search(word):
        return call('POST', '/data/search/demo', {'ftfilter': [{'field': 'caption', 'query': word}]}).json()
    check('Native import updates the existing managed fulltext index', len(search('transfernativeword')) == 1)
    try:
        with resource_transaction(admin):
            admin.transaction_update('PREFIX demo: <https://example.org/demo/> DELETE DATA { GRAPH demo:data { demo:transferindex demo:caption "transfernativeword" } }')
            admin._project_graph_import('demo', ['data'], text.replace('transfernativeword', 'transferabortedword'))
            raise RuntimeError('owned indexed rollback')
    except RuntimeError:
        pass
    check('Aborted native import restores both RDF and indexed text',
          len(search('transfernativeword')) == 1 and search('transferabortedword') == [])
    admin.update_query(prefix + 'DELETE DATA { GRAPH oldap:admin { <https://example.org/actor> oldap:inProject oldap:SystemProject } }')
    try:
        admin._project_graph_export('transfer', parts)
    except OldapError:
        check('Raw export rechecks current asserted root membership', True)
    else:
        raise AssertionError('Stale root context authorized transfer')
    finally:
        admin.update_query(prefix + 'INSERT DATA { GRAPH oldap:admin { <https://example.org/actor> oldap:inProject oldap:SystemProject } }')
