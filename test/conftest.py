import os
from time import sleep

import pytest
import jwt
from oldaplib.src.connection import Connection
from oldaplib.src.datamodel import DataModel
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_qname import Xsd_QName

from factory import factory


class ConnectionManager:
    _jwt_secret: str

    def __init__(self, jwt_secret: str):
        self._jwt_secret = jwt_secret
        Connection.jwtkey = jwt_secret

    @property
    def jwt_secret(self) -> str:
        return self._jwt_secret

@pytest.fixture
def connection_manager():
    cmanager = ConnectionManager("ABCDEFGHIJKLMNOPQRESTUVWXYZ0123456")
    return cmanager

@pytest.fixture
def app():
    app = factory()
    app.config.update({
        'TESTING': True,
    })
    con = Connection(server='http://localhost:7200',
                     repo="oldap",
                     userId="rosenth",
                     credentials="RioGrande",
                     context_name="DEFAULT")
    con.clear_graph(Xsd_QName('oldap:admin'))
    con.clear_graph(Xsd_QName('hyha:shacl'))
    con.clear_graph(Xsd_QName('hyha:onto'))
    con.upload_turtle(os.environ['OLDAPBASE'] + "/oldaplib/oldaplib/ontologies/admin.trig")
    sleep(1)
    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def token_headers(app, client):
    login = client.post('/admin/auth/rosenth', json={'password': 'RioGrande'})
    token = login.json['token']
    headers = {
        'Authorization': f'Bearer {token}'
    }
    return token, headers


@pytest.fixture()
def testuser(client, token_headers):
    header = token_headers[1]

    client.put('/admin/user/rosman', json={
        "givenName": "Manuel",
        "familyName": "Rosenthaler",
        "password": "kappa1234",
        "inProjects": [
            {
                "project": "http://www.salsah.org/version/2.0/SwissBritNet",
                "permissions": [
                    "ADMIN_USERS"
                ]
            },
            {
                "project": "oldap:HyperHamlet",
                "permissions": [
                    "ADMIN_USERS"
                ]
            }
        ],
        "hasPermissions": [
            "GenericView"
        ]
    }, headers=header)

    yield

    client.delete('/admin/user/rosman', headers=header)


@pytest.fixture()
def testproject(client, token_headers):
    header = token_headers[1]

    client.put('/admin/project/testproject', json={
        "projectIri": "http://unittest.org/project/testproject",
        "label": ["unittest@en", "unittest@de"],
        "comment": ["For testing@en", "Für Tests@de"],
        "namespaceIri": "http://unitest.org/project/unittest#",
        "projectStart": "1993-04-05",
        "projectEnd": "2000-01-10"
    }, headers=header)

    yield

    client.delete('/admin/project/testproject', headers=header)


@pytest.fixture()
def testpermissionset(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/permissionset/oldap/testpermissionset', json={
        "label": ["testPerm@en", "test@de"],
        "comment": ["For testing@en", "Für Tests@de"],
        "givesPermission": "DATA_UPDATE",
    }, headers=header)

    yield

    client.delete('/admin/permissionset/testpermission', headers=header)


@pytest.fixture()
def testemptydatamodel(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/datamodel/hyha', json={}, headers=header)

    yield


@pytest.fixture()
def testhalffulldatamodel(client, token_headers, testemptydatamodel):
    header = token_headers[1]

    response = client.put('/admin/datamodel/hyha/property', json={
        "iri": "hyha:testProp",
        "datatype": "rdf:langString",
        "name": ["Test Property@en", "Test Feld@de"],
        "description": ["Test Feld Beschreibung@de"],
        "uniqueLang": True,
        "minLength": 1,
        "maxLength": 50,
        "languageIn": ["en", "fr", "it", "de"],
    }, headers=header)

    yield


@pytest.fixture()
def testfulldatamodel(client, token_headers, testemptydatamodel):
    header = token_headers[1]

    response = client.put('/admin/datamodel/hyha/property', json={
        "iri": "hyha:testProp2",
        "subPropertyOf": "hyha:testProp",
        "datatype": "rdf:langString",
        "name": ["Test Property@en", "Test Feld@de"],
        "description": ["Test Feld Beschreibung@de"],
        "languageIn": ["en", "fr", "it", "de"],
        "uniqueLang": True,
        "in": ["Kappa", "Gaga", "gugus"],
        "minLength": 1,
        "maxLength": 50,
        # "pattern": "^[\w\.-]+@[a-zA-Z\d-]+(\.[a-zA-Z\d-]+)*\.[a-zA-Z]{2,}$",
        "minExclusive": 5.5,
        "minInclusive": 5.5,
        "maxExclusive": 5.5,
        "maxInclusive": 5.5,
        "lessThan": "hyha:testProp",
        "lessThanOrEquals": "hyha:testProp"
    }, headers=header)

    yield

