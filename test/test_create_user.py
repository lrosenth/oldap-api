def test_create_user(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/user/rosman', json={
        "givenName": "Manuel",
        "familyName": "Rosenthaler",
        "password": "kappa1234",
        "isActive": "false",
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


def test_user_already_exists(client, token_headers, testuser):
    header = token_headers[1]

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


def test_isActive(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/user/rosman', json={
        "givenName": "Manuel",
        "familyName": "Rosenthaler",
        "password": "kappa1234",
        "isActive": "False",
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

    response = client.get('/admin/user/rosman', headers=header)
    res = response.json
    assert res["isActive"] == 'false'
    print(res)

def test_bad_isActive(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/user/rosman', json={
        "givenName": "Manuel",
        "familyName": "Rosenthaler",
        "password": "kappa1234",
        "isActive": "kappa",
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
    assert res["message"] == 'Invalid input for isActive: must be "true" or "false"'

    response = client.put('/admin/user/rosman', json={
        "givenName": "Manuel",
        "familyName": "Rosenthaler",
        "password": "kappa1234",
        "isActive": True,
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
    assert res["message"] == 'Invalid input for isActive: must be a string thats "true" or "false"'


def test_field_missing(client, token_headers):
    header = token_headers[1]
    response = client.put('/admin/user/rosman', json={
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


def test_bad_projectname(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/user/rosman', json={
        "givenName": "Manuel",
        "familyName": "Rosenthaler",
        "password": "kappa1234",
        "inProjects": [
            {
                "project": "KAPPPAAA!!!",
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
    assert res['message'] == "The given projectname is not a valid anyIri"


def test_permission_QName(client, token_headers):
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
            "KAPPA!!!!!"
        ]
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    assert 'message' in res
    assert res['message'] == "The given permission is not a QName"


def test_haspermission_not_existing(client, token_headers):
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
            "Gaga"
        ]
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    assert 'message' in res
    assert res['message'] == "One of the permission sets is not existing!"


def test_userid_NCName_conform(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/user/!48ä$', json={
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
    assert response.status_code == 400
    res = response.json
    assert 'message' in res
    assert res['message'] == 'Invalid string "!48ä$" for NCName'


def test_empty_permissions(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/user/rosman', json={
        "givenName": "Manuel",
        "familyName": "Rosenthaler",
        "password": "kappa1234",
        "inProjects": [
            {
                "project": "http://www.salsah.org/version/2.0/SwissBritNet"
            }
        ],
        "hasPermissions": [
            "GenericView"
        ]
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 200


def test_empty_hasPermissions(client, token_headers):
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
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 200

    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    assert readed["has_permissions"] == []


def test_bad_userid(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/user/rosman123<:!$', json={
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
    assert response.status_code == 400
    res = response.json
    print(res)


def test_bad_token(client, token_headers):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

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
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"


def test_json_with_unknown_fields(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/user/rosman', json={
        "kappa": "kappa1234",
        "gaga": "gaga",
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
    assert response.status_code == 400
    res = response.json
