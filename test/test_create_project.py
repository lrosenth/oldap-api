
def test_create_project(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/project/testproject', json={
        "projectIri": "http://unittest.org/project/testproject",
        "label": ["unittest@en", "unittest@de"],
        "comment": ["For testing@en", "Für Tests@de"],
        "namespaceIri": "http://unitest.org/project/unittest#",
        "projectStart": "1993-04-05",
        "projectEnd": "2000-01-10"
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)


def test_create_project_with_missing_fields(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/project/testproject', json={
        "projectIri": "http://unittest.org/project/testproject",
        "comment": ["For testing@en", "Für Tests@de"],
        "namespaceIri": "http://unitest.org/project/unittest#",
        "projectStart": "1993-04-05",
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    assert res["message"] == "To create a project, at least the projectshortname, label, comment and namespaceIri are required"
    print(res)


def test_create_project_with_missing_optional_fields(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/project/testproject', json={
        "projectIri": "http://unittest.org/project/testproject",
        "label": ["unittest@en", "unittest@de"],
        "comment": ["For testing@en", "Für Tests@de"],
        "namespaceIri": "http://unitest.org/project/unittest#",
        "projectStart": "1993-04-05",
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)


def test_create_nonsensicle_project(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/project/testproject', json={
        "nonsens": "this is nonsense1234",
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    assert res["message"] == "To create a project, at least the projectshortname, label, comment and namespaceIri are required"


def test_bad_token(client, token_headers):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.put('/admin/project/testproject', json={
        "projectIri": "http://unittest.org/project/testproject",
        "label": ["unittest@en", "unittest@de"],
        "comment": ["For testing@en", "Für Tests@de"],
        "namespaceIri": "http://unitest.org/project/unittest#",
        "projectStart": "1993-04-05",
    }, headers=header)
    assert response.status_code == 401
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"
