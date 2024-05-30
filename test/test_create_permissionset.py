def test_create_permissionset(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/permissionset/oldap/testpermissionset', json={
        "label": ["testPerm@en", "test@Perm@de"],
        "comment": ["For testing@en", "Für Tests@de"],
        "givesPermission": "DATA_UPDATE",
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)


def test_create_permissionset_with_empty_fields(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/permissionset/oldap:SystemProject/testpermissionset', json={
        "comment": ["For testing@en", "Für Tests@de"],
        "givesPermission": "DATA_UPDATE",
    }, headers=header)

    # assert response.status_code == 200
    res = response.json
    print(res)
