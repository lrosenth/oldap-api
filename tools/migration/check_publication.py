"""Publication service acceptance with real modeled resources and Jena transactions.

Only server policy selection is supplied explicitly by the fixture. Authorization,
model loading, review, writes, receipts and rollback use production implementations.
"""
from uuid import uuid4

from oldaplib.src.archive_policy import ArchivePolicy
from oldaplib.src.archive_publication import ArchivePublication, PublicationConflict, validate_resources
from oldaplib.src.helpers.oldaperror import OldapErrorNoPermission


class ConfiguredPublication(ArchivePublication):
    """Supply the owned test policy without enabling other archive workflows."""
    def _policy(self):
        return self.fixture_policy


def check_publication(call, check, create_connection):
    """Publish a root/media pair and prove scoped replacement and atomic failure."""
    base = 'https://example.org/demo/'
    call('PUT', '/admin/role/demo/Public', {'label': ['Public@en']})
    call('PUT', '/admin/datamodel/demo/demo:PublicationBase', {'label': ['Publication base@en'],
        'superclass': ['oldap:Thing'], 'properties': [
            {'iri': 'demo:publicationStatus', 'class': 'oldap:Thing', 'maxCount': 1}]})
    call('PUT', '/admin/datamodel/demo/demo:PublishedRoot', {'label': ['Publication root@en'],
        'superclass': ['demo:PublicationBase'], 'properties': []})
    call('PUT', '/admin/datamodel/demo/demo:PublishedMedia', {'label': ['Publication media@en'],
        'superclass': ['demo:PublicationBase'], 'properties': [
            {'iri': 'demo:depictsRoot', 'class': 'demo:PublishedRoot'}]})
    grants = {'demo:Writer': 'DATA_UPDATE', 'demo:Public': 'DATA_RESTRICTED'}
    call('PUT', '/data/demo/demo:PublishedRoot', {'iri': 'pubroot', 'oldap:attachedToRole': grants})
    call('PUT', '/data/demo/demo:PublishedMedia', {'iri': 'pubmedia', 'demo:depictsRoot': ['demo:pubroot'],
        'oldap:attachedToRole': grants})
    con = create_connection(userId='writer', credentials='owned-writer-password')
    service = ConfiguredPublication(con, 'demo')
    definition = dict(publisherRoleIris=[base + 'Writer'], rootClassIris=[base + 'PublishedRoot'],
        mediaClassIris=[base + 'PublishedMedia'], statusPropertyIri=base + 'publicationStatus',
        publishedStatusIri=base + 'Published', mediaToRootPropertyIri=base + 'depictsRoot',
        publicRoleIri=base + 'Public', maxResources=10)
    service.fixture_policy = ArchivePolicy(con, service.project, True, publication=definition)
    validate_resources(service.fixture_policy, service.factory)
    admin = create_connection(userId='actor', credentials='owned-fixture-password')
    prefix = service.fixture_policy.context.sparql_context

    def ask(pattern):
        return admin.query(prefix + 'ASK { ' + pattern + ' }')['boolean']

    def expect(error, action):
        try:
            action()
        except error:
            return
        raise AssertionError('Expected ' + error.__name__)

    request = {'resourceIri': base + 'pubroot', 'permission': 'DATA_VIEW'}
    review = service.preview(request)
    check('Publication preview includes root and linked media using real permissions', len(review['resources']) == 2)
    # Change an ACL value only: the exact reviewed state must become stale.
    admin.update_query(prefix + '''INSERT DATA { GRAPH demo:data {
        demo:extraGrant rdf:reifies <<( demo:pubroot oldap:attachedToRole demo:Public )>> ;
            oldap:hasDataPermission oldap:DATA_VIEW ; demo:note "preserve metadata" . }}''')
    expect(PublicationConflict, lambda: service.apply({**request, 'revision': review['revision']}, str(uuid4())))
    check('Publication rejects stale review after an annotation-only change',
          not ask('GRAPH demo:data { demo:pubroot demo:publicationStatus ?status }'))

    # Fail on the second resource after the first update has run. The enclosing
    # transaction must roll back both status and permission edits and the receipt.
    admin.update_query(prefix + '''INSERT DATA { GRAPH demo:data {
        demo:sharedGrant rdf:reifies <<( demo:pubmedia oldap:attachedToRole demo:Public )>>,
            <<( demo:unrelated oldap:attachedToRole demo:Public )>> ; oldap:hasDataPermission oldap:DATA_VIEW . }}''')
    review = service.preview(request)
    operation = str(uuid4())
    expect(PublicationConflict, lambda: service.apply({**request, 'revision': review['revision']}, operation))
    check('Shared reifier refusal rolls back preceding resource publication and receipt',
          not ask('GRAPH demo:data { ?s demo:publicationStatus ?status }')
          and service._receipt(service.fixture_policy, operation, command='publication') is None
          and ask('GRAPH demo:data { demo:extraGrant oldap:hasDataPermission oldap:DATA_VIEW }'))
    admin.update_query(prefix + 'DELETE WHERE { GRAPH demo:data { demo:sharedGrant ?p ?o } }')
    review = service.preview(request)
    operation = str(uuid4())
    applied = {**request, 'revision': review['revision']}
    result = service.apply(applied, operation)
    check('Publication commits both resources and public grants', result['resourceIris'] == [base + 'pubmedia', base + 'pubroot']
          and ask('''GRAPH demo:data { demo:pubroot demo:publicationStatus demo:Published .
              demo:pubmedia demo:publicationStatus demo:Published .
              ?a rdf:reifies <<( demo:pubroot oldap:attachedToRole demo:Public )>> ; oldap:hasDataPermission oldap:DATA_VIEW .
              ?b rdf:reifies <<( demo:pubmedia oldap:attachedToRole demo:Public )>> ; oldap:hasDataPermission oldap:DATA_VIEW }'''))
    check('Publication preserves internal grants and unrelated reifier metadata',
          ask('''GRAPH demo:data { ?a rdf:reifies <<( demo:pubroot oldap:attachedToRole demo:Writer )>> ; oldap:hasDataPermission oldap:DATA_UPDATE .
              demo:extraGrant demo:note "preserve metadata" }
              FILTER NOT EXISTS { GRAPH demo:data { demo:extraGrant oldap:hasDataPermission ?grant } }'''))
    check('Publication replay returns the committed receipt', service.apply(applied, operation) == result)
    expect(PublicationConflict, lambda: service.apply({**applied, 'permission': 'DATA_RESTRICTED'}, operation))
    check('Publication rejects operation-ID reuse with changed request', True)
    call('PUT', '/data/demo/demo:PublishedRoot', {'iri': 'pubsecond', 'oldap:attachedToRole': grants})
    second = {**request, 'resourceIri': base + 'pubsecond'}
    review = service.preview(second)
    service.apply({**second, 'revision': review['revision']}, str(uuid4()))
    link = {'mediaIri': base + 'pubmedia', 'parentIri': base + 'pubsecond'}
    review = service.preview_link(link)
    linked_request = {**link, 'revision': review['revision']}
    link_operation = str(uuid4())
    linked = service.apply_link(linked_request, link_operation)
    check('Publication link review and apply preserve existing parents and grants',
          not review['alreadyLinked'] and ask("""GRAPH demo:data {
              demo:pubmedia demo:depictsRoot demo:pubroot, demo:pubsecond .
              ?g rdf:reifies <<( demo:pubmedia oldap:attachedToRole demo:Public )>> ; oldap:hasDataPermission oldap:DATA_VIEW }"""))
    check('Publication link receipt replays without another edit', service.apply_link(linked_request, link_operation) == linked)
    # No automatic widening on re-publication after an explicit downgrade.
    lower = {**request, 'permission': 'DATA_RESTRICTED'}
    review = service.preview(lower)
    service.apply({**lower, 'revision': review['revision']}, str(uuid4()))
    check('Re-publication never widens existing public grants',
          all(row['permission'] == 'DATA_RESTRICTED' for row in service.preview(request)['resources']))
    admin.update_query(prefix + f'DELETE DATA {{ GRAPH oldap:admin {{ {con.userIri.toRdf} oldap:hasRole demo:Writer }} }}')
    try:
        expect(OldapErrorNoPermission, lambda: service.preview(request))
        check('Publication checks current publisher-role membership', True)
    finally:
        admin.update_query(prefix + f'INSERT DATA {{ GRAPH oldap:admin {{ {con.userIri.toRdf} oldap:hasRole demo:Writer }} }}')
