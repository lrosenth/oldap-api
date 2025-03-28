


def test_bad_token(client, token_headers):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.get('/admin/hlist/hyha/testhlist', json={
        "label": ["testlabel@en"],
        "definition": ["testdefinition@en"]
    }, headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"

def test_dm_to_read_hlist_not_found(client, token_headers):
    header = token_headers[1]

    response = client.get('/admin/hlist/doesnotexist/testhlist', json={
        "label": ["testlabel@en"],
        "definition": ["testdefinition@en"]
    }, headers=header)
    assert response.status_code == 404
    res = response.json
    print(res)

def test_hlist_to_read_not_found(client, token_headers):
    header = token_headers[1]

    response = client.get('/admin/hlist/hyha/doesnotexist', json={
        "label": ["testlabel@en"],
        "definition": ["testdefinition@en"]
    }, headers=header)
    assert response.status_code == 404
    res = response.json
    print(res)

