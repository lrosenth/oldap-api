def test_read_datamodel(client, token_headers, testfulldatamodel):
    header = token_headers[1]

    response = client.get('/admin/datamodel/hyha', headers=header)

    res = response.json
    print(res)


def test_bad_token(client, token_headers):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.get('/admin/datamodel/hyha', headers=header)
    assert response.status_code == 403
    res = response.json
    print(res)
    assert res["message"] == "Connection failed: Wrong credentials"


def test_read_nonexisting_dm(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.get('/admin/datamodel/doesnotexist', headers=header)

    assert response.status_code == 404
    res = response.json
    print(res)
