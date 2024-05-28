import os
from time import sleep

import pytest
import jwt
from oldaplib.src.connection import Connection
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

    response = client.put('/admin/permissionset/testpermissionset', json={
        "label": ["testPerm@en", "test@Perm@de", "testpermission"],
        "comment": ["For testing@en", "Für Tests@de"],
        "givesPermission": "DATA_UPDATE",
        "definedByProject": "oldap:SystemProject"
    }, headers=header)

    yield

    client.delete('/admin/permissionset/testpermission', headers=header)

