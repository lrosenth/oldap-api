def test_delete_standalone_property(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.delete('/admin/datamodel/hyha/hyha:testProp2/del', headers=header)

    assert response.status_code == 200

    res = response.json
    print(res)
    assert res['message'] == 'Data model successfully deleted'

    response = client.get('/admin/permissionset/testpermission', headers=header)
    assert response.status_code == 404


def test_delete_resource(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.delete('/admin/datamodel/del/hyha/hyha:Sheep', headers=header)

    assert response.status_code == 200

    res = response.json
    print(res)
    assert res['message'] == 'Data model successfully deleted'

    response = client.get('/admin/permissionset/testpermission', headers=header)
    assert response.status_code == 404

def test_delete_property_in_resource(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.delete('/admin/datamodel/hyha/hyha:Sheep/hyha:testProp2/del', headers=header)

    assert response.status_code == 200

    res = response.json
    print(res)
    assert res['message'] == 'Data model successfully deleted'

    response = client.get('/admin/permissionset/testpermission', headers=header)
    assert response.status_code == 404

def test_bad_token(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.delete('/admin/datamodel/hyha/hyha:testProp2/del', headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"

def test_cantfind_dm_where_standaloneprop_should_delete(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.delete('/admin/datamodel/doesnotexist/hyha:testProp2/del', headers=header)

    assert response.status_code == 404

    res = response.json
    print(res)

def test_cantfind_standaloneprop(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.delete('/admin/datamodel/hyha/hyha:doesnotexist/del', headers=header)

    assert response.status_code == 404

    res = response.json
    print(res)

def test_bad_token_res(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.delete('/admin/datamodel/del/hyha/hyha:Sheep', headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"

def test_cantfind_dm_where_resource_should_be_deleted(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.delete('/admin/datamodel/del/doesnotexist/hyha:Sheep', headers=header)

    assert response.status_code == 404

    res = response.json
    print(res)

def test_cantfind_res(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.delete('/admin/datamodel/del/hyha/hyha:doesnotexist', headers=header)

    assert response.status_code == 404

    res = response.json
    print(res)

def test_bad_token_hasprop(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.delete('/admin/datamodel/hyha/hyha:Sheep/hyha:testProp2/del', headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"

def test_cantfind_dm_where_hasprop_should_be_deleted(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.delete('/admin/datamodel/doesnotexist/hyha:Sheep/hyha:testProp2/del', headers=header)

    assert response.status_code == 404

    res = response.json
    print(res)

def test_cantfind_prop_to_delete(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.delete('/admin/datamodel/hyha/hyha:Sheep/doesnotexist/del', headers=header)

    assert response.status_code == 404

    res = response.json
    print(res)
