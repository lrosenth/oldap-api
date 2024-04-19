def test_search_project(client, token_headers, testproject):
    header = token_headers[1]

    response = client.get('/admin/project/search', json={
        "label": "unittest"
    }, headers=header)

    res = response.json


def test_bad_token(client, token_headers):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.get('/admin/project/search', json={
        "label": "unittest"
    }, headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"


def test_no_label_or_comment(client, token_headers):
    header = token_headers[1]

    response = client.get('/admin/project/search', json={
        "nolabelortest": "kappa"
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    assert res["message"] == "Either label or comment needs to be provided"


def test_not_found_search(client, token_headers):
    header = token_headers[1]

    response = client.get('/admin/project/search', json={
        "label": "doesnotexist"
    }, headers=header)

    assert response.status_code == 404


def test_no_json(client, token_headers):
    header = token_headers[1]
    response = client.get('/admin/project/search', "NoJson", headers=header)
    assert response.status_code == 400
    res = response.json
    assert 'message' in res
    assert res['message'] == "JSON expected. Instead received None"
