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


def test_bad_token(client, token_headers):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.get('/admin/project/testproject', headers=header)
    assert response.status_code == 401
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"
