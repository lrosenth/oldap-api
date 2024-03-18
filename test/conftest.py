from time import sleep

import pytest
import jwt
from omaslib.src.connection import Connection
from omaslib.src.helpers.datatypes import QName

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
                     repo="omas",
                     userId="rosenth",
                     credentials="RioGrande",
                     context_name="DEFAULT")
    con.clear_graph(QName('omas:admin'))
    con.upload_turtle("/Users/rosman00/Library/Caches/pypoetry/virtualenvs/oldap-api-rl24mTKu-py3.12/lib/python3.12/site-packages/omaslib/ontologies/admin.trig")
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

