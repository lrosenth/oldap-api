import re


def test_read_user(client, token_headers, testuser):
    header = token_headers[1]

    response = client.get('/admin/user/rosman', headers=header)
    assert response.status_code == 200
    res = response.json
    assert res["familyName"] == "Rosenthaler"
    assert res["givenName"] == "Manuel"
    assert res["email"] == "manuel.rosenthaler@unibas.ch"
    assert res["hasPermissions"] == ['oldap:GenericView']
    assert res["inProjects"] == [{'permissions': ['oldap:ADMIN_USERS'], 'project': 'oldap:HyperHamlet'},
 {'permissions': ['oldap:ADMIN_USERS'],
  'project': 'http://www.salsah.org/version/2.0/SwissBritNet'}]
    assert res["userId"] == "rosman"

    user_iri = res.get("userIri", "")
    urn_regex = r'^urn:[a-z0-9][a-z0-9-]{0,31}:[^\s]+$'

    assert bool(re.match(urn_regex, user_iri)), "Die userIri ist nicht URN-konform"


def test_read_user_not_found(client, token_headers, testuser):
    header = token_headers[1]

    response = client.get('/admin/user/kappa', headers=header)
    assert response.status_code == 404
    res = response.json
    assert 'message' in res
    assert res["message"] == "User kappa not found"

    response = client.get('/admin/user/get', query_string={
        "iri": "https://orcid.org/0000-0003-1681-4038"
    }, headers=header)
    assert response.status_code == 404
    res = response.json
    print(res)
    assert res["message"] == "User https://orcid.org/0000-0003-1681-4038 not found"


def test_empty_has_permissions(client, token_headers):
    header = token_headers[1]

    client.put('/admin/user/rosman', json={
        "givenName": "Manuel",
        "familyName": "Rosenthaler",
        "email": "manuel.rosenthaler@unibas.ch",
        "password": "kappa1234",
        "inProjects": [
            {
                "project": "http://www.salsah.org/version/2.0/SwissBritNet",
                "permissions": [
                    "ADMIN_USERS"
                ]
            }
        ],
    }, headers=header)

    response = client.get('/admin/user/rosman', headers=header)

    res = response.json
    assert res["hasPermissions"] == []

    client.delete('/admin/user/rosman', headers=header)


def test_empty_projects(client, token_headers):
    header = token_headers[1]

    client.put('/admin/user/rosman', json={
        "givenName": "Manuel",
        "familyName": "Rosenthaler",
        "email": "manuel.rosenthaler@unibas.ch",
        "password": "kappa1234",
        "inProjects": [
            {
                "project": "http://www.salsah.org/version/2.0/SwissBritNet"
            }
        ],
        "hasPermissions": [
            "GenericView"
        ]
    }, headers=header)

    response = client.get('/admin/user/rosman', headers=header)

    res = response.json
    assert res['inProjects'][0]['permissions'] == []

    client.delete('/admin/user/rosman', headers=header)


def test_bad_token(client, token_headers):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.get('/admin/user/rosman', headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"

    response = client.get('/admin/user/get', query_string={
        "iri": "https://orcid.org/0000-0003-1681-4036"
    }, headers=header)
    assert response.status_code == 403

def test_get_user_by_iri(client, token_headers):
    header = token_headers[1]

    response = client.get('/admin/user/get', query_string={
        "iri": "https://orcid.org/0000-0003-1681-4036"
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    assert res["userId"] == "rosenth"
    assert res["familyName"] == "Rosenthaler"
    assert res["givenName"] == "Lukas"
    assert res["email"] == "lukas.rosenthaler@unibas.ch"
    assert set(res["hasPermissions"]) == {'oldap:GenericRestricted', 'oldap:GenericView'}

    response = client.get('/admin/user/get', query_string={
    }, headers=header)
    assert response.status_code == 400

    response = client.get('/admin/user/get', query_string={
        "kappa": "gugus"
    }, headers=header)
    assert response.status_code == 400

