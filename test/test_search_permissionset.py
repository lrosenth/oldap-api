def test_search_permissionset(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.get('/admin/permissionset/search', query_string={
        "label": "testPerm"
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)


def test_no_json(client, token_headers):
    header = token_headers[1]
    response = client.get('/admin/permissionset/search', "NoQueryString", headers=header)
    assert response.status_code == 400
    res = response.json
    assert 'message' in res
    assert res['message'] == "Query parameters 'label' and/or 'definedByProject' and/or ' givesPermission – got none"


def test_empty_json(client, token_headers):
    header = token_headers[1]
    response = client.get('/admin/permissionset/search', query_string={}, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)


def test_search_not_found(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.get('/admin/permissionset/search', query_string={
        "label": "doesnotexist"
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    assert res == '[]'
    print(res)


def test_bad_token(client, token_headers):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.get('/admin/permissionset/search', query_string={
        "label": "unittest"
    }, headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"


def test_search_permissionset_other_things(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.get('/admin/permissionset/search', query_string={
        "BadStuff": 1234
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)

