def test_search_permissionset(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.get('/admin/permissionset/search', json={
        "label": "testPerm"
    }, headers=header)

    # assert response.status_code == 200
    res = response.json
    print(res)
