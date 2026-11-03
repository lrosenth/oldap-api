"""Owned durable Redis plus real policy-file/HTTP archive adoption acceptance."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from unittest.mock import patch
from uuid import uuid4

from redis import Redis
from redis.exceptions import RedisError
from oldaplib.src.archive_adoption import ArchiveAdoption
from oldaplib.src.archive_policy import ArchiveConflict
from oldaplib.src.mutation_gate import GATE_KEY
from oldaplib.src.objectfactory import ResourceInstanceFactory
from oldaplib.src.resource_transaction import resource_transaction
from oldaplib.src.xsd.iri import Iri


@contextmanager
def owned_writer_store(output, *, name="archive-writer-redis"):
    """Own a socket-only Redis with acknowledged AOF durability; preserve its log."""
    executable = shutil.which('redis-server')
    if not executable:
        raise RuntimeError('redis-server is required for owned coordination acceptance')
    directory = output / name
    directory.mkdir(mode=0o700)
    with tempfile.TemporaryDirectory(prefix='oldap-archive-', dir='/tmp') as temp, (directory / 'redis.log').open('w') as log:
        socket = str(Path(temp) / 'redis.sock')
        process = subprocess.Popen([executable, '--port', '0', '--unixsocket', socket, '--unixsocketperm', '700',
            '--dir', str(directory), '--appendonly', 'yes', '--appendfsync', 'always',
            '--maxmemory-policy', 'noeviction', '--save', ''], stdout=log, stderr=log)
        client = Redis(unix_socket_path=socket, decode_responses=True, socket_timeout=5)
        try:
            for _ in range(150):
                if process.poll() is not None:
                    raise RuntimeError('Owned Redis exited')
                try:
                    if client.ping():
                        break
                except (OSError, RedisError):
                    pass
                time.sleep(.02)
            else:
                raise RuntimeError('Owned Redis readiness timeout')
            yield client, 'unix://' + socket + '?db=1'
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
            client.close()


def check_archive_writes(call, check, create_connection, output):
    """Commit adoption with audit/receipt, reject stale replay and roll back all effects."""
    base = 'https://example.org/demo/'
    # The regular API updates ADMIN_CREATE; data and structure permissions are
    # still required independently by preflight and every actual mutation.
    call('POST', '/admin/user/writer', {'inProjects': [{'project': 'https://example.org/project/demo',
        'permissions': ['ADMIN_CREATE']}]})
    token = call('POST', '/admin/auth/writer', {'password': 'owned-writer-password'}).json()['accessToken']
    headers = {'Authorization': 'Bearer ' + token}
    policy_file = output / 'archive-policy.json'
    policy_file.write_text(json.dumps({'projects': {'demo': {'enabled': True,
        'structureEditorRoleIris': [base + 'Writer'], 'archiveEditorRoleIris': [base + 'Writer'],
        'cataloguedMediaClassIris': ['http://oldap.org/shared#MediaObject'],
        'preparationNotePropertyIri': base + 'body'}}}))
    with owned_writer_store(output) as (_, url), patch.dict(os.environ, {
            'OLDAP_STAGING_LOCK_REDIS_URL': url, 'OLDAP_ARCHIVE_POLICY_FILE': str(policy_file)}):
        gate = Redis.from_url(url, decode_responses=True)
        try:
            admin = create_connection(userId='actor', credentials='owned-fixture-password')
            con = create_connection(userId='writer', credentials='owned-writer-password')
            factory = ResourceInstanceFactory(admin, 'demo')
            Area = factory.createObjectInstance('shared:StagingArea')
            Folder = factory.createObjectInstance('shared:StagingFolder')
            grants = {'demo:Writer': 'DATA_UPDATE'}
            Area(iri=Iri('demo:writearea'), **{'schema:name': 'Owned write area', 'shared:mediaPath': '/owned/not-used',
                'shared:stagingDefaultRole': 'demo:Writer', 'shared:stagingQuotaBytes': 1024,
                'oldap:attachedToRole': grants}).create()
            for name, label, parent in [('writetop', 'top', None), ('writesource', 'Source', 'writetop'),
                                        ('writeleaf', 'Leaf', 'writesource')]:
                values = {'schema:name': label, 'shared:inStagingArea': 'demo:writearea',
                          'oldap:attachedToRole': grants}
                if parent:
                    values['shared:inStagingFolder'] = 'demo:' + parent
                Folder(iri=Iri('demo:' + name), **values).create()
            check('Real policy-file loading and durable coordination allow staging fixture writes', gate.get(GATE_KEY) is None)
            try:
                Folder(iri=Iri('demo:duplicateleafe'), **{'schema:name': 'Leaf',
                    'shared:inStagingArea': 'demo:writearea', 'shared:inStagingFolder': 'demo:writesource',
                    'oldap:attachedToRole': grants}).create()
            except ArchiveConflict:
                pass
            else:
                raise AssertionError('Expected duplicate sibling rejection')
            check('Scoped schema query rejects a duplicate sibling before creating it', gate.get(GATE_KEY) is None)
            path = '/archive/demo/structure/'

            def prepare(source='writesource', *, apply_mappings=True):
                proposal = call('POST', path + 'proposal', {'sourceFolderIri': base + source}, headers=headers).json()
                plan = proposal['suggestedPlan']
                if not apply_mappings:
                    plan['applyMappings'] = False
                preflight = call('POST', path + 'preflight', {'plan': plan}, headers=headers).json()
                return {'plan': plan, 'reviewDigest': preflight['reviewDigest'], 'confirm': True}

            def records(operation):
                rows = admin.query('SELECT ?record WHERE { GRAPH <urn:oldap:archive-operations> { '
                    '?s <urn:oldap:archive:record> ?record } }')['results']['bindings']
                return [record for row in rows if (record := json.loads(row['record']['value'])).get('operationId',
                    record.get('result', {}).get('operationId')) == operation]

            prefix = ArchiveAdoption(con, 'demo')._policy().context.sparql_context
            admin.update_query(prefix + 'INSERT DATA { GRAPH demo:data { '
                '<urn:owned:orphan-source-grant> rdf:reifies <<( demo:writeleaf oldap:attachedToRole demo:Public )>> ; '
                'oldap:hasDataPermission oldap:DATA_VIEW . } }')
            request = prepare()
            operation = str(uuid4())
            response = call('POST', path + 'apply', request, headers={**headers, 'Idempotency-Key': operation}).json()
            units = response['createdUnits']
            check('HTTP adoption commits parent and child units plus folder mappings',
                  response['state'] == 'committed' and len(units) == 2 and len(response['mappings']) == 2)
            mapped = {row['folderIri']: row['targetIri'] for row in response['mappings']}
            prefix = ArchiveAdoption(con, 'demo')._policy().context.sparql_context
            check('Committed RDF contains parent links, mappings and inherited writer grants', admin.query(prefix + f"""ASK {{ GRAPH demo:data {{
                <{mapped[base + 'writeleaf']}> shared:parentArchiveUnit <{mapped[base + 'writesource']}> .
                demo:writeleaf shared:defaultArchiveUnit <{mapped[base + 'writeleaf']}> .
                demo:writesource shared:defaultArchiveUnit <{mapped[base + 'writesource']}> .
                ?grant rdf:reifies <<( <{mapped[base + 'writeleaf']}> oldap:attachedToRole demo:Writer )>> ; oldap:hasDataPermission oldap:DATA_UPDATE .
            }} }}""")['boolean'])
            check('Adoption does not revive orphaned source grants on created units',
                  not admin.query(prefix + 'ASK { GRAPH demo:data { VALUES ?s { ' +
                    ' '.join('<' + row['iri'] + '>' for row in units) + ' } ?s oldap:attachedToRole demo:Public } }')['boolean'])
            journal = records(operation)
            check('Adoption commits structural audit and receipt together',
                  len(journal) == 5 and sum(row.get('command') == 'structure-apply' for row in journal) == 1)
            check('Confirmed adoption releases durable writer ownership', gate.get(GATE_KEY) is None)
            replay = call('POST', path + 'apply', request, headers={**headers, 'Idempotency-Key': operation}).json()
            check('Exact HTTP retry returns the same receipt without new audit or units', replay == response and records(operation) == journal)
            changed = {**request, 'plan': {**request['plan'], 'applyMappings': False}}
            call('POST', path + 'apply', changed, headers={**headers, 'Idempotency-Key': operation}, status=409)
            check('Changed operation-ID reuse is rejected and releases the gate', gate.get(GATE_KEY) is None)

            # A fresh source exercises a real failure after units, mappings,
            # audit and receipt have all been written in the joined transaction.
            Folder(iri=Iri('demo:rollbacksource'), **{'schema:name': 'Rollback source',
                'shared:inStagingArea': 'demo:writearea', 'shared:inStagingFolder': 'demo:writetop',
                'oldap:attachedToRole': grants}).create()
            request = prepare('rollbacksource')
            operation = str(uuid4())
            service = ArchiveAdoption(con, 'demo')
            created = []
            try:
                with resource_transaction(con):
                    result = service.apply(request, operation_id=operation)
                    created = [row['iri'] for row in result['createdUnits']]
                    owner = json.loads(gate.get(GATE_KEY))
                    check('Writer ownership journals the active Jena session before commit', bool(owner['transactions']))
                    raise RuntimeError('owned archive rollback')
            except RuntimeError as error:
                assert str(error) == 'owned archive rollback'
            check('Aborted adoption removes its receipt and structural audit', records(operation) == [])
            prefix = service._policy().context.sparql_context
            check('Aborted adoption removes new units and restores original mapping',
                  not admin.query(prefix + 'ASK { GRAPH demo:data { VALUES ?s { ' +
                    ' '.join('<' + iri + '>' for iri in created) + ' } ?s ?p ?o } }')['boolean']
                  and not admin.query(prefix + 'ASK { GRAPH demo:data { demo:rollbacksource shared:defaultArchiveUnit ?target } }')['boolean'])
            check('Confirmed rollback releases durable ownership and closes the session',
                  gate.get(GATE_KEY) is None and not con.in_transaction())
            # Retry the still-current reviewed request after a confirmed rollback.
            result = call('POST', path + 'apply', request, headers={**headers, 'Idempotency-Key': operation}).json()
            check('A confirmed rolled-back operation can be applied once successfully',
                  result['state'] == 'committed' and len(records(operation)) == 3)
            call('POST', path + 'apply', request, headers={**headers, 'Idempotency-Key': str(uuid4())}, status=409)
            check('A stale apply is rejected after another operation changes its source', gate.get(GATE_KEY) is None)
            Folder(iri=Iri('demo:structureonly'), **{'schema:name': 'Structure only',
                'shared:inStagingArea': 'demo:writearea', 'shared:inStagingFolder': 'demo:writetop',
                'oldap:attachedToRole': grants}).create()
            request = prepare('structureonly', apply_mappings=False)
            operation = str(uuid4())
            result = call('POST', path + 'apply', request, headers={**headers, 'Idempotency-Key': operation}).json()
            check('Structure-only adoption creates units without changing source mappings',
                  len(result['createdUnits']) == 1 and result['mappings'] == []
                  and not admin.query(prefix + 'ASK { GRAPH demo:data { demo:structureonly shared:defaultArchiveUnit ?target } }')['boolean'])
            journal = records(operation)
            receipt = next(row for row in journal if row.get('command') == 'structure-apply')
            check('Structure-only receipt retains provenance with only unit-creation audit',
                  len(journal) == 2 and receipt['applyMappings'] is False
                  and receipt['sourceCorrespondence'] == [{'folderIri': base + 'structureonly',
                                                           'targetIri': result['createdUnits'][0]['iri']}])
        finally:
            gate.close()
