def test_create_role(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/role/test/testrole', json={
        "label": ["testPerm@en", "test@Perm@de"],
        "comment": ["For testing@en", "Für Tests@de"],
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)


def test_no_json(client, token_headers):
    header = token_headers[1]
    response = client.put('/admin/role/test/testrole', 'KEIN JSON', headers=header)
    assert response.status_code == 400
    res = response.json
    assert 'message' in res
    assert res['message'] == "JSON expected. Instead received None"


def test_create_role_without_label(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/role/oldap:SystemProject/testrole', json={
        "comment": ["For testing@en", "Für Tests@de"],
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)


def test_create_permissionset_without_comment(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/role/oldap:SystemProject/testrole2', json={
        "label": ["testPerm@en", "test@Perm@de"],
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)


def test_create_role_with_bad_field(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/role/oldap/testrole', json={
        "Nonsense": "Kappagaga",
        "label": ["testPerm@en", "test@Perm@de"],
        "comment": ["For testing@en", "Für Tests@de"],
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)


def test_bad_token(client, token_headers):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.put('/admin/role/oldap/testrole', json={
        "label": ["testPerm@en", "test@Perm@de"],
        "comment": ["For testing@en", "Für Tests@de"],
    }, headers=header)
    assert response.status_code == 403
    res = response.json
    print(res)
    assert res["message"] == "Connection failed: Wrong credentials"


def test_role_already_exists(client, token_headers, testrole):
    header = token_headers[1]

    response = client.put('/admin/role/test/testrole', json={
        "label": ["testPerm@en", "test@Perm@de"],
        "comment": ["For testing@en", "Für Tests@de"],
    }, headers=header)
    assert response.status_code == 200
    response = client.put('/admin/role/test/testrole', json={
        "label": ["testPerm@en", "test@Perm@de"],
        "comment": ["For testing@en", "Für Tests@de"],
    }, headers=header)
    assert response.status_code == 409
    res = response.json
    print(res)


def test_no_permission_create_role(client, token_headers):
    header = token_headers[1]

    client.put('/admin/user/rosmankappa', json={
        "givenName": "Manuel",
        "familyName": "Rosenthaler",
        "email": "manuel.rosenthaler@unibas.ch",
        "password": "kappa1234",
        "inProjects": [
            {
                "project": "http://www.salsah.org/version/2.0/SwissBritNet",
            }
        ],
        "hasRole": {"oldap:Unknown": 'DATA_RESTRICTED'},
    }, headers=header)

    login = client.post('/admin/auth/rosmankappa', json={'password': 'kappa1234'})
    token = login.json['token']
    headers = {
        'Authorization': f'Bearer {token}'
    }

    response2 = client.put('/admin/role/oldap/testrole', json={
        "label": ["testPerm@en", "test@Perm@de"],
        "comment": ["For testing@en", "Für Tests@de"],
    }, headers=headers)
    assert response2.status_code == 403


def test_empty_label(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/role/oldap/testrole', json={
        "label": [],
        "comment": ["For testing@en", "Für Tests@de"],
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)


def test_empty_comment(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/role/oldap/testrole', json={
        "comment": [],
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)


def test_bad_langstring(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/role/oldap/testrole', json={
        "label": 123,
        "comment": ["For testing@en", "Für Tests@de"],
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)


