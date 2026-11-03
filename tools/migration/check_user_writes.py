"""Real API user/role acceptance against the runner's owned Jena dataset."""


def check_user_writes(call, check, create_connection):
    """Exercise unchanged routes, persisted RDF 1.2 grants and rollback boundaries."""
    from oldaplib.src.user import User
    from oldaplib.src.helpers.oldaperror import OldapErrorNoPermission, OldapErrorUpdateFailed

    project = 'https://example.org/project/demo'
    call('PUT', '/admin/role/demo/Reader', {'label': ['Reader@en']})
    call('POST', '/admin/role/demo/Reader', {'label': ['Updated reader@en']})
    check('Role create/update/read works with Jena', 'Updated reader' in call('GET', '/admin/role/demo/Reader').text)
    definition = {'givenName': 'Migration', 'familyName': 'Reader', 'email': 'reader@example.org',
                  'password': 'owned-reader-password', 'inProjects': [{'project': project, 'permissions': ['ADMIN_USERS']}],
                  'hasRole': {'demo:Reader': 'DATA_VIEW'}}
    call('PUT', '/admin/user/reader', definition)
    user = call('GET', '/admin/user/reader').json()
    check('User creation round-trips project and role permissions',
          user['hasRole'] == {'demo:Reader': 'DATA_VIEW'} and
          user['inProjects'] == [{'project': project, 'permissions': ['oldap:ADMIN_USERS']}])
    con = create_connection(userId='actor', credentials='owned-fixture-password')
    # The generated user IRI may be a UUID URN; serialize it as an absolute IRI
    # rather than feeding it through the existing string/QName ambiguity.
    iri = '<' + user['userIri'] + '>'
    assert_query = 'ASK { GRAPH oldap:admin { ' + iri
    prefix = 'PREFIX oldap: <http://oldap.org/base#> PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> '
    check('User creation writes asserted membership plus RDF 1.2 grant', con.query(prefix + assert_query +
          ' oldap:inProject <' + project + '> . ?g rdf:reifies <<( ' + iri + ' oldap:inProject <' + project + '> )>> ;'
          ' oldap:hasAdminPermission oldap:ADMIN_USERS }}')['boolean'])
    # One reifier describing two memberships is valid RDF 1.2 but ambiguous
    # for OLDAP permission edits. Reject it rather than changing another user.
    shared = '<https://example.org/shared-grant>'
    other = '<<( <https://example.org/actor> oldap:inProject oldap:SystemProject )>>'
    con.update_query(prefix + 'INSERT DATA { GRAPH oldap:admin {' + shared +
        ' rdf:reifies <<( ' + iri + ' oldap:inProject <' + project + '> )>>, ' + other +
        ' ; oldap:hasAdminPermission oldap:ADMIN_USERS . }}')
    call('POST', '/admin/user/reader', {'inProjects': [{'project': project, 'permissions': []}]}, status=409)
    call('DELETE', '/admin/user/reader', status=409)
    check('Shared reifier refuses update and deletion without altering another membership',
          call('GET', '/admin/user/reader').json() == user and con.query(prefix +
          'ASK { GRAPH oldap:admin {' + shared + ' rdf:reifies ' + other +
          '; oldap:hasAdminPermission oldap:ADMIN_USERS }}')['boolean'])
    con.update_query(prefix + 'DELETE WHERE { GRAPH oldap:admin {' + shared + ' ?p ?o }}')
    reader = create_connection(userId='reader', credentials='owned-reader-password')
    check('New user authenticates with persisted RDF 1.2 role grant', 'demo:Reader' in {str(role) for role in reader.userdata.hasRole})
    stale = User.read(con=con, userId='reader')
    call('POST', '/admin/user/reader', {'familyName': 'Changed', 'inProjects': [
        {'project': project, 'permissions': ['ADMIN_MODEL']}], 'hasRole': {'demo:Reader': 'DATA_UPDATE'}})
    updated = call('GET', '/admin/user/reader').json()
    check('User scalar and permission updates persist together', updated['familyName'] == 'Changed' and
          updated['hasRole'] == {'demo:Reader': 'DATA_UPDATE'} and
          updated['inProjects'] == [{'project': project, 'permissions': ['oldap:ADMIN_MODEL']}])
    stale.familyName = 'Stale edit'
    try:
        stale.update()
    except OldapErrorUpdateFailed:
        check('Stale user update is rejected without overwriting permissions', call('GET', '/admin/user/reader').json() == updated)
    else:
        raise AssertionError('Stale user update unexpectedly succeeded')
    version = int(User.read(con=con, userId='reader').authVersion)
    check('Security-sensitive update increments authentication version', version == 1)
    # An invalid target must abort before any scalar or grant changes persist.
    call('POST', '/admin/user/reader', {'familyName': 'Must not persist',
        'hasRole': {'demo:Missing': 'DATA_VIEW'}}, status=404)
    check('Invalid role rolls back all user changes', call('GET', '/admin/user/reader').json() == updated)
    call('POST', '/admin/user/reader', {'familyName': 'Must not persist', 'inProjects': [
        {'project': 'https://example.org/project/missing', 'permissions': ['ADMIN_USERS']}]}, status=404)
    check('Invalid project rolls back data and authentication version',
          call('GET', '/admin/user/reader').json() == updated and int(User.read(con=con, userId='reader').authVersion) == version)
    # Imported datasets can contain several reifiers for one grant. Revocation
    # must clear all permission values while preserving unrelated annotations.
    con.update_query(prefix + 'INSERT DATA { GRAPH oldap:admin {'
        ' <https://example.org/duplicate-grant> rdf:reifies <<( ' + iri + ' oldap:inProject <' + project + '> )>> ;'
        ' oldap:hasAdminPermission oldap:ADMIN_MODEL ; <https://example.org/note> "keep" . }}')
    call('POST', '/admin/user/reader', {'inProjects': [{'project': project, 'permissions': []}], 'hasRole': None})
    empty = call('GET', '/admin/user/reader').json()
    check('Empty project permissions preserve membership while role removal clears grants',
          empty['inProjects'] == [{'project': project, 'permissions': []}] and empty['hasRole'] == {})
    check('Removed permissions leave no owned grant annotations', not con.query(prefix +
          'ASK { GRAPH oldap:admin { ?g rdf:reifies <<( ' + iri + ' ?membership ?target )>> ;'
          ' ?permission ?value . VALUES ?permission { oldap:hasAdminPermission oldap:hasDefaultDataPermission } }}')['boolean'])
    check('Permission cleanup preserves unrelated annotation metadata', con.query(prefix +
        'ASK { GRAPH oldap:admin { <https://example.org/duplicate-grant> <https://example.org/note> "keep" }}')['boolean'])
    reader = create_connection(userId='reader', credentials='owned-reader-password')
    denied = User.read(con=reader, userId='reader')
    denied.familyName = 'Unauthorized edit'
    try:
        denied.update()
    except OldapErrorNoPermission:
        check('User without admin permission cannot change profile fields', call('GET', '/admin/user/reader').json() == empty)
    else:
        raise AssertionError('Unauthorized user update unexpectedly succeeded')
    call('POST', '/admin/user/reader', {'inProjects': None})
    check('Removing all projects leaves no membership', call('GET', '/admin/user/reader').json()['inProjects'] == [])
    call('POST', '/admin/user/reader', {'inProjects': [{'project': project, 'permissions': ['ADMIN_USERS']}],
                                       'hasRole': {'demo:Reader': 'DATA_VIEW'}})
    con.update_query(prefix + 'INSERT DATA { GRAPH <https://example.org/unrelated> {' + iri +
                     ' <https://example.org/note> "keep" }}')
    call('DELETE', '/admin/user/reader')
    call('GET', '/admin/user/reader', status=404)
    check('User deletion removes administration triples', not con.query(prefix + assert_query + ' ?p ?o }}')['boolean'])
    check('User deletion removes remaining grant permissions', not con.query(prefix +
        'ASK { GRAPH oldap:admin { ?g rdf:reifies <<( ' + iri + ' ?membership ?target )>> ;'
        ' ?permission ?value . VALUES ?permission { oldap:hasAdminPermission oldap:hasDefaultDataPermission } }}')['boolean'])
    check('User deletion preserves other graphs and users', con.query(prefix +
        'ASK { GRAPH <https://example.org/unrelated> {' + iri + ' <https://example.org/note> "keep" }'
        ' GRAPH oldap:admin { <https://example.org/actor> a oldap:User }}')['boolean'])
    call('DELETE', '/admin/role/demo/Reader')
    call('GET', '/admin/role/demo/Reader', status=404)
    check('Unassigned role deletion succeeds', True)
