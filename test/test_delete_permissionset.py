def test_delete_permissionset(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.delete('/admin/permissionset/oldap/testpermissionset', headers=header)

    assert response.status_code == 200

    res = response.json
    assert res['message'] == 'Permissionset successfully deleted'

    response = client.get('/admin/permissionset/testpermission', headers=header)
    assert response.status_code == 404
