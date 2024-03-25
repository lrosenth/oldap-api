import json

import jwt
import pytest
from omaslib.src.helpers.serializer import serializer


def test_login_succeed(client, connection_manager):
    response = client.post('/admin/auth/rosenth', json={'password': 'RioGrande'})
    assert response.status_code == 200
    res = response.json
    assert res['message'] == 'Login succeeded'
    token = jwt.decode(jwt=res['token'], key=connection_manager.jwt_secret, algorithms="HS256")
    userdata = json.loads(token['userdata'], object_hook=serializer.decoder_hook)
    assert userdata.userId == 'rosenth'
    assert userdata.userIri == 'https://orcid.org/0000-0003-1681-4036'
    assert userdata.active


def test_login_wrong_userid(client):
    response = client.post('/admin/auth/XZY', json={'password': 'Rio Grande'})
    assert response.status_code == 404
    res = response.json
    assert res['message'] == 'Given user not found!'


def test_login_no_password(client):
    response = client.post('/admin/auth/rosenth', json={'gaga': 'RioGrande'})
    assert response.status_code == 400
    res = response.json
    assert res['message'] == 'Invalid content type, JSON required'


def test_login_no_json(client):
    response = client.post('/admin/auth/rosenth')
    assert response.status_code == 400
    res = response.json
    assert res['message'] == 'Invalid content type, JSON required'


def test_logout(client):
    response = client.delete('/admin/auth/rosenth')
    assert response.status_code == 200

def test_no_json(client, token_headers, testuser):
    response = client.post('/admin/auth/rosenth', 'Kein JSON!!')
    assert response.status_code == 400
    res = response.json
    assert 'message' in res
    assert res['message'] == "JSON expected. Instead received None"
