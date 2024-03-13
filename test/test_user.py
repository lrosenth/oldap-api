import json


def test_create_user(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/user/rosman', json={
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
    assert response.status_code == 200
    res = response.json
    assert 'message' in res
    assert res["message"] == "User rosman created"
    assert 'userIri' in res
    assert res["userIri"] == "rosman"


def test_user_already_exists(client, token_headers):
    header = token_headers[1]

    firstlogin = client.put('/admin/user/rosman', json={
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
    secondlogin = client.put('/admin/user/rosman', json={
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
    assert secondlogin.status_code == 409
    res = secondlogin.json
    assert 'message' in res
    assert res['message'] == 'A user with a user ID "rosman" already exists'


def test_field_missing(client, token_headers):
    header = token_headers[1]
    response = client.put('/admin/user/rosman', json={
        "givenName": "Manuel",
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
    assert response.status_code == 400
    res = response.json
    assert 'message' in res
    assert res['message'] == "Missing field 'familyName'"


def test_no_json(client, token_headers):
    header = token_headers[1]
    response = client.put('/admin/user/rosman', 'Kein JSON!!', headers=header)
    assert response.status_code == 400
    res = response.json
    assert 'message' in res
    assert res['message'] == "JSON expected. Instead received None"


def test_wrong_projectpermission(client, token_headers):
    header = token_headers[1]
    response = client.put('/admin/user/rosman', json={
        "givenName": "Manuel",
        "familyName": "Rosenthaler",
        "password": "kappa1234",
        "inProjects": [
            {
                "project": "http://www.salsah.org/version/2.0/SwissBritNet",
                "permissions": [
                    "KAPPA!!!"
                ]
            }
        ],
        "hasPermissions": [
            "GenericView"
        ]
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    assert 'message' in res
    assert res['message'] == "The given project project permission is not a valid one"

