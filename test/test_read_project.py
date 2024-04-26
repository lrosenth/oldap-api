def test_read_project(client, token_headers, testproject):
    header = token_headers[1]

    response = client.get('/admin/project/testproject', headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)


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
