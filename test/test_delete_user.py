

def test_delete_user(client, token_headers):
    header = token_headers[1]

    client.put('/admin/user/rosman', json={
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

    response = client.delete('/admin/user/rosman', headers=header)

    res = response.json
    assert res["message"] == "User rosman deleted"


def test_delete_nonexisting_user(client, token_headers):
    header = token_headers[1]

    client.put('/admin/user/rosman', json={
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

    response = client.delete('/admin/user/kappa', headers=header)

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
    assert response.status_code == 401
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"
