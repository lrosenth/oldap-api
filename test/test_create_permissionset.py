def test_create_permissionset(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/permissionset/oldap/testpermissionset', json={
        "label": ["testPerm@en", "test@Perm@de"],
        "comment": ["For testing@en", "Für Tests@de"],
        "givesPermission": "DATA_UPDATE",
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)


def test_no_json(client, token_headers):
    header = token_headers[1]
    response = client.put('/admin/permissionset/oldap/testpermissionset', 'KEIN JSON', headers=header)
    assert response.status_code == 400
    res = response.json
    assert 'message' in res
    assert res['message'] == "JSON expected. Instead received None"


def test_create_permissionset_with_missing_label(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/permissionset/oldap:SystemProject/testpermissionset', json={
        "comment": ["For testing@en", "Für Tests@de"],
        "givesPermission": "DATA_UPDATE",
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)


def test_create_permissionset_with_missing_comment(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/permissionset/oldap:SystemProject/testpermissionset', json={
        "label": ["testPerm@en", "test@Perm@de"],
        "givesPermission": "DATA_UPDATE",
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)


def test_create_permissionset_with_missing_givespermission(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/permissionset/oldap/testpermissionset', json={
        "label": ["testPerm@en", "test@Perm@de"],
        "comment": ["For testing@en", "Für Tests@de"],
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)


def test_create_permissionset_with_bad_field(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/permissionset/oldap/testpermissionset', json={
        "Nonsense": "Kappagaga",
        "label": ["testPerm@en", "test@Perm@de"],
        "comment": ["For testing@en", "Für Tests@de"],
        "givesPermission": "DATA_UPDATE",
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)


def test_bad_token(client, token_headers):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.put('/admin/permissionset/oldap/testpermissionset', json={
        "label": ["testPerm@en", "test@Perm@de"],
        "comment": ["For testing@en", "Für Tests@de"],
        "givesPermission": "DATA_UPDATE",
    }, headers=header)
    assert response.status_code == 403
    res = response.json
    print(res)
    assert res["message"] == "Connection failed: Wrong credentials"


def test_permissionset_already_exists(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.put('/admin/permissionset/oldap/testpermissionset', json={
        "label": ["testPerm@en", "test@Perm@de"],
        "comment": ["For testing@en", "Für Tests@de"],
        "givesPermission": "DATA_UPDATE",
    }, headers=header)
    assert response.status_code == 409
    res = response.json
    print(res)


def test_no_permission_create_permissionset(client, token_headers):
    header = token_headers[1]

    client.put('/admin/user/rosmankappa', json={
        "givenName": "Manuel",
        "familyName": "Rosenthaler",
        "password": "kappa1234",
        "inProjects": [
            {
                "project": "http://www.salsah.org/version/2.0/SwissBritNet",
            }
        ],
        "hasPermissions": [
            "GenericRestricted"
        ]
    }, headers=header)

    login = client.post('/admin/auth/rosmankappa', json={'password': 'kappa1234'})
    token = login.json['token']
    headers = {
        'Authorization': f'Bearer {token}'
    }

    response2 = client.put('/admin/permissionset/oldap/testpermissionset', json={
        "label": ["testPerm@en", "test@Perm@de"],
        "comment": ["For testing@en", "Für Tests@de"],
        "givesPermission": "DATA_UPDATE",
    }, headers=headers)
    assert response2.status_code == 403


def test_empty_label(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/permissionset/oldap/testpermissionset', json={
        "label": [],
        "comment": ["For testing@en", "Für Tests@de"],
        "givesPermission": "DATA_UPDATE",
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)


def test_empty_comment(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/permissionset/oldap/testpermissionset', json={
        "comment": [],
        "givesPermission": "DATA_UPDATE",
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)


def test_nonexisting_permission(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/permissionset/oldap/testpermissionset', json={
        "label": ["testPerm@en", "test@Perm@de"],
        "comment": ["For testing@en", "Für Tests@de"],
        "givesPermission": "NONEXISTING",
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)


def test_bad_langstring(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/permissionset/oldap/testpermissionset', json={
        "label": 123,
        "comment": ["For testing@en", "Für Tests@de"],
        "givesPermission": "DATA_UPDATE",
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)


def test_list_permission(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/permissionset/oldap/testpermissionset', json={
        "label": 123,
        "comment": ["For testing@en", "Für Tests@de"],
        "givesPermission": ["DATA_UPDATE", "ADDITIONAL_PERM"],
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)
