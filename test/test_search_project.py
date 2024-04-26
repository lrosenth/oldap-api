def test_search_project(client, token_headers, testproject):
    header = token_headers[1]

    response = client.get('/admin/project/search', json={
        "label": "unittest"
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)


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
        "nolabelorcomment": "kappa"
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
    res = response.json
    print(res)


def test_no_json(client, token_headers):
    header = token_headers[1]
    response = client.get('/admin/project/search', "NoJson", headers=header)
    assert response.status_code == 400
    res = response.json
    assert 'message' in res
    assert res['message'] == "JSON expected. Instead received None"


def test_find_several_projects(client, token_headers, testproject):
    header = token_headers[1]

    response = client.put('/admin/project/kappaproject', json={
        "projectIri": "http://unittest.org/project/kappaproject",
        "label": ["unittest@en", "unittest@de"],
        "comment": ["For testing@en", "Für Tests@de"],
        "namespaceIri": "http://unitest.org/project/unittest#",
        "projectStart": "1993-04-05",
        "projectEnd": "2000-01-10"
    }, headers=header)

    response = client.get('/admin/project/search', json={
        "label": "unittest"
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    assert res["message"] == '[Iri("http://unittest.org/project/testproject"), Iri("http://unittest.org/project/kappaproject")]'
    print(res)
