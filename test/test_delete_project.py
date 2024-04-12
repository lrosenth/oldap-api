def test_delete_project(client, token_headers, testproject):
    header = token_headers[1]

    response = client.delete('/admin/project/testproject', headers=header)

    assert response.status_code == 200

    res = response.json
    assert res['message'] == 'Project successfully deleted'

    response = client.get('/admin/project/testproject', headers=header)
    assert response.status_code == 400
