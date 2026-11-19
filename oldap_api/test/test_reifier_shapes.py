"""HTTP model CRUD with real library persistence on an isolated RDF dataset."""
from unittest.mock import patch

import pytest
from flask import Flask

from oldaplib.test.test_reifier_shape import DatasetConnection
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.project import Project
from oldaplib.src.xsd.xsd_date import Xsd_date
from oldap_api.views.datamodelling_views import datamodel_bp, process_property, _property_payload, property_modifier


@pytest.fixture
def client():
    con = DatasetConnection()
    project = Project(con=con, projectIri='https://example.org/project', projectShortName='example',
        namespaceIri=NamespaceIRI('https://example.org/ns/'), projectStart=Xsd_date('2026-01-01'))
    app = Flask(__name__)
    app.register_blueprint(datamodel_bp)
    with patch('oldaplib.src.cachesingleton.CacheSingletonRedis'), patch('oldap_api.authentication.Connection', return_value=con), patch.object(
        Project, 'read', return_value=project), patch(
        'oldaplib.src.resource_transaction.archive_coordination_enabled', return_value=False):
        yield app.test_client(), con, project


def test_http_shape_lifecycle_and_validation(client):
    http, con, _ = client
    url = '/admin/datamodel/example/reifier-shape/example:VisitShape'
    headers = {'Authorization': 'Bearer test'}
    payload = {'properties': [{'iri': 'example:dateTime', 'datatype': 'xsd:dateTime', 'minCount': 1, 'maxCount': 1}]}
    assert http.get(url).status_code == 401
    created = http.put(url, json=payload, headers=headers)
    assert created.status_code == 201, created.json
    assert created.json['properties'][0]['datatype'] == 'xsd:dateTime'
    assert http.put(url, json=payload, headers=headers).status_code == 409
    assert http.get(url, headers=headers).json == created.json
    payload['properties'][0]['maxCount'] = 2
    changed = http.post(url, json=payload, headers=headers)
    assert changed.status_code == 200, changed.json
    assert changed.json['properties'][0]['maxCount'] == 2
    invalid = {'properties': payload['properties'] * 2}
    assert http.post(url, json=invalid, headers=headers).status_code == 400
    assert http.delete(url, headers=headers).status_code == 204
    assert http.get(url, headers=headers).status_code == 404


def test_false_and_empty_reference_updates(client):
    _, con, project = client
    app = Flask(__name__)
    with app.test_request_context():
        prop = process_property(con, project, 'example:isAt', {'class': 'schema:Place',
            'reifierShapes': ['example:VisitShape'], 'reificationRequired': False})
        assert _property_payload(prop)['reificationRequired'] is False
        assert _property_payload(prop)['reifierShapes'] == ['example:VisitShape']
        response, status = property_modifier({'reifierShapes': [], 'reificationRequired': None}, prop)
        assert status == 200, response.json
        assert not prop.reifierShapes
        assert prop.reificationRequired is None
        _, status = property_modifier({'reificationRequired': 'false'}, prop)
        assert status == 400


def test_shape_write_requires_model_permission(client):
    http, con, _ = client
    con.userdata.inProject.clear()
    response = http.put('/admin/datamodel/example/reifier-shape/example:Forbidden',
        json={'properties': []}, headers={'Authorization': 'Bearer test'})
    assert response.status_code == 403
    assert len(con.dataset) == 0


def test_shared_superproperty_http_roundtrip_and_clear(client):
    http, con, _ = client
    headers = {'Authorization': 'Bearer test'}
    url = '/admin/datamodel/example/reifier-shape/example:Source'
    other = '/admin/datamodel/example/reifier-shape/example:Other'
    field = {'iri': 'example:source', 'datatype': 'xsd:string', 'subPropertyOf': 'dcterms:source'}
    assert http.put(url, json={'properties': [field]}, headers=headers).status_code == 201
    # A second use adopts the existing declaration without redefining it.
    minimal = {'iri': 'example:source', 'datatype': 'xsd:string'}
    response = http.put(other, json={'properties': [minimal]}, headers=headers)
    assert response.status_code == 201, response.json
    assert response.json['properties'][0]['subPropertyOf'] == 'dcterms:source'
    field['subPropertyOf'] = 'schema:citation'
    response = http.post(url, json={'properties': [field]}, headers=headers)
    assert response.status_code == 200, response.json
    assert http.get(other, headers=headers).json['properties'][0]['subPropertyOf'] == 'schema:citation'
    # Explicit null clears the shared relation, without deleting either field.
    field['subPropertyOf'] = None
    response = http.post(url, json={'properties': [field]}, headers=headers)
    assert response.status_code == 200, response.json
    assert 'subPropertyOf' not in http.get(other, headers=headers).json['properties'][0]
    field['subPropertyOf'] = 'dcterms:source'
    assert http.post(url, json={'properties': [field]}, headers=headers).status_code == 200
    assert http.post(url, json={'properties': []}, headers=headers).status_code == 200
    assert http.get(other, headers=headers).json['properties'][0]['subPropertyOf'] == 'dcterms:source'


