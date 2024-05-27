import re
from pprint import pprint


def test_modify_label(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "label": "Kappa@fr"
    }, headers=header)

    assert response.status_code == 200

    response2 = client.get('/admin/project/testproject', headers=header)
    res = response2.json
    assert res.get('label') == ['Kappa@fr']


def test_bad_modify_label(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "label": "Gaga\"++-usw@en"
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)
    response2 = client.get('/admin/project/testproject', headers=header)
    print(response2.text)


def test_modify_comment(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "comment": ["For testing@en", "FÜR DAS TESTEN@de", "Pour les tests@fr"]
    }, headers=header)

    assert response.status_code == 200
    res = response.json

    response2 = client.get('/admin/project/testproject', headers=header)
    # Regex to find the content of "Comment"
    result = response2.json
    pprint(result)
    assert set(result['comment']) == {"For testing@en", "FÜR DAS TESTEN@de", "Pour les tests@fr"}


def test_bad_modify_comment(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "comment": "Gaga\"++-usw@en"
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)
    response2 = client.get('/admin/project/testproject', headers=header)
    res = response2.json
    assert res.get('comment') == ["Gaga\"++-usw@en"]


def test_modify_startdate(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "projectStart": "1995-05-28"
    }, headers=header)

    assert response.status_code == 200
    response2 = client.get('/admin/project/testproject', headers=header)
    res = response2.json
    assert res['projectStart'] == "1995-05-28"


def test_modify_bad_startdate(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "projectStart": "2024-05-28-88<code>kappa</code>"
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)


def test_modify_enddate(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "projectEnd": "2024-05-28"
    }, headers=header)

    assert response.status_code == 200
    response2 = client.get('/admin/project/testproject', headers=header)
    res = response2.json
    assert res['projectEnd'] == "2024-05-28"


def test_bad_token(client, token_headers):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.post('/admin/project/testproject', json={
        "label": "Kappa@fr"
    }, headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"


def test_modify_immutable(client, token_headers):
    header = token_headers[1]

    projectshortname = client.post('/admin/project/testproject', json={
        "projectShortName": "randomprojectname"
    }, headers=header)
    assert projectshortname.status_code == 400
    res = projectshortname.json

    projectIri = client.post('/admin/project/testproject', json={
        "projectIri": "randomprojectIri"
    }, headers=header)
    assert projectIri.status_code == 400
    res = projectIri.json

    namespaceIri = client.post('/admin/project/testproject', json={
        "namespaceIri": "randomnamespaceIri"
    }, headers=header)
    assert namespaceIri.status_code == 400
    res = namespaceIri.json


def test_project_to_modify_not_found(client, token_headers):
    header = token_headers[1]

    response = client.post('/admin/project/notexistingproject', json={
        "label": "Kappa@fr"
    }, headers=header)

    assert response.status_code == 404
    res = response.json
    print(res)
    assert res["message"] == 'Project with IRI/shortname "notexistingproject" not found.'


def test_no_json(client, token_headers, testuser):
    header = token_headers[1]
    response = client.post('/admin/project/testproject', 'Kein JSON!!', headers=header)
    assert response.status_code == 400
    res = response.json
    assert 'message' in res
    assert res['message'] == "JSON expected. Instead received None"


def test_no_permission_modify(client, token_headers, testproject):
    header = token_headers[1]

    client.put('/admin/user/rosmankappa', json={
        "givenName": "Kappauser",
        "familyName": "KappaKappatest",
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

    response2 = client.post('/admin/project/testproject', json={
        "label": "Kappa"
    }, headers=headers)
    res2 = response2.json
    print(res2)
    assert response2.status_code == 403


def test_modify_inconsistent_dates(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "projectEnd": "1992-04-05"
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)
    response2 = client.get('/admin/project/testproject', headers=header)
    print(response2.text)


def test_modify_nothing(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={

    }, headers=header)
    assert response.status_code == 400
    res = response.json
    assert res["message"] == "Either the label, comment, projectStart or projectEnd needs to be modified"
    print(res)


def test_randomstuff(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "label": ""
    }, headers=header)

    # assert response.status_code == 400
    res = response.json
    print(res)
    response2 = client.get('/admin/project/testproject', headers=header)
    print(response2.text)


def test_json_with_unknown_fields(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "kappa": "Gaga\"++-usw@en"
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)
