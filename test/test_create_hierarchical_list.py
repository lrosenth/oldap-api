def test_create_empty_hlist(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/hlist/hyha/testhlist', json={
        "label": ["testlabel@en"],
        "definition": ["testdefinition@en"]
    }, headers=header)

    assert response.status_code == 200
    res = response.get_json()
    print(res)

    response = client.get('/admin/hlist/hyha/testhlist', headers=header)
    res = response.json
    print(res)
