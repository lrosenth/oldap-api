from oldaplib.src.xsd.iri import Iri


def test_search_project(client, token_headers, testproject):
    header = token_headers[1]

    response = client.get('/admin/project/search', query_string={
        "label": "unittest"
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    assert res == [Iri("http://unittest.org/project/testproject")]


def test_bad_token(client, token_headers):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.get('/admin/project/search', query_string={
        "label": "unittest"
    }, headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"


def test_no_label_or_comment(client, token_headers):
    header = token_headers[1]

    response = client.get('/admin/project/search', query_string={
        "nolabelorcomment": "kappa"
    }, headers=header)

    assert response.status_code == 400
    res = response.json


def test_not_found_search(client, token_headers):
    header = token_headers[1]

    response = client.get('/admin/project/search', query_string={
        "label": "doesnotexist"
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    assert res == []


def test_no_query_params(client, token_headers):
    header = token_headers[1]
    response = client.get('/admin/project/search', headers=header)
    assert response.status_code == 400
    res = response.json
    assert 'message' in res
    assert res['message'] == "Query parameters 'label' and/or 'comment' expected – got none"


def test_empty_query_params(client, token_headers):
    header = token_headers[1]
    response = client.get('/admin/project/search', query_string={}, headers=header)
    assert response.status_code == 400
    res = response.json
    assert 'message' in res
    assert res['message'] == "Query parameters 'label' and/or 'comment' expected – got none"


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

    response = client.get('/admin/project/search', query_string={
        "label": "unittest"
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    assert set(res) == {"http://unittest.org/project/testproject", "http://unittest.org/project/kappaproject"}
    print(res)


def test_json_with_unknown_fields(client, token_headers, testproject):
    header = token_headers[1]

    response = client.get('/admin/project/search', query_string={
        "kappa": "unittest"
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)
