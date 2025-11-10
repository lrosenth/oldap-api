def test_read_project(client, token_headers, testproject):
    expected = {
        "projectIri": "http://unittest.org/project/testproject",
        "label": ["unittest@en", "unittest@de"],
        "comment": ["For testing@en", "Für Tests@de"],
        "namespaceIri": "http://unitest.org/project/unittest#",
        "projectStart": "1993-04-05",
        "projectEnd": "2000-01-10"
    }
    header = token_headers[1]

    response = client.get('/admin/project/testproject', headers=header)

    assert response.status_code == 200
    res = response.json
    for key, val in expected.items():
        assert res[key] == val

def test_read_project_with_ontologies(client, token_headers, testproject_with_external_ontologies):
    expected = {
        "projectIri": "http://unittest.org/project/testprojectB",
        "label": ["unittest@en", "unittest@de"],
        "comment": ["For testing@en", "Für Tests@de"],
        "namespaceIri": "http://unitest.org/project/unittestB#",
        "projectStart": "1993-04-05",
        "projectEnd": "2000-01-10"
    }
    header = token_headers[1]

    response = client.get('/admin/project/testprojectB', headers=header)

    assert response.status_code == 200
    res = response.json
    for key, val in expected.items():
        assert res[key] == val

def test_read_project_by_iri(client, token_headers, testproject):
    expected = {
        "projectIri": "http://unittest.org/project/testproject",
        "label": ["unittest@en", "unittest@de"],
        "comment": ["For testing@en", "Für Tests@de"],
        "namespaceIri": "http://unitest.org/project/unittest#",
        "projectStart": "1993-04-05",
        "projectEnd": "2000-01-10"
    }
    header = token_headers[1]

    response = client.get('/admin/project/get', query_string={
        "iri": "http://unittest.org/project/testproject"
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    for key, val in expected.items():
        assert res[key] == val


def test_bad_token(client, token_headers):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.get('/admin/project/testproject', headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"


def test_read_project_not_found(client, token_headers):
    header = token_headers[1]

    response = client.get('/admin/project/projectdoesnotexist', headers=header)

    assert response.status_code == 404

    res = response.json
    assert res["message"] == 'Project with IRI/shortname "projectdoesnotexist" not found.'
