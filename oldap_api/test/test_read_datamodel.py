from pprint import pprint

def test_read_datamodel_extontos(client, token_headers, testdatamodelwithexternalontology):
    header = token_headers[1]

    response = client.get('/admin/datamodel/hyha', headers=header)

    res = response.json
    assert response.status_code == 200
    assert len(res['externalOntologies']) == 1


def test_read_standaloneporp_datamodel(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.get('/admin/datamodel/hyha', headers=header)

    res = response.json
    pprint(res)
    assert response.status_code == 200


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
