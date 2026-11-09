"""Owned acceptance of resource writes and data permissions through normal API routes."""
from oldaplib.src.objectfactory import ResourceInstanceFactory
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.helpers.oldaperror import OldapErrorUpdateFailed, OldapErrorAlreadyExists
from oldaplib.src.resource_transaction import resource_transaction


def check_resource_writes(call, check, create_connection):
    """Check ordinary CRUD, permission thresholds and transaction rollback."""
    call('PUT', '/admin/datamodel/demo/demo:Record', {'label': ['Record@en'], 'superclass': ['oldap:Thing'],
        'properties': [{'iri': 'demo:body', 'datatype': 'xsd:string', 'maxCount': 1}]})
    call('PUT', '/admin/role/demo/Writer', {'label': ['Writer@en']})
    call('PUT', '/admin/user/writer', {'givenName': 'Data', 'familyName': 'Writer', 'email': 'writer@example.org',
        'password': 'owned-writer-password', 'inProjects': [{'project': 'https://example.org/project/demo', 'permissions': []}],
        'hasRole': {'demo:Writer': 'DATA_VIEW'}})
    token = call('POST', '/admin/auth/writer', {'password': 'owned-writer-password'}).json()['accessToken']
    writer = {'Authorization': 'Bearer ' + token}
    con = create_connection(userId='actor', credentials='owned-fixture-password')
    # Factory.read intentionally requires a role grant even for administrators;
    # retain that established contract in this synthetic root-user fixture.
    con.update_query('INSERT DATA { GRAPH <http://oldap.org/base#admin> {'
        '<https://example.org/actor> <http://oldap.org/base#hasRole> <https://example.org/demo/Writer> }}')
    payload = {'iri': 'record', 'demo:body': 'Original', 'oldap:attachedToRole': {'demo:Writer': 'DATA_VIEW'}}
    call('PUT', '/data/demo/demo:Record', payload, headers=writer, status=403)
    check('Role membership alone does not grant resource creation', True)
    call('PUT', '/data/demo/demo:Record', payload)
    call('PUT', '/data/demo/demo:Record', payload, status=409)
    path = '/data/demo/demo:record'
    check('API creates resource with readable RDF 1.2 grant and rejects duplicate IRI',
          'Original' in call('GET', path, headers=writer).text)
    call('POST', path, {'demo:body': 'Forbidden'}, headers=writer, status=403)
    call('DELETE', path, headers=writer, status=403)
    check('View-only role cannot update or delete data', 'Original' in call('GET', path).text)
    call('POST', path, {'oldap:attachedToRole': {'demo:Writer': 'DATA_UPDATE'}})
    call('POST', path, {'demo:body': 'Changed by writer'}, headers=writer)
    check('Object DATA_UPDATE grant authorizes ordinary user update', 'Changed by writer' in call('GET', path).text)
    call('POST', path, {'oldap:attachedToRole': {'demo:Writer': 'DATA_PERMISSIONS'}}, headers=writer, status=403)
    check('DATA_UPDATE cannot escalate object permissions', True)

    call('POST', path, {'oldap:attachedToRole': {'demo:Writer': 'DATA_PERMISSIONS'}})
    call('POST', path, {'demo:body': 'Changed with permissions',
         'oldap:attachedToRole': {'demo:Writer': 'DATA_UPDATE'}}, headers=writer)
    check('DATA_PERMISSIONS permits atomic data and grant changes', 'Changed with permissions' in call('GET', path).text)

    con = create_connection(userId='actor', credentials='owned-fixture-password')
    factory = ResourceInstanceFactory(con=con, project='demo')
    Record = factory.createObjectInstance('demo:Record')
    try:
        with resource_transaction(con):
            Record(iri=Iri('demo:pending'), **{'demo:body': 'Pending', 'oldap:attachedToRole': {'demo:Writer': 'DATA_VIEW'}}).create()
            Record(iri=Iri('demo:record'), **{'demo:body': 'Duplicate', 'oldap:attachedToRole': {'demo:Writer': 'DATA_VIEW'}}).create()
    except OldapErrorAlreadyExists:
        check('Composed transaction rolls back earlier create when later create fails', not con.query(
            'ASK { GRAPH <https://example.org/demo/data> { <https://example.org/demo/pending> ?p ?o }}')['boolean'])
    else:
        raise AssertionError('Duplicate in composed transaction unexpectedly succeeded')
    stale = factory.read(Iri('demo:record'))
    call('POST', path, {'demo:body': 'Fresh change'})
    stale[Xsd_QName('demo:body')] = 'Stale change'
    try:
        stale.update()
    except OldapErrorUpdateFailed:
        check('Stale resource update rolls back value changes', 'Fresh change' in call('GET', path).text)
    else:
        raise AssertionError('Stale update unexpectedly succeeded')

    instance = factory.read(Iri('demo:record'))
    instance[Xsd_QName('demo:body')] = 'Callback must roll back'
    def fail_after_write(connection):
        connection.transaction_update('INSERT DATA { GRAPH <https://example.org/demo/data> {'
            '<https://example.org/callback> <https://example.org/marker> "pending" }}')
        raise RuntimeError('owned callback failure')
    try:
        instance.update(before_commit=fail_after_write)
    except RuntimeError as error:
        assert str(error) == 'owned callback failure'
    else:
        raise AssertionError('Callback failure did not escape')
    check('Callback failure rolls back resource and related write together',
          'Fresh change' in call('GET', path).text and not con.query(
              'ASK { GRAPH <https://example.org/demo/data> {<https://example.org/callback> ?p ?o }}')['boolean'])
    # A grant in another graph must never raise rights on this project object.
    con.update_query('PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> '
        'PREFIX oldap: <http://oldap.org/base#> INSERT DATA { GRAPH <https://example.org/foreign> {'
        '<https://example.org/demo/record> oldap:attachedToRole <https://example.org/demo/Writer> .'
        '<https://example.org/foreign-grant> rdf:reifies <<( <https://example.org/demo/record> '
        'oldap:attachedToRole <https://example.org/demo/Writer> )>> ; oldap:hasDataPermission oldap:DATA_PERMISSIONS . }}')
    call('POST', path, {'demo:body': 'Foreign grant must not help',
         'oldap:attachedToRole': {'demo:Writer': 'DATA_PERMISSIONS'}}, headers=writer, status=403)
    check('Foreign-graph grants cannot authorize or partially apply updates', 'Fresh change' in call('GET', path).text)
    # Reification alone must not confer access after asserted membership removal.
    con.update_query('DELETE DATA { GRAPH <https://example.org/demo/data> { <https://example.org/demo/record> '
        '<http://oldap.org/base#attachedToRole> <https://example.org/demo/Writer> }}')
    call('GET', path, headers=writer, status=404)
    check('Orphaned grant does not preserve read access', True)
    con.update_query('INSERT DATA { GRAPH <https://example.org/demo/data> { <https://example.org/demo/record> '
        '<http://oldap.org/base#attachedToRole> <https://example.org/demo/Writer> }}')

    call('PUT', '/admin/datamodel/demo/demo:RevisedRecord', {'label': ['Revised record@en'],
        'superclass': ['demo:Record'], 'properties': [{'iri': 'demo:revision', 'datatype': 'xsd:string', 'maxCount': 1}]})
    call('POST', path + '/transform', {'targetClass': 'demo:RevisedRecord', 'preserveClass': 'demo:Record',
        'expectedSourceClass': 'demo:Record', 'properties': {'demo:revision': 'Transformed'},
        'attachedToRole': {'demo:Writer': 'DATA_UPDATE'}})
    check('Class transformation commits new class, values and RDF 1.2 permissions',
          'Transformed' in call('GET', path, headers=writer).text and con.query(
          'ASK { GRAPH <https://example.org/demo/data> {<https://example.org/demo/record> a <https://example.org/demo/RevisedRecord> }}')['boolean'])
    prefix = 'PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> PREFIX oldap: <http://oldap.org/base#> '
    con.update_query(prefix + 'INSERT DATA { GRAPH <https://example.org/demo/data> {'
        '<https://example.org/shared-resource-grant> rdf:reifies '
        '<<( <https://example.org/demo/record> oldap:attachedToRole <https://example.org/demo/Writer> )>>,'
        '<<( <https://example.org/demo/other> oldap:attachedToRole <https://example.org/demo/Writer> )>> ;'
        'oldap:hasDataPermission oldap:DATA_UPDATE . }}')
    call('POST', path, {'demo:body': 'Must not persist', 'oldap:attachedToRole': {'demo:Writer': 'DATA_VIEW'}}, status=409)
    call('DELETE', path, status=409)
    check('Shared object grant rejects edits and deletion before changing data', 'Fresh change' in call('GET', path).text)
    con.update_query('DELETE WHERE { GRAPH <https://example.org/demo/data> { <https://example.org/shared-resource-grant> ?p ?o }}')
    # Refresh the factory after changing the model, then test deletion hooks.
    factory = ResourceInstanceFactory(con=con, project='demo')
    instance = factory.read(Iri('demo:record'))
    try:
        instance.delete(before_commit=fail_after_write)
    except RuntimeError as error:
        assert str(error) == 'owned callback failure'
    else:
        raise AssertionError('Delete callback failure did not escape')
    check('Failed delete callback restores resource and permission grants',
          'Transformed' in call('GET', path, headers=writer).text)
    call('POST', path, {'oldap:attachedToRole': {'demo:Writer': 'DATA_DELETE'}})
    call('DELETE', path, headers=writer)
    call('GET', path, status=404)
    check('DATA_DELETE removes the resource and its grant annotations', not con.query(
        'PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> '
        'ASK { GRAPH <https://example.org/demo/data> { ?grant rdf:reifies '
        '<<( <https://example.org/demo/record> <http://oldap.org/base#attachedToRole> ?role )>> }}')['boolean'])
    check('Resource deletion leaves identical grant terms in foreign graph untouched', con.query(
        'ASK { GRAPH <https://example.org/foreign> { <https://example.org/foreign-grant> ?p ?o }}')['boolean'])
    payload['iri'] = 'revoked'
    call('PUT', '/data/demo/demo:Record', payload)
    call('POST', '/data/demo/demo:revoked', {'oldap:attachedToRole': {}})
    call('GET', '/data/demo/demo:revoked', headers=writer, status=404)
    check('Empty role map removes asserted grants and revokes access', not con.query(prefix +
        'ASK { GRAPH <https://example.org/demo/data> { <https://example.org/demo/revoked> oldap:attachedToRole ?role }}')['boolean'])
    Record = factory.createObjectInstance('demo:Record')
    Record.read(con, Iri('demo:revoked')).delete()
