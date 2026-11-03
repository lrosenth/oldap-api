"""Import the complete migration YAML into an owned, initially empty Jena project.

Only the GraphDB-specific Lucene connectors are skipped. All class declarations,
external-ontology registrations and taxonomy files go through the real tools CLI
and normal HTTP endpoints. Synthetic data exercises the canonical part direction;
this is not a production-data migration.
"""
import json
from pathlib import Path
import subprocess

import yaml


def check_fasnacht_model(call, check, create_connection, base, password, output, *, real_export=False):
    """Check full model import, repeat planning and permission-filtered parts.

    Args:
        call: Owned authenticated HTTP request helper.
        check: Probe acceptance recorder.
        create_connection: Normal Jena backend factory.
        base: Owned API origin.
        password: Owned fixture administrator password.
        output: Private output directory; never a live project directory.
    """
    workspace = Path(__file__).resolve().parents[3]
    source = workspace / 'oldap-tools/fasnacht/fasnacht-onto.yaml'
    wanted = yaml.safe_load(source.read_text())['ontology']
    cli = workspace / 'oldap-tools/.venv/bin/oldap-tools'

    def load(*args):
        process = subprocess.run([str(cli), '--api', base, '--user', 'actor', '--password', password,
            'ontology', 'load', '-i', str(source), '--connectors', 'skip', *map(str, args)],
            capture_output=True, text=True, timeout=900)
        with (output / 'fasnacht-tools.log').open('a') as log:
            log.write(process.stdout + process.stderr)
        if process.returncode:
            raise AssertionError('Fasnacht import failed; inspect private fasnacht-tools.log')
        return process.stdout

    load('--dry-run')
    check('Full Fasnacht planning does not create the project',
          call('GET', '/admin/project/fasnacht', status=404).status_code == 404)
    load('--backup-out', output / 'fasnacht-before.zip')
    actual = call('GET', '/admin/datamodel/fasnacht').json()
    resources = {resource['iri']: resource for resource in actual['resources']}
    check('Full Fasnacht import creates every declared resource class',
          set(resources) == set(wanted['classes']))
    for name in ('fasnacht:Place', 'fasnacht:CarnivalThing'):
        properties = {p['iri']: p for p in resources[name]['properties']}
        check(name + ' uses only the canonical isPartOf field',
              'dcterms:hasPart' not in properties and
              'dcterms:isPartOf' in properties and not properties['dcterms:isPartOf'].get('inverseOf'))
    archive = next(p for p in resources['fasnacht:ArchiveObject']['properties'] if p['iri'] == 'fasnacht:archiveUnit')
    check('Full Fasnacht archive assignment has no inverse axiom', not archive.get('inverseOf'))
    check('Full Fasnacht replay plans zero changes', 'Planned 0' in load('--dry-run'))

    con = create_connection(userId='actor', credentials=password)
    if real_export:
        from check_fasnacht_export import check_fasnacht_export
        check_fasnacht_export(call, check, con, workspace, output)
        return
    prefix = ('PREFIX fasnacht: <http://fasnacht.digital/ns/> '
              'PREFIX dcterms: <http://purl.org/dc/terms/> '
              'PREFIX schema: <https://schema.org/> '
              'PREFIX oldap: <http://oldap.org/base#> '
              'PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> ')
    call('PUT', '/admin/role/fasnacht/ProbeReader', {'label': ['Probe reader@en']})
    con.update_query(prefix + '''INSERT DATA {
      GRAPH oldap:admin { <https://example.org/actor> oldap:hasRole fasnacht:ProbeReader }
      GRAPH fasnacht:data {
        fasnacht:ProbeParent a fasnacht:CarnivalEvent ; schema:name "Parent"@en ;
          dcterms:hasPart fasnacht:ProbeChild, fasnacht:ProbeHidden .
        fasnacht:ProbeChild a fasnacht:CarnivalEvent ; schema:name "Child"@en ;
          oldap:attachedToRole fasnacht:ProbeReader .
        fasnacht:ProbeHidden a fasnacht:CarnivalEvent ; schema:name "Hidden"@en .
        <urn:fasnacht:probe:grant> rdf:reifies <<( fasnacht:ProbeChild oldap:attachedToRole fasnacht:ProbeReader )>> ;
          oldap:hasDataPermission oldap:DATA_VIEW .
      }
    }''')
    queries = workspace / 'oldaplib/tools/migration/sparql'
    con.transaction_start()
    try:
        issues = con.transaction_query((queries / 'fasnacht-parts-preflight.rq').read_text())['results']['bindings']
        if issues:
            raise AssertionError('Owned parts fixture failed preflight')
        con.transaction_update((queries / 'fasnacht-parts.ru').read_text())
        con.transaction_commit()
    except Exception:
        if con.in_transaction():
            con.transaction_abort()
        raise
    request = {'includeProperties': ['schema:name'], 'filter': [{
        'property': 'dcterms:isPartOf', 'op': '==', 'value': 'fasnacht:ProbeParent', 'type': 'iri'}]}
    rows = call('POST', '/data/search/fasnacht/class/fasnacht:CarnivalThing', request).json()
    check('Full-model reverse API lookup returns only the readable child',
          len(rows) == 1 and 'ProbeChild' in json.dumps(rows) and 'ProbeHidden' not in json.dumps(rows))
    check('Full-model conversion removes legacy hasPart data', not con.query(prefix +
          'ASK { GRAPH fasnacht:data { ?s dcterms:hasPart ?o } }')['boolean'])
