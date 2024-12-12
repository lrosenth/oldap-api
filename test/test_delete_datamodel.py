from oldaplib.src.xsd.iri import Iri


def test_delete_whole_datamodel(client, token_headers, testemptydatamodel):
    header = token_headers[1]

    response = client.delete('/admin/datamodel/hyha', headers=header)

    assert response.status_code == 200

    res = response.json
    print(res)
    assert res['message'] == 'Data model successfully deleted'

    response = client.get('/admin/datamodel/hyha', headers=header)
    res = response.json
    print(res)
    assert response.status_code == 404
    assert res['message'] == 'Datamodel "hyha:shacl" not found'


def test_delete_standalone_property(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.delete('/admin/datamodel/hyha/property/hyha:testProp2', headers=header)

    assert response.status_code == 200

    res = response.json
    print(res)
    assert res['message'] == 'Data model successfully deleted'

    response = client.get('/admin/datamodel/hyha', headers=header)
    res = response.json
    print(res)

    for ele in res["standaloneProperties"]:
        assert Iri(ele["iri"]).prefix != "hyha"


def test_delete_resource(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.delete('/admin/datamodel/hyha/hyha:Sheep', headers=header)

    assert response.status_code == 200

    res = response.json
    print(res)
    assert res['message'] == 'Data model successfully deleted'

    response = client.get('/admin/datamodel/hyha', headers=header)
    res = response.json
    print(res)
    assert res['resources'] == []

def test_delete_property_in_resource(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.delete('/admin/datamodel/hyha/hyha:Sheep/hyha:testProp2', headers=header)

    assert response.status_code == 200

    res = response.json
    print(res)
    assert res['message'] == 'Data model successfully deleted'

    response = client.get('/admin/datamodel/hyha', headers=header)
    res = response.json
    print(res)
    assert res["resources"][0]['hasProperty'] == []

def test_bad_token(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.delete('/admin/datamodel/hyha', headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"

    response = client.delete('/admin/datamodel/hyha/hyha:Sheep', headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"


def test_cantfind_dm_to_delete(client, token_headers):
    header = token_headers[1]

    response = client.delete('/admin/datamodel/doesnotexist', headers=header)

    assert response.status_code == 404

    res = response.json
    print(res)

def test_cantfind_dm_where_standaloneprop_should_delete(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.delete('/admin/datamodel/doesnotexist/property/hyha:testProp2', headers=header)

    assert response.status_code == 404

    res = response.json
    print(res)

def test_cantfind_standaloneprop(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.delete('/admin/datamodel/hyha/property/hyha:doesnotexist', headers=header)

    assert response.status_code == 404

    res = response.json
    print(res)

def test_cantfind_resource_to_delete(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.delete('/admin/datamodel/hyha/doesnotexist', headers=header)
    assert response.status_code == 404

    res = response.json
    print(res)

def test_cantfind_dm_to_delete_resource(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.delete('/admin/datamodel/doesnotexist/doesnotexist', headers=header)
    assert response.status_code == 404

    res = response.json
    print(res)

def test_cantfind_dm_to_delete_hasprop(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.delete('/admin/datamodel/doesnotexist/hyha:Sheep/hyha:testProp2', headers=header)
    assert response.status_code == 404

    res = response.json
    print(res)

def test_cantfind_hasprop_or_resource_to_delete(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.delete('/admin/datamodel/hyha/doesnotexist/hyha:testProp2', headers=header)
    assert response.status_code == 404

    res = response.json
    print(res)

    response = client.delete('/admin/datamodel/hyha/hyha:Sheep/doesnotexist', headers=header)
    assert response.status_code == 404

    res = response.json
    print(res)

def test_bad_token_hasprop(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.delete('/admin/datamodel/hyha/hyha:Sheep/hyha:testProp2', headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"

def test_bad_token_whole_dm(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.delete('/admin/datamodel/hyha', headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"

def test_bad_token_standaloneprop(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.delete('/admin/datamodel/doesnotexist/property/hyha:testProp2', headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"

def test_cantfind_dm_where_whole_dm_should_be_deleted(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.delete('/admin/datamodel/doesnotexist', headers=header)

    assert response.status_code == 404

    res = response.json
    print(res)
