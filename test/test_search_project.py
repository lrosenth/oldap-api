from pprint import pprint

from oldaplib.src.xsd.iri import Iri


def test_search_project(client, token_headers, testproject):
    header = token_headers[1]

    response = client.get('/admin/project/search', query_string={
        "label": "unittest"
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    assert res == [{'projectIri': "http://unittest.org/project/testproject", 'projectShortName': 'testproject'}]


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
    assert response.status_code == 200
    res = response.json
    res2 = [(x['projectIri'], x['projectShortName']) for x in res]
    assert set(res2) == {('oldap:SystemProject', 'oldap'), ('oldap:HyperHamlet', 'hyha'), ('http://www.salsah.org/version/2.0/SwissBritNet', 'britnet')}


def test_empty_query_params(client, token_headers):
    header = token_headers[1]
    response = client.get('/admin/project/search', query_string={}, headers=header)
    assert response.status_code == 200
    res = response.json
    res2 = [(x['projectIri'], x['projectShortName']) for x in res]
    assert set(res2) == {('oldap:SystemProject', 'oldap'), ('oldap:HyperHamlet', 'hyha'), ('http://www.salsah.org/version/2.0/SwissBritNet', 'britnet')}


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
    res2 = [(x['projectIri'], x['projectShortName']) for x in res]
    assert set(res2) == {("http://unittest.org/project/testproject", "testproject"), ("http://unittest.org/project/kappaproject", "kappaproject")}


def test_json_with_unknown_fields(client, token_headers, testproject):
    header = token_headers[1]

    response = client.get('/admin/project/search', query_string={
        "kappa": "unittest"
    }, headers=header)

    assert response.status_code == 400
    res = response.json
