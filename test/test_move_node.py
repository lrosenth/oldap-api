from pprint import pprint


def test_move_node(client, token_headers, testfullhlist):
    header = token_headers[1]

    response = client.post('/admin/hlist/hyha/testfullhlist/nodeBB/move', json={
        "root": 1234
    }, headers=header)

    assert response.status_code == 200
    res = response.get_json()
    print(res)

    response = client.get('/admin/hlist/hyha/testfullhlist', headers=header)
    res = response.json
    pprint(res)
