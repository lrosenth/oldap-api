from pprint import pprint


def test_del_hlist_node(client, token_headers, testfullhlist):
    header = token_headers[1]

    response = client.delete('/admin/hlist/hyha/testfullhlist/nodeBB', query_string={
        "recursive": True
    }, headers=header)

    assert response.status_code == 200
    res = response.get_json()
    print(res)

    response = client.get('/admin/hlist/hyha/testfullhlist', headers=header)
    res = response.json
    pprint(res)
