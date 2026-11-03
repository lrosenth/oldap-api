"""Exercise archival assignment model migration through the real HTTP API.

Uses owned demo resources and the actual Fasnacht YAML property's target and
cardinality. The tools CLI performs the model change, including backup and replay;
no SPARQL schema cleanup substitutes for the API update under test.
"""
import json
from pathlib import Path

import yaml


def check_archive_assignment(call, check, create_connection, tools_command, output):
    """Verify explicit inverse removal, unchanged instances and repeatable import.

    Args:
        call: Authenticated HTTP fixture request helper.
        check: Acceptance recorder that raises on failure.
        create_connection: Normal backend factory for readback and data fixtures.
        tools_command: Real tools CLI subprocess runner against the owned API.
        output: Private acceptance directory for YAML and pre-change backup.
    """
    source = Path(__file__).resolve().parents[3] / 'oldap-tools/fasnacht/fasnacht-onto.yaml'
    model = yaml.safe_load(source.read_text())['ontology']
    prop = next(p for p in model['classes']['fasnacht:ArchiveObject']['properties']
                if p['iri'] == 'fasnacht:archiveUnit')
    assert prop['inverse_of'] is None
    route = '/admin/datamodel/demo/demo:ArchiveObject'
    call('PUT', route, {'superclass': ['oldap:Thing'], 'properties': [{
        'iri': 'demo:archiveUnit', 'class': prop['to_class'],
        'maxCount': prop['max_count'], 'inverseOf': 'schema:about'}]})
    con = create_connection(userId='actor', credentials='owned-fixture-password')
    prefix = ('PREFIX demo: <https://example.org/demo/> '
              'PREFIX shared: <http://oldap.org/shared#> '
              'PREFIX schema: <https://schema.org/> '
              'PREFIX owl: <http://www.w3.org/2002/07/owl#> ')
    # Seed data only. Existing Writer grant belongs to the owned CRUD fixture.
    con.update_query(prefix + '''INSERT DATA { GRAPH demo:data {
        demo:assignmentUnit a shared:ArchiveUnit .
        demo:subjectUnit a shared:ArchiveUnit ; schema:about demo:subjectObject .
    } }''')
    grants = {'oldap:attachedToRole': {'demo:Writer': 'DATA_VIEW'}}
    call('PUT', '/data/demo/demo:ArchiveObject', {
        'iri': 'assignedObject', 'demo:archiveUnit': 'demo:assignmentUnit', **grants})
    call('PUT', '/data/demo/demo:ArchiveObject', {'iri': 'subjectObject', **grants})
    check('Archive API legacy model exposes the subject as an inferred assignment',
          'demo:subjectUnit' in call('GET', '/data/demo/demo:subjectObject').text)
    before = call('GET', '/data/demo/demo:assignedObject').json()
    instances_before = con.query(prefix + 'SELECT ?s ?p ?o WHERE { GRAPH demo:data { ?s ?p ?o } }')['results']['bindings']
    desired = {'ontology': {'project': {'shortname': 'demo', 'namespace': 'https://example.org/demo/'},
        'classes': {'demo:ArchiveObject': {'properties': [{
            'iri': 'demo:archiveUnit', 'to_class': prop['to_class'],
            'max_count': prop['max_count'], 'inverse_of': prop['inverse_of']} ]}}}}
    target = output / 'archive-assignment.yaml'
    target.write_text(json.dumps(desired))
    check('Archive tools dry run plans the inverse removal',
          'Planned 1' in tools_command('load', '-i', target, '--dry-run'))
    tools_command('load', '-i', target, '--backup-out', output / 'archive-before.zip')
    model_after = call('GET', '/admin/datamodel/demo').json()
    resource = next(r for r in model_after['resources'] if r['iri'] == 'demo:ArchiveObject')
    field = next(p for p in resource['properties'] if p['iri'] == 'demo:archiveUnit')
    check('Archive API model update removes inverse metadata and keeps cardinality',
          not field.get('inverseOf') and field['maxCount'] == 1)
    check('Archive API model update removes the persisted OWL axiom', not con.query(prefix +
        'ASK { GRAPH demo:onto { demo:archiveUnit owl:inverseOf schema:about } }')['boolean'])
    check('Archive API direct assignment response remains unchanged',
          call('GET', '/data/demo/demo:assignedObject').json() == before)
    check('Archive API no longer derives assignment from a subject link',
          'demo:subjectUnit' not in call('GET', '/data/demo/demo:subjectObject').text)
    after = con.query(prefix + 'SELECT ?s ?p ?o WHERE { GRAPH demo:data { ?s ?p ?o } }')['results']['bindings']
    check('Archive API model migration preserves every instance triple',
          sorted(map(lambda r: json.dumps(r, sort_keys=True), after)) ==
          sorted(map(lambda r: json.dumps(r, sort_keys=True), instances_before)))
    check('Archive tools migration replay plans zero writes',
          'Planned 0' in tools_command('load', '-i', target, '--dry-run'))
