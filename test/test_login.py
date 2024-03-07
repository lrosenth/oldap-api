import pytest


def test_login(client):
    response = client.post('/admin/login', json={'userid': 'rosenth', 'password': 'RioGrande'})
    assert response.status_code == 200
    res = response.json
    assert res['message'] == 'Erfolgreich eingeloggd'