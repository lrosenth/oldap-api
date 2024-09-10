def test_delete_standalone_property(client, token_headers, testfulldatamodelstandaloneprop):
    header = token_headers[1]

    response = client.delete('/admin/datamodel/hyha/hyha:testProp2/del', headers=header)

    assert response.status_code == 200

    res = response.json
    print(res)
    assert res['message'] == 'Data model successfully deleted'

    response = client.get('/admin/permissionset/testpermission', headers=header)
    assert response.status_code == 404
