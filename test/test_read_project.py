def test_read_project(client, token_headers, testproject):
    header = token_headers[1]

    response = client.get('/admin/project/testproject', headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)


