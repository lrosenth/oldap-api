def test_delete_user(client, token_headers):
    header = token_headers[1]

    client.put('/admin/user/rosman', json={
        "givenName": "Manuel",
        "familyName": "Rosenthaler",
        "email": "manuel.rosenthaler@unibas.ch",
        "password": "kappa1234",
        "inProjects": [
            {
                "project": "http://www.salsah.org/version/2.0/SwissBritNet",
                "permissions": [
                    "ADMIN_USERS"
                ]
            }
        ],
        "hasRole": {"oldap:Unknown": "DATA_VIEW"},
    }, headers=header)

    response = client.delete('/admin/user/rosman', headers=header)

    res = response.json
    assert res["message"] == "User rosman deleted"


def test_delete_nonexisting_user(client, token_headers):
    header = token_headers[1]

    client.put('/admin/user/rosman', json={
        "givenName": "Manuel",
        "familyName": "Rosenthaler",
        "email": "manuel.rosenthaler@unibas.ch",
        "password": "kappa1234",
        "inProjects": [
            {
                "project": "http://www.salsah.org/version/2.0/SwissBritNet",
                "permissions": [
                    "ADMIN_USERS"
                ]
            }
        ],
        "hasRole": {"oldap:Unknown": "DATA_VIEW"},
    }, headers=header)

    response = client.delete('/admin/user/kappa', headers=header)
    assert response.status_code == 404
    res = response.json
    assert res["message"] == 'User "kappa" not found.'

    # Cleanup
    client.delete('/admin/user/rosman', headers=header)


def test_bad_token(client, token_headers):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.delete('/admin/user/kappa', headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"


def test_no_right_delete_user(client, token_headers):
    header = token_headers[1]

    client.put('/admin/user/rosman', json={
        "givenName": "Manuel",
        "familyName": "Rosenthaler",
        "email": "manuel.rosenthaler@unibas.ch",
        "password": "kappa1234",
        "inProjects": [
            {
                "project": "http://www.salsah.org/version/2.0/SwissBritNet",
                "permissions": [
                    "ADMIN_USERS"
                ]
            }
        ],
        "hasRole": {"oldap:Unknown": "DATA_VIEW"},
    }, headers=header)

    client.put('/admin/user/kappa', json={
        "givenName": "Kappa",
        "familyName": "Gaga",
        "email": "gaga@dumdum.com",
        "password": "dumdum",
        "inProjects": [],
        "hasRole": {}
    }, headers=header)

    response = client.post('/admin/auth/kappa', json={'password': 'dumdum'})
    badtoken = response.json["token"]
    badheader = {'Authorization': f'Bearer {badtoken}'}

    response = client.delete('/admin/user/rosman', headers=badheader)

    res2 = response.json
    print(res2)
    assert res2["message"] == "Actor has no ADMIN_USERS permission for project http://www.salsah.org/version/2.0/SwissBritNet"
