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
