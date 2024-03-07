import jwt
import pytest


def test_login_succeed(client, connection_manager):
    response = client.post('/admin/auth', json={'userid': 'rosenth', 'password': 'RioGrande'})
    assert response.status_code == 200
    res = response.json
    assert res['message'] == 'Login succeeded'
    #jwt = jwt.decode(jwt=res['token'], key=connection_manager.jwtkey, algorithms="HS256")

def test_login_failed(client):
    response = client.post('/admin/auth', json={'userid': 'rosenth', 'password': '*'})
    assert response.status_code == 401
    res = response.json
    assert res['message'] == 'Wrong credentials'