def test_shape_cannot_redefine_a_foreign_predicate(client):
    http, con, _ = client
    response = http.put('/admin/datamodel/example/reifier-shape/example:Foreign',
        json={'properties': [{'iri': 'shared:source', 'datatype': 'xsd:string',
                              'subPropertyOf': 'dcterms:source'}]},
        headers={'Authorization': 'Bearer test'})
    assert response.status_code == 403, response.json
    assert len(con.dataset) == 0


def test_multiple_superproperties_http_roundtrip_preserves_constraints_and_clear(client):
    http, _, _ = client
    headers = {'Authorization': 'Bearer test'}
    url = '/admin/datamodel/example/reifier-shape/example:Multiple'
    parents = ['dcterms:coverage', 'dc:coverage']
    field = {'iri': 'example:temporal', 'datatype': 'xsd:string', 'subPropertyOf': parents}
    created = http.put(url, json={'properties': [field]}, headers=headers)
    assert created.status_code == 201, created.json
    assert created.json['properties'][0]['subPropertyOf'] == sorted(parents)
    assert http.get(url, headers=headers).json == created.json
    # Replacing a complete field with an unrelated constraint retains all parents.
    field['maxCount'] = 2
    updated = http.post(url, json={'properties': [field]}, headers=headers)
    assert updated.status_code == 200, updated.json
    assert updated.json['properties'][0]['subPropertyOf'] == sorted(parents)
    assert updated.json['properties'][0]['maxCount'] == 2
    # Singleton responses keep the legacy wire format; [] clears the entire set.
    field['subPropertyOf'] = ['dc:coverage']
    updated = http.post(url, json={'properties': [field]}, headers=headers)
    assert updated.status_code == 200, updated.json
    assert updated.json['properties'][0]['subPropertyOf'] == 'dc:coverage'
    field['subPropertyOf'] = []
    updated = http.post(url, json={'properties': [field]}, headers=headers)
    assert updated.status_code == 200, updated.json
    assert 'subPropertyOf' not in updated.json['properties'][0]


@pytest.mark.parametrize('invalid', [42, True, {}, ['dcterms:date', None], [42], 'invalid iri'])
def test_invalid_superproperty_inputs_are_client_errors(client, invalid):
    http, con, _ = client
    response = http.put('/admin/datamodel/example/reifier-shape/example:Invalid',
        json={'properties': [{'iri': 'example:source', 'datatype': 'xsd:string',
                              'subPropertyOf': invalid}]},
        headers={'Authorization': 'Bearer test'})
    assert response.status_code == 400, response.json
    assert len(con.dataset) == 0


def test_property_patch_accepts_multiple_parents_and_preserves_them_on_unrelated_updates(client):
    _, con, project = client
    app = Flask(__name__)
    with app.test_request_context():
        prop = process_property(con, project, 'example:source', {'datatype': 'xsd:string'})
        parents = ['dcterms:coverage', 'dc:coverage']
        response, status = property_modifier({'subPropertyOf': parents}, prop)
        assert status == 200, response.json
        assert _property_payload(prop)['subPropertyOf'] == sorted(parents)
        response, status = property_modifier({'maxCount': 2}, prop)
        assert status == 200, response.json
        assert _property_payload(prop)['subPropertyOf'] == sorted(parents)
        response, status = property_modifier({'subPropertyOf': ['dc:coverage', 42]}, prop)
        assert status == 400
        assert _property_payload(prop)['subPropertyOf'] == sorted(parents)
        response, status = property_modifier({'subPropertyOf': None}, prop)
        assert status == 200, response.json
        assert 'subPropertyOf' not in _property_payload(prop)


