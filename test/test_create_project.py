
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


def test_delete_project(client, token_headers, testproject):
    header = token_headers[1]

    response = client.delete('/admin/project/testproject', headers=header)

    assert response.status_code == 200

    res = response.json
    assert res['message'] == 'Project successfully deleted'

    response = client.get('/admin/project/testproject', headers=header)
    assert response.status_code == 400


def test_read_project(client, token_headers, testproject):
    header = token_headers[1]

    response = client.get('/admin/project/testproject', headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)


def test_search_project(client, token_headers, testproject):
    header = token_headers[1]

    response = client.get('/admin/project/search', json={
        "label": "unittest"
    }, headers=header)

    res = response.json
    print(res)


def test_modify_project(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "label": "Kappa@fr"
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)

    response = client.get('/admin/project/testproject', headers=header)
    print(response.text)




