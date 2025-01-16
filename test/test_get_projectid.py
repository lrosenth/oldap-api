from pprint import pprint


def test_get_projectid(client, token_headers, testproject):
    header = token_headers[1]

    response = client.get('/admin/project/getid', json={
        "iri": "oldap:HyperHamlet"
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    assert res["id"] == "hyha"

def test_get_projectid2(client, token_headers, testproject):
    header = token_headers[1]

    response = client.get('/admin/project/getid', json={
        "iri": "http://www.salsah.org/version/2.0/SwissBritNet"
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    assert res["id"] == "britnet"

def test_get_project_unknown(client, token_headers, testproject):
    header = token_headers[1]

    response = client.get('/admin/project/getid', json={
        "iri": "oldap:unknown"
    }, headers=header)

    assert response.status_code == 404
    res = response.json
    assert res["message"] == 'OldapErrorNotFound: No project shortname found for oldap:unknown'

def test_get_project_malformed(client, token_headers, testproject):
    header = token_headers[1]

    response = client.get('/admin/project/getid', json={
        "iri": "gaga:unknown"
    }, headers=header)

    assert response.status_code == 500
    res = response.json
    assert res["message"] == "OldapError: MALFORMED QUERY: QName 'gaga:unknown' uses an undefined prefix"

def test_get_project_malformed2(client, token_headers, testproject):
    header = token_headers[1]

    response = client.get('/admin/project/getid', json={
        "iri": "http://www.example.org/no/project"
    }, headers=header)

    assert response.status_code == 404
    res = response.json
    assert res["message"] == 'OldapErrorNotFound: No project shortname found for http://www.example.org/no/project'