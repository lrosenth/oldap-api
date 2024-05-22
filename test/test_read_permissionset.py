def test_read_permissionset(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.get('/admin/permissionset/testpermission', headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)
