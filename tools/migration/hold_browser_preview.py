"""Keep an owned real-export API alive for a bounded manual browser rehearsal."""
from contextlib import ExitStack
import json
import time


def hold_browser_preview(call, create_connection, base, output, token, *, media_root=None, asset_service_root=None, fulltext_preview=False):
    """Provision the public fixture identity, publish readiness and await stop.

    Only disposable admin metadata changes. Imported instance grants are left
    unchanged. Creating ``browser-stop`` in output ends the preview; a 20-minute
    deadline also closes the enclosing runner and its owned services.
    """
    con = create_connection(token=token)
    # The real export includes a Chama role, but not its admin project.
    # Provision only its source namespace in this disposable fixture so new
    # tokens can encode that role as the QName required by the existing codec.
    from oldaplib.src.helpers.context import Context
    from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
    Context(name='DEFAULT')['chama'] = NamespaceIRI('https://chama.salsah.org/ns/')
    con.update_query('''PREFIX oldap: <http://oldap.org/base#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        INSERT DATA { GRAPH oldap:admin {
          <urn:browser-chama-project> a oldap:Project ; oldap:projectShortName "chama"^^xsd:NCName ;
              oldap:namespaceIri <https://chama.salsah.org/ns/> ; oldap:projectStart "2024-01-01"^^xsd:date .
          oldap:Unknown a oldap:Role ; oldap:inProject oldap:SystemProject .
          <https://example.org/unknown> oldap:hasRole oldap:Unknown .
          <urn:browser-unknown-role> rdf:reifies <<( <https://example.org/unknown> oldap:hasRole oldap:Unknown )>> ;
              oldap:hasDefaultDataPermission oldap:DATA_VIEW .
        } }''')
    (output / 'audit-role-metadata.json').write_text(json.dumps(call('GET', '/admin/user/actor').json().get('hasRole'), indent=2))
    token = call('POST', '/admin/auth/unknown', {'password': ''}).json()['accessToken']
    public = {'Authorization': 'Bearer ' + token}
    call('GET', '/admin/user/unknown', headers=public)
    audit_token = call('POST', '/admin/auth/actor', {'password': 'owned-fixture-password'}).json()['accessToken']
    call('GET', '/admin/user/actor', headers={'Authorization': 'Bearer ' + audit_token})
    comparison = json.loads((output / 'real-data-comparison.json').read_text())
    parent = next(row['parent'] for row in comparison['api_comparisons'] if row['expected'])
    detail = call('GET', '/data/fasnacht/' + parent).json()
    call('PUT', '/data/fasnacht/fasnacht:CarnivalEvent', {
        'iri': 'browser-private-child', 'schema:name': ['Jena internes Prüfobjekt@de'],
        'dcterms:isPartOf': parent,
        'fasnacht:publicationStatus': detail['fasnacht:publicationStatus'][0],
        'oldap:attachedToRole': {'oldap:WriterRecoveryOperator': 'DATA_VIEW'}})
    info = {'api_url': base, 'public_identity': 'unknown',
            'public_role': 'oldap:Unknown', 'audit_identity': 'actor',
            'private_test_child': 'fasnacht:browser-private-child',
            'parents': comparison['api_comparisons'], 'stop_file': str(output / 'browser-stop'),
            'scope': 'Disposable real-export target; audit actor has source role identities; public identity only oldap:Unknown. No source account restoration.'}
    if fulltext_preview:
        from check_fasnacht_fulltext import check_fasnacht_fulltext
        check_fasnacht_fulltext(call, con, base, output, public, {'Authorization': 'Bearer ' + audit_token})
        info['fulltext_enabled'] = True
    with ExitStack() as stack:
        if media_root is not None:
            from preview_media import preview_media
            info['media_url'] = stack.enter_context(preview_media(media_root, output, call, public, con))
        if asset_service_root is not None:
            from preview_assets import preview_assets
            info['media_url'] = stack.enter_context(preview_assets(asset_service_root, media_root, output, call, public, base, info['media_url']))
        (output / 'browser-ready.json').write_text(json.dumps(info, indent=2) + '\n')
        print('BROWSER_READY', base, flush=True)
        deadline = time.monotonic() + 1200
        while not (output / 'browser-stop').exists() and time.monotonic() < deadline:
            time.sleep(1)
