def test_modify_project(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "label": "Kappa@fr"
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)

    response = client.get('/admin/project/testproject', headers=header)
    print(response.text)
