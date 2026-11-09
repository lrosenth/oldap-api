"""Real Jena inventory/adoption queries with explicit owned archive policy.

Folders use imported RDF fixtures and the real shared-model reader. Media rows deliberately
exercise imported RDF edge cases without pretending to validate media uploads.
"""
import hashlib
import json

from oldaplib.src.archive_adoption import ArchiveAdoption
from oldaplib.src.archive_inventory import ArchiveInventory
from oldaplib.src.archive_policy import ArchivePolicy, ArchiveConflict
from oldaplib.src.helpers.jena_permission_write import permission_annotation
from oldaplib.src.resource_transaction import resource_transaction
from oldaplib.src.xsd.iri import Iri


class ConfiguredAdoption(ArchiveAdoption):
    """Provide fixture-owned policy without enabling deployment coordination."""
    def _policy(self):
        return self.fixture_policy


def check_archive_reads(call, check, create_connection):
    """Verify class scope, role/creator access, keyset queries and revision guards."""
    base = 'https://example.org/demo/'
    con = create_connection(userId='writer', credentials='owned-writer-password')
    admin = create_connection(userId='actor', credentials='owned-fixture-password')
    adoption = ConfiguredAdoption(con, 'demo')
    policy = ArchivePolicy(con, adoption.project, True, structure_roles=(base + 'Writer',),
                           media_classes=(base + 'Catalogue', base + 'ExactCatalogue'))
    adoption.fixture_policy = policy
    inventory = ArchiveInventory(con, 'demo', cursor_secret=b'owned-inventory-key-0123456789012')
    inventory.repository = adoption
    prefix = policy.context.sparql_context
    # Seed the owned imported dataset directly: creating staging resources via
    # the public API additionally requires deployment write coordination.
    fixture = ''
    for name, parent, permission in [('inventoryroot', None, 'DATA_UPDATE'),
            ('inventorychild', 'inventoryroot', 'DATA_UPDATE'),
            ('inventoryhidden', 'inventoryroot', 'DATA_RESTRICTED'),
            ('inventorydisconnected', 'inventoryhidden', 'DATA_UPDATE')]:
        subject = 'demo:' + name
        fixture += f'{subject} a shared:StagingFolder ; schema:name "{name}" ; shared:inStagingArea demo:inventoryarea ; oldap:attachedToRole demo:Writer . '
        fixture += f'{subject} oldap:createdBy {admin.userIri.toRdf} ; oldap:lastModifiedBy {admin.userIri.toRdf} ; oldap:creationDate "2026-10-28T12:00:00Z"^^xsd:dateTimeStamp ; oldap:lastModificationDate "2026-10-28T12:00:00Z"^^xsd:dateTimeStamp . '
        if parent:
            fixture += f'{subject} shared:inStagingFolder demo:{parent} . '
        fixture += permission_annotation(subject, 'oldap:attachedToRole', 'demo:Writer', 'oldap:' + permission)
    fixture += 'demo:inventoryarea a shared:StagingArea ; schema:name "Owned area" ; shared:mediaPath "/owned/not-used" ; shared:stagingDefaultRole demo:Writer ; shared:stagingQuotaBytes 1024 . '
    admin.update_query(prefix + 'INSERT DATA { GRAPH demo:data { ' + fixture + ' } }')
    folder = adoption.factory.read(Iri('demo:inventoryroot'))
    # A two-edge path crosses project/shared schemas. Another class has its
    # only hierarchy assertion in a foreign schema and must not match.
    triples = '''GRAPH demo:onto { demo:Photo rdfs:subClassOf shared:OwnedStage .
        demo:CataloguePhoto rdfs:subClassOf demo:Catalogue . }
        GRAPH shared:onto { shared:OwnedStage rdfs:subClassOf shared:StagingMediaObject . }
        GRAPH demo:foreign { demo:ForeignPhoto rdfs:subClassOf shared:StagingMediaObject . }
        GRAPH demo:data { demo:inventoryroot shared:referencedMediaObject demo:archived, demo:exact, demo:visible . }
    '''
    rows = [('visible', 'demo:Photo', 'DATA_VIEW'), ('hidden', 'demo:Photo', 'DATA_RESTRICTED'),
            ('orphan', 'demo:Photo', 'DATA_VIEW'), ('foreign', 'demo:ForeignPhoto', 'DATA_VIEW'),
            ('creator', 'shared:StagingMediaObject', None), ('archived', 'demo:CataloguePhoto', 'DATA_VIEW'),
            ('exact', 'demo:ExactCatalogue', 'DATA_VIEW')]
    for name, kind, permission in rows:
        subject = 'demo:' + name
        properties = f'{subject} a {kind} . '
        if name not in ('archived', 'exact'):
            properties += f'{subject} shared:inStagingFolder demo:inventoryroot ; shared:inStagingArea demo:inventoryarea . '
        if name == 'creator':
            properties += f'{subject} oldap:createdBy {con.userIri.toRdf} . '
        if permission:
            if name != 'orphan':
                properties += f'{subject} oldap:attachedToRole demo:Writer . '
            properties += permission_annotation(subject, 'oldap:attachedToRole', 'demo:Writer', 'oldap:' + permission)
        triples += 'GRAPH demo:data { ' + properties + ' }\n'
    # This identity belongs to both categories: per-folder counts deduplicate it.
    triples += 'GRAPH demo:data { demo:visible a demo:CataloguePhoto . }'
    admin.update_query(prefix + 'INSERT DATA { ' + triples + ' }')

    def identities(last=None, limit=50):
        return [(row['kind']['value'], row['media']['value']) for row in inventory._rows(policy, folder, limit, last)]

    expected = [('archiveReference', base + 'archived'), ('archiveReference', base + 'exact'),
                ('archiveReference', base + 'visible'), ('stagingMedia', base + 'creator'), ('stagingMedia', base + 'visible')]
    check('Inventory queries honor role thresholds, creator access and graph-scoped classes', identities() == expected)
    first = identities(limit=2)
    last = (first[-1][0], hashlib.sha256(first[-1][1].encode()).hexdigest())
    check('Inventory keyset continuation preserves order without duplicate rows', first + identities(last) == expected)
    counts = adoption._direct_media_counts([{'iri': base + 'inventoryroot'}, {'iri': base + 'inventorychild'}],
                                           base + 'inventoryarea', policy)
    assert counts == {base + 'inventoryroot': 4, base + 'inventorychild': 0}, counts
    check('Adoption counts deduplicate mixed memberships and exclude hidden or orphaned grants',
          counts == {base + 'inventoryroot': 4, base + 'inventorychild': 0})
    source, states = adoption._source(base + 'inventoryroot', policy)
    check('Adoption source excludes hidden folders and visible descendants behind them',
          {row['iri'] for row in source['folders']} == {base + 'inventoryroot', base + 'inventorychild'})
    check('Batch adoption revisions agree with repository folder revisions',
          adoption._revision(states[base + 'inventoryroot']) == adoption.folder_revision(folder, policy))
    proposal = adoption.proposal({'sourceFolderIri': base + 'inventoryroot'})
    admin.update_query(prefix + 'INSERT DATA { GRAPH demo:data { ' + permission_annotation(
        'demo:inventorychild', 'oldap:attachedToRole', 'demo:Writer', 'oldap:DATA_VIEW') + ' } }')
    fresh, _ = adoption._source(base + 'inventoryroot', policy)
    check('Annotation-only changes invalidate the adoption source snapshot', fresh['sourceSnapshot'] != source['sourceSnapshot'])
    try:
        adoption.preflight({'plan': proposal['suggestedPlan']})
    except ArchiveConflict as error:
        assert error.code == 'STALE_REVIEW'
    else:
        raise AssertionError('Expected stale adoption plan')
    check('Public adoption preflight rejects a stale plan before writes', not con.in_transaction())

    # Default-target lookups use the same schema/visibility rules as media.
    target_data = 'demo:unit a demo:Unit . demo:secretUnit a shared:ArchiveUnit . demo:unit oldap:attachedToRole demo:Writer . '
    target_data += permission_annotation('demo:unit', 'oldap:attachedToRole', 'demo:Writer', 'oldap:DATA_VIEW')
    target_data += 'demo:inventoryroot shared:defaultArchiveUnit demo:unit . demo:inventorychild shared:defaultArchiveUnit demo:secretUnit . '
    admin.update_query(prefix + 'INSERT DATA { GRAPH demo:onto { demo:Unit rdfs:subClassOf shared:ArchiveUnit } GRAPH demo:data { ' + target_data + ' } }')
    mapped, _ = adoption._source(base + 'inventoryroot', policy)
    mappings = {row['iri']: row for row in mapped['folders']}
    check('Adoption exposes visible subclass targets but hides inaccessible default IRIs',
          mappings[base + 'inventoryroot']['defaultArchiveUnitIri'] == base + 'unit'
          and mappings[base + 'inventorychild']['defaultArchiveUnitIri'] is None
          and mappings[base + 'inventorychild']['mappingState'] == 'unavailable')
    admin.update_query(prefix + 'DELETE DATA { GRAPH demo:data { demo:inventorychild shared:defaultArchiveUnit demo:secretUnit } }')
    record = {'command': 'structure-apply', 'applyMappings': False, 'project': 'demo',
              'sourceCorrespondence': [{'folderIri': base + 'inventorychild', 'targetIri': base + 'unit'}]}
    admin.update_query('INSERT DATA { GRAPH <urn:oldap:archive-operations> { <urn:owned:hint> <urn:oldap:archive:record> '
                       + json.dumps(json.dumps(record)) + ' } }')
    hints = adoption.default_proposal({'sourceFolderIri': base + 'inventoryroot'})
    check('Default proposal resolves visible receipt hints and direct media counts',
          hints['suggestedPlan']['mappings'] == [{'folderIri': base + 'inventorychild', 'action': 'set', 'target': {'iri': base + 'unit'}}]
          and next(row for row in hints['folders'] if row['iri'] == base + 'inventoryroot')['directMediaCount'] == 4)
    admin.update_query(prefix + 'DELETE DATA { GRAPH demo:data { demo:unit oldap:attachedToRole demo:Writer } }')
    hidden_hints = adoption.default_proposal({'sourceFolderIri': base + 'inventoryroot'})
    check('Receipt provenance never grants access after target membership removal', hidden_hints['suggestedPlan']['mappings'] == [])

    # State digests include orphan annotations but never reifier identities.
    old_revision = adoption.folder_revision(folder, policy)
    admin.update_query(prefix + 'INSERT DATA { GRAPH demo:foreign { ' + permission_annotation(
        'demo:inventoryroot', 'oldap:attachedToRole', 'demo:Writer', 'oldap:DATA_DELETE') + ' } }')
    check('Foreign graph annotations cannot change the reviewed folder revision',
          adoption.folder_revision(folder, policy) == old_revision)
    with resource_transaction(con):
        con.transaction_update(prefix + 'INSERT DATA { GRAPH demo:data { ' + permission_annotation(
            'demo:inventoryroot', 'oldap:attachedToRole', 'demo:Public', 'oldap:DATA_VIEW') + ' } }')
        check('Archive revisions include transaction-local permission changes',
              adoption.folder_revision(folder, policy) != old_revision)
    identity = {'actor': str(policy.context.qname2iri(con.userIri.as_qname)) if con.userIri.is_qname else str(con.userIri),
                'project': 'demo', 'folder': base + 'inventoryroot'}
    cursor = inventory._encode({'context': hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest(),
                                'revision': old_revision, 'last': last})
    try:
        inventory.page(base + 'inventoryroot', cursor=cursor)
    except ArchiveConflict as error:
        assert error.code == 'STALE_FOLDER'
    else:
        raise AssertionError('Expected stale inventory cursor')
    check('Public inventory rejects a stale cursor after a grant change', not con.in_transaction())
