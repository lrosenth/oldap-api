"""Normal API search acceptance after committed and aborted resource mutations."""
from oldaplib.src.enums.datapermissions import DataPermission
from oldaplib.src.objectfactory import ResourceInstanceFactory, FTSearchFilter
from oldaplib.src.resource_transaction import resource_transaction
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.helpers.oldaperror import OldapErrorAlreadyExists


def check_fulltext_writes(call, check, create_connection):
    """Verify index visibility, authorization and live field-map revisions."""
    token = call('POST', '/admin/auth/writer', {'password': 'owned-writer-password'}).json()['accessToken']
    writer = {'Authorization': 'Bearer ' + token}
    path = '/data/demo/demo:indexed'

    def create(name, text, resource='demo:Record', **extra):
        call('PUT', '/data/demo/' + resource, {'iri': name, 'demo:body': text,
            'oldap:attachedToRole': {'demo:Writer': 'DATA_VIEW'}, **extra})

    def search(term, field='body', count=False, **options):
        return call('POST', '/data/search/demo', {'ftfilter': [{'field': field, 'query': term}],
            'countOnly': count, **options}, headers=writer).json()

    def activate(fields):
        state = call('GET', '/admin/fulltext/demo').json()
        return call('PUT', '/admin/fulltext/demo', {'configuration': {
            'graph': 'https://example.org/demo/data', 'fields': fields}, 'expectedRevision': state['revision']}).json()

    # This text exists before its property is configured for indexing.
    create('indexed', 'migrationalpha')
    fields = {'body': ['https://example.org/demo/body']}
    activate(fields)
    check('Activating a new field indexes pre-existing resource text', len(search('migrationalpha')) == 1)
    create('secondindex', 'migrationalpha')
    check('Committed API create immediately enters fulltext search', len(search('migrationalpha')) == 2)
    check('Fulltext count and pagination agree after real creates', search('migrationalpha', count=True)['count'] == 2
          and len(search('migrationalpha', limit=1, offset=1)) == 1)
    call('POST', path, {'demo:body': 'migrationbeta'})
    check('Committed update removes old text and indexes new text', len(search('migrationalpha')) == 1
          and len(search('migrationbeta')) == 1)

    con = create_connection(userId='actor', credentials='owned-fixture-password')
    factory = ResourceInstanceFactory(con=con, project='demo')
    instance = factory.read(Iri('demo:indexed'))
    instance[Xsd_QName('demo:body')] = 'migrationrollback'
    def fail(connection):
        raise RuntimeError('owned fulltext rollback')
    try:
        instance.update(before_commit=fail)
    except RuntimeError as error:
        assert str(error) == 'owned fulltext rollback'
    else:
        raise AssertionError('Expected update callback failure')
    check('Rolled-back update preserves old hits and exposes no pending text',
          len(search('migrationbeta')) == 1 and search('migrationrollback') == [])
    try:
        factory.read(Iri('demo:indexed')).delete(before_commit=fail)
    except RuntimeError as error:
        assert str(error) == 'owned fulltext rollback'
    else:
        raise AssertionError('Expected delete callback failure')
    check('Rolled-back deletion preserves the fulltext hit', len(search('migrationbeta')) == 1)
    Record = factory.createObjectInstance('demo:Record')
    try:
        with resource_transaction(con):
            Record(iri=Iri('demo:pendingindex'), **{'demo:body': 'migrationpending',
                'oldap:attachedToRole': {'demo:Writer': 'DATA_VIEW'}}).create()
            raise RuntimeError('owned create rollback')
    except RuntimeError as error:
        assert str(error) == 'owned create rollback'
    check('Rolled-back create never becomes searchable', search('migrationpending') == [])

    # Permission changes need not remove Lucene text: search must apply current
    # asserted memberships and RDF 1.2 grants on every request, including counts.
    call('POST', path, {'oldap:attachedToRole': {'demo:Writer': 'DATA_RESTRICTED'}})
    check('Permission downgrade removes search hits and counts', search('migrationbeta') == []
          and search('migrationbeta', count=True)['count'] == 0)
    # Use the creator-aware class read to restore access without altering the
    # established factory.read role threshold for API mutations.
    instance = Record.read(con, Iri('demo:indexed'))
    instance[Xsd_QName('oldap:attachedToRole')] = {Xsd_QName('demo:Writer'): DataPermission.DATA_VIEW}
    instance.update()
    check('Restoring permission restores search visibility without text rewrite', len(search('migrationbeta')) == 1)

    call('PUT', '/admin/datamodel/demo/demo:IndexedRecord', {'label': ['Indexed record@en'],
        'superclass': ['demo:Record'], 'properties': [{'iri': 'demo:caption', 'datatype': 'xsd:string', 'maxCount': 1}]})
    create('latefield', 'migrationbody', 'demo:IndexedRecord', **{'demo:caption': 'migrationcaption'})
    call('POST', '/data/search/demo', {'ftfilter': [{'field': 'caption', 'query': 'migrationcaption'}]},
         headers=writer, status=400)
    fields['caption'] = ['https://example.org/demo/caption']
    activate(fields)
    check('New model property becomes searchable through configuration alone', len(search('migrationcaption', 'caption')) == 1)
    combined = call('POST', '/data/search/demo', {'ftfilter': [
        {'field': 'body', 'query': 'migrationbody'}, 'AND', {'field': 'caption', 'query': 'migrationcaption'}],
        'includeProperties': ['demo:caption']}, headers=writer).json()
    check('Configured fields combine with AND and return selected properties',
          len(combined) == 1 and 'migrationcaption' in str(combined))

    # Pin a compiled query to the old map, then change the map from another
    # request. The old connection must reject it instead of interpreting it anew.
    con._resource_fulltext_pattern(Xsd_NCName('demo'), [FTSearchFilter(field='body', query='migrationbeta')], 'score')
    fields['body'] = ['https://example.org/demo/caption']
    activate(fields)
    try:
        con.query('ASK {}')
    except OldapErrorAlreadyExists:
        check('Connection with stale compiled field revision is rejected', True)
    else:
        raise AssertionError('Stale field revision unexpectedly accepted')
    check('Fresh API requests use the new field mapping', search('migrationbeta') == []
          and len(search('migrationcaption')) == 1)
    fields['body'] = ['https://example.org/demo/body']
    activate(fields)
    check('Reactivation rebuilds the original field mapping correctly', len(search('migrationbeta')) == 1)
    call('DELETE', path)
    check('Committed delete removes text from results and counts', search('migrationbeta') == []
          and search('migrationbeta', count=True)['count'] == 0)
    call('DELETE', '/data/demo/demo:secondindex')
    call('DELETE', '/data/demo/demo:latefield')
    check('Deleting remaining resources clears all tested text hits', search('migrationalpha') == []
          and search('migrationcaption', 'caption') == [])
