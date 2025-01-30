


def test_del_hlist_node(client, token_headers, testfullhlist):
    header = token_headers[1]

    response = client.delete('/admin/hlist/hyha/testfullhlist/nodeA', headers=header)

    assert response.status_code == 200
    res = response.get_json()
    print(res)
