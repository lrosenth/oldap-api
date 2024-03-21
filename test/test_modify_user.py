import jwt
from flask import jsonify
from omaslib.src.connection import Connection
from omaslib.src.helpers.omaserror import OmasErrorNotFound, OmasError


def test_modify_givenname(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "givenName": "Kappa"
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    assert res["message"] == "User updated successfully"

    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    assert readed["given_name"] == "Kappa"


def test_modify_familyname(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "familyName": "Kappa"
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    assert res["message"] == "User updated successfully"

    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    assert readed["family_name"] == "Kappa"


def test_modify_credentials(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "password": "Kappa"
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    assert res["message"] == "User updated successfully"

    # Wenn Connection funktioniert dann update erfolgreich.
    con = Connection(server='http://localhost:7200',
                     repo="omas",
                     userId="rosman",
                     credentials="Kappa",
                     context_name="DEFAULT")


def test_modify_inproject(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "inProjects": [
            {
                "project": "http://www.salsah.org/version/2.0/SwissBritNet",
                "permissions": ["ADMIN_RESOURCES"]
            }
        ]
    }, headers=header)

    assert response.status_code == 200
    res = response.json

    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    print(readed)


def test_modify_haspermission(client, token_headers, testuser):
    header = token_headers[1]

    # TODO: Bug! Wenn leere Liste übergeben wird dann bleiben die alten haspermissions erhalten
    response = client.post('/admin/user/rosman', json={
        "hasPermissions": [
            "GenericView"
        ]
    }, headers=header)

    assert response.status_code == 200
    res = response.json

    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    assert readed["has_permissions"] == ['omas:GenericView']
