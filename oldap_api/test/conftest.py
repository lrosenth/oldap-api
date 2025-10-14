import os
from pathlib import Path
from time import sleep

import pytest
from oldaplib.src.connection import Connection
from oldaplib.src.helpers.context import Context
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldap_api.factory import factory


class ConnectionManager:
    _jwt_secret: str

    def __init__(self, jwt_secret: str):
        self._jwt_secret = jwt_secret
        os.environ['OLDAP_JWT_SECRET'] = jwt_secret

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

    cfg = os.getenv("APP_ENV", "Dev")
    app.config.from_object(f"oldap_api.config.{cfg}")

    uploaddir = Path(app.config['UPLOAD_FOLDER'])
    if not uploaddir.exists():
        uploaddir.mkdir()

    tmpdir = Path(app.config['TMP_FOLDER'])
    if not tmpdir.exists():
        tmpdir.mkdir()

    app.config.update({
        'TESTING': True
    })
    con = Connection(userId="rosenth",
                     credentials="RioGrande",
                     context_name="DEFAULT")
    context = Context(name="DEFAULT")
    context['hyha'] = NamespaceIRI('http://hyperhamlet.unibas.ch/')
    con.clear_graph(Xsd_QName('oldap:admin'))
    con.clear_graph(Xsd_QName('hyha:shacl'))
    con.clear_graph(Xsd_QName('hyha:onto'))
    con.clear_graph(Xsd_QName('hyha:lists'))
    con.clear_graph(Xsd_QName('hyha:data'))
    con.upload_turtle(os.environ['OLDAPBASE'] + "/oldaplib/oldaplib/ontologies/admin.trig")
    con.upload_turtle(os.environ['OLDAPBASE'] + "/oldaplib/oldaplib/ontologies/admin-testing.trig")
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
def bareboneuser(client, token_headers):
    header = token_headers[1]

    client.put('/admin/user/simple', json={
        "givenName": "Simple",
        "familyName": "User",
        "email": "simple.user@test.com",
        "password": "kappa1234"
    }, headers=header)

    yield

    client.delete('/admin/user/simple', headers=header)

