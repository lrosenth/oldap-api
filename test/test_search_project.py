def test_search_project(client, token_headers, testproject):
    header = token_headers[1]

    response = client.get('/admin/project/search', json={
        "label": "unittest"
    }, headers=header)

    res = response.json
    print(res)


