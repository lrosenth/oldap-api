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

    # TODO: mit ADMIN_USERS als haspermissions funktioniert es nicht. WARUM??!!
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




