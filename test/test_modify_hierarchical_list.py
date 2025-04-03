from pprint import pprint


def test_modify_node(client, token_headers, testfullhlist):
    header = token_headers[1]

    response = client.post('/admin/hlist/hyha/testfullhlist/nodeA', json={
        "prefLabel": "kappa@de",
        "definition": "gaga",
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)

    response = client.get('/admin/hlist/hyha/testfullhlist', headers=header)
    res = response.json
    pprint(res)
    # assert res[0]["oldapListNodeId"] == 'nodeA'
    # assert res[0]["definition"] == ["gaga@en"]
    # assert res[0]["prefLabel"] == ['nodeA@en', 'kappa@de']