def test_model_resource_response_retains_imported_dcterms_parents(client):
    """Serialize real imported parents without consulting cached/live system models."""
    from pathlib import Path
    from rdflib import URIRef
    import oldaplib
    from oldaplib.src.datamodel import DataModel
    from oldaplib.src.resourceclass import ResourceClass

    http, con, project = client
    ontology_root = Path(oldaplib.__file__).parent / 'ontologies'
    for name in ('oldap.trig', 'shared.trig'):
        con.dataset.parse(ontology_root / name, format='trig')
    con.dataset.graph(URIRef('http://purl.org/dc/terms/onto')).parse(
        ontology_root / 'standard/dcterms.ttl', format='turtle')
    system = Project(con=con, projectIri='http://oldap.org/base#SystemProject',
        projectShortName='oldap', namespaceIri=NamespaceIRI('http://oldap.org/base#'),
        projectStart=Xsd_date('2026-01-01'))
    shared = Project(con=con, projectIri='http://oldap.org/shared#SharedProject',
        projectShortName='shared', namespaceIri=NamespaceIRI('http://oldap.org/shared#'),
        projectStart=Xsd_date('2026-01-01'))
    prop = process_property(con, project, 'dcterms:temporal', {'datatype': 'xsd:string'})
    prop.read_owl()
    # ResourceClass imports its cache independently and resolves oldap:Thing
    # during construction. Use the bundled system graph and explicit projects.
    with patch.object(ResourceClass, '_sysproject', system), patch.object(
            ResourceClass, '_sharedproject', shared), patch(
            'oldaplib.src.resourceclass.CacheSingletonRedis') as resource_cache, patch(
            'oldaplib.src.propertyclass.CacheSingletonRedis') as property_cache:
        resource_cache.return_value.get.return_value = None
        property_cache.return_value.get.return_value = None
        resource = ResourceClass(con=con, project=project, owlclass_iri='example:Resource', properties=[prop])
        model = DataModel(con=con, project=project, resclasses=[resource])
        with patch('oldap_api.views.datamodelling_views.DataModel.read', return_value=model):
            response = http.get('/admin/datamodel/example', headers={'Authorization': 'Bearer test'})
    assert response.status_code == 200, response.json
    field = response.json['resources'][0]['properties'][0]
    assert field['iri'] == 'dcterms:temporal'
    assert field['subPropertyOf'] == ['dc:coverage', 'dcterms:coverage']


def test_foreign_multiple_parents_survive_local_field_changes(client):
    from rdflib import URIRef
    from rdflib.namespace import RDFS

    http, con, _ = client
    graph = con.dataset.graph(URIRef('http://purl.org/dc/terms/onto'))
    predicate = URIRef('http://purl.org/dc/terms/temporal')
    triples = {(predicate, RDFS.subPropertyOf, URIRef(parent)) for parent in (
        'http://purl.org/dc/elements/1.1/coverage', 'http://purl.org/dc/terms/coverage')}
    for triple in triples:
        graph.add(triple)
    headers = {'Authorization': 'Bearer test'}
    url = '/admin/datamodel/example/reifier-shape/example:Imported'
    field = {'iri': 'dcterms:temporal', 'datatype': 'xsd:string'}
    response = http.put(url, json={'properties': [field]}, headers=headers)
    assert response.status_code == 201, response.json
    field = response.json['properties'][0]
    # Use the write-side keys when returning the full definition.
    field = {key: field[key] for key in ('iri', 'datatype', 'subPropertyOf')}
    field['maxCount'] = 2
    response = http.post(url, json={'properties': [field]}, headers=headers)
    assert response.status_code == 200, response.json
    assert set(graph) == triples
    field['subPropertyOf'] = ['dc:coverage']
    response = http.post(url, json={'properties': [field]}, headers=headers)
    assert response.status_code == 403, response.json
    assert set(con.dataset.graph(graph.identifier)) == triples


def test_legacy_cached_scalar_parent_serializes_without_losing_compatibility(client):
    from oldaplib.src.enums.propertyclassattr import PropClassAttr
    from oldaplib.src.xsd.iri import Iri

    _, con, project = client
    prop = process_property(con, project, 'example:source', {'datatype': 'xsd:string'})
    # Simulate a pre-upgrade cached object bypassing current setter normalization.
    prop._attributes[PropClassAttr.SUBPROPERTY_OF] = Iri('dcterms:source')
    assert _property_payload(prop)['subPropertyOf'] == 'dcterms:source'
