import re


def test_modify_label(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "label": "Kappa@fr"
    }, headers=header)

    assert response.status_code == 200
    res = response.json

    response2 = client.get('/admin/project/testproject', headers=header)
    # Regex to find the content of "Comment"
    match = re.search(r'Label:\s*(.+?)(?=\\n)', response2.text)
    comments_raw = match.group(1)
    # Remove unnecessary backslashes before quotes (around the entire entry and language tags)
    comments_cleaned = re.sub(r'\\(?=")', '', comments_raw)  # Remove \ before "
    comments_cleaned = re.sub(r'"@', '@', comments_cleaned)  # Remove " before @

    # Correctly place the quotation marks and handle the final quotation mark
    comments_cleaned = re.sub(r',\s', '", ', comments_cleaned)  # Add closing " before comma
    comments_cleaned += '"'  # Add a closing quotation mark at the end of the string

    # Decode unicode escapes
    comments_decoded = bytes(comments_cleaned, "utf-8").decode("unicode_escape")

    assert comments_decoded == '"Kappa@fr"'


def test_modify_comment(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "comment": ["For testing@en", "FÜR DAS TESTEN@de", "Pour les tests@fr"]
    }, headers=header)

    assert response.status_code == 200
    res = response.json

    response2 = client.get('/admin/project/testproject', headers=header)
    # Regex to find the content of "Comment"
    match = re.search(r'Comment:\s*(.+?)(?=\\n)', response2.text)
    comments_raw = match.group(1)
    # Remove unnecessary backslashes before quotes (around the entire entry and language tags)
    comments_cleaned = re.sub(r'\\(?=")', '', comments_raw)  # Remove \ before "
    comments_cleaned = re.sub(r'"@', '@', comments_cleaned)  # Remove " before @

    # Correctly place the quotation marks and handle the final quotation mark
    comments_cleaned = re.sub(r',\s', '", ', comments_cleaned)  # Add closing " before comma
    comments_cleaned += '"'  # Add a closing quotation mark at the end of the string

    # Decode unicode escapes
    comments_decoded = bytes(comments_cleaned, "utf-8").decode("unicode_escape")

    assert comments_decoded == '"For testing@en", "FÜR DAS TESTEN@de", "Pour les tests@fr"'


def test_modify_startdate(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "projectStart": "2024-05-28"
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    response2 = client.get('/admin/project/testproject', headers=header)
    # Regex to find the content of "Comment"
    match = re.search(r'start:\s*(.+?)(?=\\n)', response2.text)
    comments_raw = match.group(1)
    assert comments_raw == "2024-05-28"


def test_modify_enddate(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "projectEnd": "2024-05-28"
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    response2 = client.get('/admin/project/testproject', headers=header)
    # Regex to find the content of "Comment"
    match = re.search(r'end:\s*(.+?)(?=\\n)', response2.text)
    comments_raw = match.group(1)
    assert comments_raw == "2024-05-28"


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
    assert projectshortname.status_code == 403
    res = projectshortname.json
    assert res["message"] == "projectShortName, projectIri and namespaceIri must not be modified"

    projectIri = client.post('/admin/project/testproject', json={
        "projectIri": "randomprojectIri"
    }, headers=header)
    assert projectIri.status_code == 403
    res = projectIri.json
    assert res["message"] == "projectShortName, projectIri and namespaceIri must not be modified"

    namespaceIri = client.post('/admin/project/testproject', json={
        "namespaceIri": "randomnamespaceIri"
    }, headers=header)
    assert namespaceIri.status_code == 403
    res = namespaceIri.json
    assert res["message"] == "projectShortName, projectIri and namespaceIri must not be modified"


def test_project_to_modify_not_found(client, token_headers):
    header = token_headers[1]

    response = client.post('/admin/project/notexistingproject', json={
        "label": "Kappa@fr"
    }, headers=header)

    assert response.status_code == 404
    res = response.json
    assert res["message"] == 'Project with IRI/shortname "notexistingproject" not found.'


def test_no_json(client, token_headers, testuser):
    header = token_headers[1]
    response = client.post('/admin/project/testproject', 'Kein JSON!!', headers=header)
    assert response.status_code == 400
    res = response.json
    assert 'message' in res
    assert res['message'] == "JSON expected. Instead received None"


def test_no_permission_modify(client, token_headers, testproject):
    # TODO: Funktioniert nicht. Warum?! --> Probably bug in Backend
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
        "givenName": "Kappa"
    }, headers=headers)
    res2 = response2.json
    print(res2)
    assert response2.status_code == 403
