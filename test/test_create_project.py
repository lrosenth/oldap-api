
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


def test_no_json(client, token_headers):
    header = token_headers[1]
    response = client.put('/admin/project/testproject', 'Kein JSON!!', headers=header)
    assert response.status_code == 400
    res = response.json
    assert 'message' in res
    assert res['message'] == "JSON expected. Instead received None"


def test_create_project_with_missing_label(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/project/testproject', json={
        "projectIri": "http://unittest.org/project/testproject",
        "comment": ["For testing@en", "Für Tests@de"],
        "namespaceIri": "http://unitest.org/project/unittest#",
        "projectStart": "1993-04-05",
        "projectEnd": "2000-01-10"
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    assert res["message"] == "To create a project, at least the projectshortname, label, comment and namespaceIri are required"
    print(res)


def test_create_project_with_missing_comment(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/project/testproject', json={
        "projectIri": "http://unittest.org/project/testproject",
        "label": ["unittest@en", "unittest@de"],
        "namespaceIri": "http://unitest.org/project/unittest#",
        "projectStart": "1993-04-05",
        "projectEnd": "2000-01-10"
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)


def test_create_project_with_missing_namespaceIri(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/project/testproject', json={
        "projectIri": "http://unittest.org/project/testproject",
        "label": ["unittest@en", "unittest@de"],
        "comment": ["For testing@en", "Für Tests@de"],
        "projectStart": "1993-04-05",
        "projectEnd": "2000-01-10"
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    assert res["message"] == "To create a project, at least the projectshortname, label, comment and namespaceIri are required"
    print(res)


def test_create_project_with_missing_projectIri(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/project/testproject', json={
        "label": ["unittest@en", "unittest@de"],
        "comment": ["For testing@en", "Für Tests@de"],
        "namespaceIri": "http://unitest.org/project/unittest#",
        "projectStart": "1993-04-05",
        "projectEnd": "2000-01-10"
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)


def test_create_project_with_missing_projectstart(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/project/testproject', json={
        "projectIri": "http://unittest.org/project/testproject",
        "label": ["unittest@en", "unittest@de"],
        "comment": ["For testing@en", "Für Tests@de"],
        "namespaceIri": "http://unitest.org/project/unittest#",
        "projectEnd": "2000-01-10"
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)


def test_create_project_with_missing_projectend(client, token_headers):
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


def test_inconsistent_start_and_enddate(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/project/testproject', json={
        "projectIri": "http://unittest.org/project/testproject",
        "label": ["unittest@en", "unittest@de"],
        "comment": ["For testing@en", "Für Tests@de"],
        "namespaceIri": "http://unitest.org/project/unittest#",
        "projectStart": "2000-01-10",
        "projectEnd": "1993-04-05"
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)

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
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"


def test_project_already_exists(client, token_headers, testproject):
    header = token_headers[1]

    response = client.put('/admin/project/testproject', json={
        "projectIri": "http://unittest.org/project/testproject",
        "label": ["unittest@en", "unittest@de"],
        "comment": ["For testing@en", "Für Tests@de"],
        "namespaceIri": "http://unitest.org/project/unittest#",
        "projectStart": "1993-04-05",
        "projectEnd": "2000-01-10"
    }, headers=header)
    assert response.status_code == 409


def test_no_permission_create_project(client, token_headers, testuser):
    header = token_headers[1]

    client.put('/admin/user/rosmankappa', json={
        "givenName": "Manuel",
        "familyName": "Rosenthaler",
        "password": "kappa1234",
        "inProjects": [
            {
                "project": "http://www.salsah.org/version/2.0/SwissBritNet",
            }
        ],
        "hasPermissions": [
            "GenericRestricted"
        ]
    }, headers=header)

    login = client.post('/admin/auth/rosmankappa', json={'password': 'kappa1234'})
    token = login.json['token']
    headers = {
        'Authorization': f'Bearer {token}'
    }

    response2 = client.put('/admin/project/testproject', json={
        "projectIri": "http://unittest.org/project/testproject",
        "label": ["unittest@en", "unittest@de"],
        "comment": ["For testing@en", "Für Tests@de"],
        "namespaceIri": "http://unitest.org/project/unittest#",
        "projectStart": "1993-04-05",
        "projectEnd": "2000-01-10"
    }, headers=headers)
    assert response2.status_code == 403


def test_bad_langstring(client, token_headers, testuser):
    header = token_headers[1]

    response = client.put('/admin/project/testproject', json={
        "projectIri": "http://unittest.org/project/testproject",
        "label": ["unittest@en", "unittest@de"],
        "comment": 2000,
        "namespaceIri": "http://unitest.org/project/unittest#",
        "projectStart": "1993-04-05",
        "projectEnd": "2000-01-10"
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    assert res["message"] == 'LangString parameter has wrong datatype: int, must be "str | Xsd_string | List[str] | Dict[Language | str, str] | LangString"'
    print(res)


def test_bad_iri(client, token_headers, testuser):
    header = token_headers[1]

    response = client.put('/admin/project/testproject', json={
        "projectIri": 2000,
        "label": ["unittest@en", "unittest@de"],
        "comment": ["For testing@en", "Für Tests@de"],
        "namespaceIri": "http://unitest.org/project/unittest#",
        "projectStart": "1993-04-05",
        "projectEnd": "2000-01-10"
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    assert res["message"] == 'Invalid value for IRI: "2000"'
    print(res)

