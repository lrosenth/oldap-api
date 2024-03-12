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