@pytest.fixture()
def testuser(client, token_headers):
    header = token_headers[1]

    client.put('/admin/user/rosman', json={
        "givenName": "Manuel",
        "familyName": "Rosenthaler",
        "email": "manuel.rosenthaler@unibas.ch",
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
def testhalffulldatamodelstandaloneprop(client, token_headers, testemptydatamodel):
    header = token_headers[1]

    response = client.put('/admin/datamodel/hyha/property/hyha:testProp', json={
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
def testfulldatamodelstandaloneproplangstring(client, token_headers, testemptydatamodel):
    header = token_headers[1]

    response = client.put('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "subPropertyOf": "hyha:testProp",
        "datatype": "rdf:langString",
        "name": ["Test Property@en", "Test Feld@de"],
        "description": ["Test Feld Beschreibung@de"],
        "languageIn": ["en", "fr", "it", "de"],
        "uniqueLang": True,
        "minLength": 1,
        "maxLength": 50,
        "pattern": r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$",
        "minExclusive": 5.5,
        "minInclusive": 5.5,
        "maxExclusive": 5.5,
        "maxInclusive": 5.5,
        "lessThan": "hyha:testProp",
        "lessThanOrEquals": "hyha:testProp"
    }, headers=header)

    yield

@pytest.fixture()
def testfulldatamodelstandalonepropstring(client, token_headers, testemptydatamodel):
    header = token_headers[1]

    response = client.put('/admin/datamodel/hyha/property/hyha:testProp3', json={
        "subPropertyOf": "hyha:testProp",
        "datatype": "xsd:string",
        "name": ["Test Property@en", "Test Feld@de"],
        "description": ["Test Feld Beschreibung@de"],
        "inSet": ["Kappa", "Gaga", "gugus"],
        "minLength": 1,
        "maxLength": 50,
        "pattern": r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$",
        "minExclusive": 5.5,
        "minInclusive": 5.5,
        "maxExclusive": 5.5,
        "maxInclusive": 5.5,
        "lessThan": "hyha:testProp",
        "lessThanOrEquals": "hyha:testProp"
    }, headers=header)

    yield


@pytest.fixture()
def testfulldatamodeltwostandaloneprop(client, token_headers, testemptydatamodel):
    header = token_headers[1]

    response = client.put('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "subPropertyOf": "hyha:testProp",
        "datatype": "rdf:langString",
        "name": ["Test Property@en", "Test Feld@de"],
        "description": ["Test Feld Beschreibung@de"],
        "languageIn": ["en", "fr", "it", "de"],
        "uniqueLang": True,
        "inSet": ["Kappa", "Gaga", "gugus"],
        "minLength": 1,
        "maxLength": 50,
        "pattern": r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$",
        "minExclusive": 5.5,
        "minInclusive": 5.5,
        "maxExclusive": 5.5,
        "maxInclusive": 5.5,
        "lessThan": "hyha:testProp",
        "lessThanOrEquals": "hyha:testProp"
    }, headers=header)

    response = client.put('/admin/datamodel/hyha/property/hyha:testProp3', json={
        "subPropertyOf": "hyha:testProp",
        "datatype": "rdf:langString",
        "name": ["Second Test Property@en", "Zweite Test Feld@de"],
        "description": ["Test Feld Beschreibung@de", "zweite testfeld beschreibung@en"],
        "languageIn": ["en", "fr", "it", "de"],
        "uniqueLang": True,
        "inSet": ["Kappa", "Gaga", "gugus"],
        "minLength": 1,
        "maxLength": 50,
        "pattern": r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$",
        "minExclusive": 5.5,
        "minInclusive": 5.5,
        "maxExclusive": 5.5,
        "maxInclusive": 5.5,
        "lessThan": "hyha:testProp",
        "lessThanOrEquals": "hyha:testProp"
    }, headers=header)


    yield


@pytest.fixture()
def testfulldatamodelresourcesimple(client, token_headers, testemptydatamodel):
    header = token_headers[1]

    response = client.put('/admin/datamodel/hyha/hyha:SimpleSheep', json={
        "label": [
            "Eine Buchseite@de",
            "A page of a book@en"
        ],
        "comment": [
            "Eine Buchseite@de",
            "A page of a book@en"
        ],
        "closed": True,
        "hasProperty": [
            {
                "property": {
                    "iri": "hyha:testProp3",
                    "datatype": "xsd:string",
                    "name": ["Test Property@en", "Test Feld@de"],
                    "description": ["Test Feld Beschreibung@de"],
                },
                "maxCount": 1,
                "minCount": 1,
                "order": 1
            },
        ]
    }, headers=header)

    yield

@pytest.fixture()
def testfulldatamodelresource(client, token_headers, testemptydatamodel):
    header = token_headers[1]

    response = client.put('/admin/datamodel/hyha/hyha:Sheep', json={
        # "superclass": "hyha:Animal",
        "label": [
            "Eine Buchseite@de",
            "A page of a book@en"
        ],
        "comment": [
            "Eine Buchseite@de",
            "A page of a book@en"
        ],
        "closed": True,
        "hasProperty": [
            {
                "property": {
                    "iri": "hyha:testProp2",
                    "subPropertyOf": "hyha:testProp",
                    "datatype": "rdf:langString",
                    "name": ["Test Property@en", "Test Feld@de"],
                    "description": ["Test Feld Beschreibung@de"],
                    "languageIn": ["en", "fr", "it", "de"],
                    "uniqueLang": True,
                    "inSet": ["Kappa", "Gaga", "gugus"],
                    "minLength": 1,
                    "maxLength": 50,
                    "pattern": r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$",
                    "minExclusive": 5.5,
                    "minInclusive": 5.5,
                    "maxExclusive": 5.5,
                    "maxInclusive": 5.5,
                    "lessThan": "hyha:testProp",
                    "lessThanOrEquals": "hyha:testProp"
                },
                "maxCount": 3,
                "minCount": 1,
                "order": 1
            },
        ]
    }, headers=header)

    yield

@pytest.fixture()
def testfulldatamodelresourcesuperclasses(client, token_headers, testemptydatamodel):
    header = token_headers[1]

    response = client.put('/admin/datamodel/hyha/hyha:Mammal', json={
        "label": [
            "Säugetier@de",
            "Mammal@en"
        ],
        "closed": True,
        "hasProperty": [
            {
                "property": {
                    "iri": "hyha:mammalName",
                    "datatype": "xsd:string",
                    "name": ["Mammal name@en", "Säugetiername@de"],
                },
                "order": 1
            },
        ]
    }, headers=header)

    response = client.put('/admin/datamodel/hyha/hyha:Lion', json={
        "label": [
            "Löwe@de",
            "Lion@en"
        ],
        "superclass": ["hyha:Mammal", "dcterms:Predator"],
        "closed": True,
        "hasProperty": [
            {
                "property": {
                    "iri": "hyha:preyScheme",
                    "datatype": "xsd:string",
                    "name": ["Prey scheme@en", "Beuteschema@de"],
                },
                "order": 1
            },
        ]
    }, headers=header)

    yield

@pytest.fixture()
def testfulldatamodelresourcewithstandalone(client, token_headers, testemptydatamodel):
    header = token_headers[1]


    response = client.put('/admin/datamodel/hyha/property/hyha:testPropAdd', json={
        "subPropertyOf": "hyha:testProp",
        "datatype": "rdf:langString",
        "name": ["Test Property@en", "Test Feld@de"],
        "description": ["Test Feld Beschreibung@de"],
        "languageIn": ["en", "fr", "it", "de"],
        "uniqueLang": True,
        "inSet": ["Kappa", "Gaga", "gugus"],
        "minLength": 1,
        "maxLength": 50,
        "pattern": r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$",
        "minExclusive": 5.5,
        "minInclusive": 5.5,
        "maxExclusive": 5.5,
        "maxInclusive": 5.5,
        "lessThan": "hyha:testProp",
        "lessThanOrEquals": "hyha:testProp"
    }, headers=header)

    response = client.put('/admin/datamodel/hyha/hyha:Sheep', json={
        # "superclass": "hyha:Animal",
        "label": [
            "Eine Buchseite@de",
            "A page of a book@en"
        ],
        "comment": [
            "Eine Buchseite@de",
            "A page of a book@en"
        ],
        "closed": True,
        "hasProperty": [
            {
                "property": {
                    "iri": "hyha:testProp2",
                    "subPropertyOf": "hyha:testProp",
                    "datatype": "rdf:langString",
                    "name": ["Test Property@en", "Test Feld@de"],
                    "description": ["Test Feld Beschreibung@de"],
                    "languageIn": ["en", "fr", "it", "de"],
                    "uniqueLang": True,
                    "inSet": ["Kappa", "Gaga", "gugus"],
                    "minLength": 1,
                    "maxLength": 50,
                    "pattern": r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$",
                    "minExclusive": 5.5,
                    "minInclusive": 5.5,
                    "maxExclusive": 5.5,
                    "maxInclusive": 5.5,
                    "lessThan": "hyha:testProp",
                    "lessThanOrEquals": "hyha:testProp"
                },
                "maxCount": 3,
                "minCount": 1,
                "order": 1
            },
            # {
            #     "property": "hyha:testProp2",
            #     "minCount": 1,
            #     "maxCount": 1,
            #     "order": 2
            # }
        ]
    }, headers=header)

    yield


@pytest.fixture()
def testemptyhlist(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/hlist/hyha/testhlist', json={
        "prefLabel": ["testlabel@en"],
        "definition": ["testdefinition@en"]
    }, headers=header)

    yield

@pytest.fixture()
def testfullhlist(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/hlist/hyha/testfullhlist', json={
        "prefLabel": ["testlabel@en"],
        "definition": ["testdefinition@en"]
    }, headers=header)

    response = client.put('/admin/hlist/hyha/testfullhlist/nodeA', json={
        "prefLabel": ["testrootnodelabel@en"],
        "definition": ["testrootnodedefinition@en"],
        "position": "root"
    }, headers=header)

    response = client.put('/admin/hlist/hyha/testfullhlist/nodeB', json={
        "prefLabel": ["testrootnodelabel@en"],
        "definition": ["testrootnodedefinition@en"],
        "position": "rightOf",
        "refnode": "nodeA"
    }, headers=header)

    response = client.put('/admin/hlist/hyha/testfullhlist/nodeC', json={
        "prefLabel": ["testrootnodelabel@en"],
        "definition": ["testrootnodedefinition@en"],
        "position": "rightOf",
        "refnode": "nodeB"
    }, headers=header)

    response = client.put('/admin/hlist/hyha/testfullhlist/nodeBA', json={
        "prefLabel": ["testrootnodelabel@en"],
        "definition": ["testrootnodedefinition@en"],
        "position": "belowOf",
        "refnode": "nodeB"
    }, headers=header)

    response = client.put('/admin/hlist/hyha/testfullhlist/nodeBB', json={
        "prefLabel": ["testrootnodelabel@en"],
        "definition": ["testrootnodedefinition@en"],
        "position": "rightOf",
        "refnode": "nodeBA"
    }, headers=header)

    response = client.put('/admin/hlist/hyha/testfullhlist/nodeBC', json={
        "prefLabel": ["testrootnodelabel@en"],
        "definition": ["testrootnodedefinition@en"],
        "position": "rightOf",
        "refnode": "nodeBB"
    }, headers=header)

    response = client.put('/admin/hlist/hyha/testfullhlist/nodeBBA', json={
        "prefLabel": ["testrootnodelabel@en"],
        "definition": ["testrootnodedefinition@en"],
        "position": "belowOf",
        "refnode": "nodeBB"
    }, headers=header)

    response = client.put('/admin/hlist/hyha/testfullhlist/nodeBBB', json={
        "prefLabel": ["testrootnodelabel@en"],
        "definition": ["testrootnodedefinition@en"],
        "position": "rightOf",
        "refnode": "nodeBBA"
    }, headers=header)

    response = client.put('/admin/hlist/hyha/testfullhlist/nodeBBC', json={
        "prefLabel": ["testrootnodelabel@en"],
        "definition": ["testrootnodedefinition@en"],
        "position": "rightOf",
        "refnode": "nodeBBB"
    }, headers=header)

    response = client.put('/admin/hlist/hyha/testfullhlist/nodeBBBA', json={
        "prefLabel": ["testrootnodelabel@en"],
        "definition": ["testrootnodedefinition@en"],
        "position": "belowOf",
        "refnode": "nodeBBB"
    }, headers=header)


    yield
