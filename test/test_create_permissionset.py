def test_create_permissionset(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/permissionset/testpermissionset', json={
        "label": ["testPerm@en", "test@Perm@de"],
        "comment": ["For testing@en", "Für Tests@de"],
        "givesPermission": ["DATA_UPDATE"],
        "definedByProject": "omas:SystemProject"
    }, headers=header)

    # assert response.status_code == 200
    res = response.json
    print(res)
