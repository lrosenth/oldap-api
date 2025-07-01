

def test_move_node(client, token_headers, testfullhlist):
    header = token_headers[1]

    response = client.post('/admin/hlist/hyha/testfullhlist/nodeBB', json={
        "prefLabel": ["newlabelForBB@en"]
    }, headers=header)
    assert response.status_code == 200
    res = response.get_json()
    print(res)

