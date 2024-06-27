def test_modify_label(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": "Kappa@fr",
        "comment": "random comment",
        "givesPermission": "DATA_UPDATE"
    }, headers=header)

    assert response.status_code == 200

    response2 = client.get('/admin/permissionset/oldap/testpermissionset', headers=header)
    res = response2.json
    print(res)
    assert res.get('label') == ['Kappa@fr']


def test_modify_comment(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": ["testPerm@en", "test@Perm@de"],
        "comment": "random changed comment",
        "givesPermission": "DATA_UPDATE"
    }, headers=header)

    assert response.status_code == 200

    response2 = client.get('/admin/permissionset/oldap/testpermissionset', headers=header)
    res = response2.json
    print(res)
    assert res.get('comment') == ['random changed comment@en']


def test_modify_gives_permission(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": ["testPerm@en", "test@Perm@de"],
        "comment": "random comment",
        "givesPermission": "DATA_VIEW"
    }, headers=header)

    assert response.status_code == 200

    response2 = client.get('/admin/permissionset/oldap/testpermissionset', headers=header)
    res = response2.json
    print(res)
    assert res.get('givesPermission') == 'DataPermission.DATA_VIEW'


def test_bad_token(client, token_headers):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": "Kappa@fr"
    }, headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"


def test_permissionset_to_modify_not_found(client, token_headers):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/notexistingproject', json={
        "label": "Kappa@fr"
    }, headers=header)

    assert response.status_code == 404
    res = response.json
    print(res)
    assert res["message"] == 'No permission set "oldap:notexistingproject"'


def test_no_json(client, token_headers, testuser):
    header = token_headers[1]
    response = client.post('/admin/permissionset/oldap/testpermissionset', 'Kein JSON!!', headers=header)
    assert response.status_code == 400
    res = response.json
    assert 'message' in res
    assert res['message'] == "JSON expected. Instead received None"


def test_empty_json(client, token_headers, testuser):
    header = token_headers[1]
    response = client.post('/admin/permissionset/oldap/testpermissionset', json={}, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)


def test_json_with_unknown_fields(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "kappa": "Gaga\"++-usw@en"
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)


def test_bad_langstring(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "comment": 123,
        "givesPermission": "DATA_UPDATE",
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)
