def test_delete_role(client, token_headers, testrole):
    header = token_headers[1]

    response = client.delete('/admin/role/oldap/testrole', headers=header)

    assert response.status_code == 200

    res = response.json
    assert res['message'] == 'Role successfully deleted'

    response = client.get('/admin/role/oldap/testrole', headers=header)
    assert response.status_code == 404


def test_bad_token(client, token_headers, testrole):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.delete('/admin/role/oldap/testrole', headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"


def test_delete_nonexisting_permissionset(client, token_headers):
    header = token_headers[1]

    response = client.delete('/admin/role/oldap/nonexistingproject', headers=header)

    assert response.status_code == 404

    res = response.json
    assert res["message"] == 'No permission set "oldap:nonexistingproject"'
    print(res)


def test_no_permission_delete(client, token_headers, testrole):
    header = token_headers[1]

    client.put('/admin/user/rosmankappa', json={
        "givenName": "Kappauser",
        "familyName": "KappaKappatest",
        "email": "<kappa@kappa.com>",
        "password": "kappa1234",
        "inProjects": [
            {
                "project": "http://www.salsah.org/version/2.0/SwissBritNet",
            }
        ],
        "hasRole": {"oldap:Unknown": "DATA_VIEW"},
    }, headers=header)

    login = client.post('/admin/auth/rosmankappa', json={'password': 'kappa1234'})
    token = login.json['token']
    headers = {
        'Authorization': f'Bearer {token}'
    }

    response2 = client.delete('/admin/role/oldap/testrole', headers=headers)
    res2 = response2.json
    print(res2)
    assert response2.status_code == 403
