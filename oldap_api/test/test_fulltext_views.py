"""Public fulltext contract; live RDF authorization is covered by Jena probe."""
from unittest.mock import Mock, patch
import pytest
from flask import Flask
from oldap_api.views.fulltext_views import fulltext_bp
from oldaplib.src.helpers.oldaperror import (
    OldapErrorAlreadyExists, OldapErrorConfiguration, OldapErrorNoPermission, OldapErrorNotFound,
)


@pytest.fixture
def client():
    app = Flask(__name__)
    app.register_blueprint(fulltext_bp)
    return app.test_client()


def test_authentication_and_unsupported_backend(client):
    assert client.get('/admin/fulltext/demo').status_code == 401
    assert client.put('/admin/fulltext/demo', json={}).status_code == 401
    con = Mock(_managed_fulltext=False)
    with patch('oldap_api.authentication.Connection', return_value=con):
        response = client.get('/admin/fulltext/demo', headers={'Authorization': 'Bearer token'})
        assert response.status_code == 503
        con.query.assert_not_called()


@pytest.mark.parametrize('body', [None, {}, {'configuration': {}},
    {'configuration': {}, 'expectedRevision': None, 'backendUrl': 'http://elsewhere'}])
def test_put_requires_closed_body(client, body):
    with patch('oldap_api.authentication.Connection'), patch('oldaplib.src.project_fulltext.ProjectFulltext') as service:
        response = client.put('/admin/fulltext/demo', headers={'Authorization': 'Bearer token'}, json=body)
        assert response.status_code == 400
        assert response.headers['Cache-Control'] == 'no-store'
        service.return_value.apply.assert_not_called()


@pytest.mark.parametrize('error,status', [(OldapErrorNoPermission('denied'), 403),
    (OldapErrorAlreadyExists('stale'), 409), (OldapErrorConfiguration('uncertain'), 503),
    (OldapErrorNotFound('absent'), 404)])
def test_failures_have_explicit_status(client, error, status):
    with patch('oldap_api.authentication.Connection'), patch('oldaplib.src.project_fulltext.ProjectFulltext', side_effect=error):
        assert client.get('/admin/fulltext/demo', headers={'Authorization': 'Bearer token'}).status_code == status
