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
