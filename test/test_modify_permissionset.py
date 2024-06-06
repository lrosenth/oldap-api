def test_modify_label(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": "Kappa@fr"
    }, headers=header)

    assert response.status_code == 200

    response2 = client.get('/admin/permissionset/oldap/testpermissionset', headers=header)
    res = response2.json
    print(res)
    assert res.get('label') == ['Kappa@fr']
