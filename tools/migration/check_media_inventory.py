"""Owned modeled media, public HTTP lookups and complete inventory hydration."""
import os
from unittest.mock import patch
from urllib.parse import urlencode, quote

from check_archive_writes import owned_writer_store
from oldaplib.src.objectfactory import ResourceInstanceFactory
from oldaplib.src.helpers.context import Context
from oldaplib.src.xsd.iri import Iri


def check_media_inventory(call, check, create_connection, output):
    """Keep real policy, authorization, model loading and token signing active."""
    base = 'https://example.org/demo/'
    token = call('POST', '/admin/auth/writer', {'password': 'owned-writer-password'}).json()['accessToken']
    headers = {'Authorization': 'Bearer ' + token}
    with owned_writer_store(output, name='media-reader-redis') as (_, url), patch.dict(os.environ, {
            'OLDAP_STAGING_LOCK_REDIS_URL': url,
            'OLDAP_ARCHIVE_POLICY_FILE': str(output / 'archive-policy.json')}):
        admin = create_connection(userId='actor', credentials='owned-fixture-password')
        factory = ResourceInstanceFactory(admin, 'demo')
        Folder = factory.createObjectInstance('shared:StagingFolder')
        Folder(iri=Iri('demo:mediafolder'), **{'schema:name': 'Media acceptance',
            'shared:inStagingArea': 'demo:writearea', 'shared:inStagingFolder': 'demo:writetop',
            'oldap:attachedToRole': {'demo:Writer': 'DATA_UPDATE'}}).create()
        Media = factory.createObjectInstance('shared:StagingMediaObject')
        for name, permission in [('mediaone', 'DATA_UPDATE'), ('mediatwo', 'DATA_VIEW'),
                                 ('mediarestricted', 'DATA_RESTRICTED')]:
            Media(iri=Iri('demo:' + name), **{'dcterms:type': 'dcmitype:StillImage',
                'shared:mediaAccessMode': 'local', 'shared:protocol': 'iiif',
                'shared:assetId': name, 'shared:originalName': name + '.jpg',
                'shared:path': '/owned/' + name, 'shared:derivativeName': name + '-small.jpg',
                'shared:inStagingArea': 'demo:writearea', 'shared:inStagingFolder': 'demo:mediafolder',
                'shared:stagingStatus': 'shared:StagingStatusNew',
                'oldap:attachedToRole': {'demo:Writer': permission}}).create()
        for name, permission in [('mediaone', 4), ('mediatwo', 2), ('mediarestricted', 1)]:
            for route in ('id/' + name, 'iri/' + quote(base + name, safe='')):
                result = call('GET', '/data/mediaobject/' + route, headers=headers).json()
                claims = admin.token_codec.decode_media_token(result['token'])
                check('Media lookup ' + route + ' preserves metadata, grant and signed claims',
                      result['shared:originalName'] == name + '.jpg' and result['permval'] == permission
                      and claims['assetId'] == name and claims['permval'] == permission)
        path = '/data/demo/staging-folder-inventory?'
        query = {'folderIri': base + 'mediafolder', 'limit': 1}
        first = call('GET', path + urlencode(query), headers=headers).json()
        second = call('GET', path + urlencode({**query, 'cursor': first['nextCursor']}), headers=headers).json()
        entries = {item['mediaIri']: item for page in (first, second) for item in page['entries']}
        check('Inventory hydrates two visible media across pages and excludes restricted media',
              set(entries) == {base + 'mediaone', base + 'mediatwo'} and second['nextCursor'] is None)
        check('Inventory preserves per-entry titles and capabilities',
              entries[base + 'mediaone']['title'] == 'mediaone.jpg'
              and entries[base + 'mediaone']['canEditMetadata']
              and not entries[base + 'mediatwo']['canEditMetadata']
              and entries[base + 'mediatwo']['canDownloadOriginal'])
        prefix = Context(name=admin.context_name).sparql_context
        Catalogue = factory.createObjectInstance('shared:MediaObject')
        Catalogue(iri=Iri('demo:cataloguemedia'), **{'dcterms:type': 'dcmitype:StillImage',
            'shared:mediaAccessMode': 'external', 'shared:protocol': 'http',
            'shared:originalName': 'Catalogue image', 'shared:mediaUrl': 'https://example.org/image.jpg',
            'oldap:attachedToRole': {'demo:Writer': 'DATA_UPDATE'}}).create()
        # Import only the reference edge; the target itself was model-created.
        admin.update_query(prefix + 'INSERT DATA { GRAPH demo:data { demo:mediafolder shared:referencedMediaObject demo:cataloguemedia } }')
        mixed = call('GET', path + urlencode({'folderIri': base + 'mediafolder'}), headers=headers).json()
        reference = next(item for item in mixed['entries'] if item['kind'] == 'archiveReference')
        check('Hydrated archive reference permits moving but never editing/deleting the catalogue target',
              reference['title'] == 'Catalogue image' and reference['canMove']
              and not reference['canEditMetadata'] and not reference['canDeleteMedia']
              and not reference['canDownloadOriginal'])
        admin.update_query(prefix + 'DELETE DATA { GRAPH demo:data { demo:mediaone oldap:attachedToRole demo:Writer } }')
        for route in ('id/mediaone', 'iri/' + quote(base + 'mediaone', safe='')):
            call('GET', '/data/mediaobject/' + route, headers=headers, status=404)
        check('Orphaned media permission annotations cannot issue new tokens', True)
        fresh = call('GET', path + urlencode({'folderIri': base + 'mediafolder'}), headers=headers).json()
        check('Fresh inventory excludes a revoked membership despite its remaining annotation',
              {item['mediaIri'] for item in fresh['entries']} == {base + 'mediatwo', base + 'cataloguemedia'})
        # Imported duplicate IDs must fail before metadata from two resources
        # can be combined into a single signed capability.
        from oldaplib.src.helpers.jena_permission_write import permission_annotation
        admin.update_query(prefix + 'INSERT DATA { GRAPH demo:data { '
            'demo:duplicatemedia a shared:MediaObject ; shared:assetId "mediatwo" ; oldap:attachedToRole demo:Writer . '
            + permission_annotation('demo:duplicatemedia', 'oldap:attachedToRole', 'demo:Writer', 'oldap:DATA_VIEW')
            + ' } }')
        call('GET', '/data/mediaobject/id/mediatwo', headers=headers, status=400)
        check('Ambiguous visible asset IDs are rejected before token issuance', True)
        admin.update_query(prefix + 'INSERT DATA { GRAPH demo:data { '
            'demo:foreignmedia a demo:ForeignMedia ; shared:assetId "foreignmedia" ; oldap:attachedToRole demo:Writer . '
            + permission_annotation('demo:foreignmedia', 'oldap:attachedToRole', 'demo:Writer', 'oldap:DATA_VIEW')
            + ' } GRAPH <urn:unrelated:onto> { demo:ForeignMedia rdfs:subClassOf shared:MediaObject } }')
        call('GET', '/data/mediaobject/id/foreignmedia', headers=headers, status=404)
        check('Unrelated schema ancestry cannot turn a resource into visible media', True)
