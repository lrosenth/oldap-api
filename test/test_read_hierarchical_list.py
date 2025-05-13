from pprint import pprint

# Funktion zum Durchsuchen der Liste (rekursiv)
def extract_oldapListNodeIds(hlist, found_nodes):
    for node in hlist['nodes']:
        if "oldapListNodeId" in node:
            found_nodes.add(node["oldapListNodeId"])
        if "nodes" in node:
            extract_oldapListNodeIds(node, found_nodes)

def test_read_hlist(client, token_headers, testfullhlist):
    header = token_headers[1]

    response = client.get('/admin/hlist/hyha/testfullhlist', json={
        "label": ["testlabel@en"],
        "definition": ["testdefinition@en"]
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    pprint(res)
    # Liste der zu überprüfenden Werte
    required_nodes = {"nodeA", "nodeB", "nodeC", "nodeBA", "nodeBB", "nodeBC", "nodeBBA", "nodeBBB", "nodeBBC", "nodeBBBA"}

    # Überprüfung
    found_nodes = set()
    extract_oldapListNodeIds(res, found_nodes)

    # Ergebnis ausgeben
    missing_nodes = required_nodes - found_nodes
    assert not missing_nodes

def test_bad_token(client, token_headers):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.get('/admin/hlist/hyha/testhlist', json={
        "label": ["testlabel@en"],
        "definition": ["testdefinition@en"]
    }, headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"

def test_dm_to_read_hlist_not_found(client, token_headers):
    header = token_headers[1]

    response = client.get('/admin/hlist/doesnotexist/testhlist', json={
        "label": ["testlabel@en"],
        "definition": ["testdefinition@en"]
    }, headers=header)
    assert response.status_code == 404
    res = response.json
    print(res)

def test_hlist_to_read_not_found(client, token_headers):
    header = token_headers[1]

    response = client.get('/admin/hlist/hyha/doesnotexist', json={
        "label": ["testlabel@en"],
        "definition": ["testdefinition@en"]
    }, headers=header)
    assert response.status_code == 404
    res = response.json
    print(res)

def test_hliest_read_node_01(client, token_headers, testfullhlist):
    header = token_headers[1]

    response = client.get('/admin/hlist/hyha/testfullhlist/nodeA', headers=header)
    res = response.json
    pprint(res)
    assert res['nodeid'] == 'nodeA'
    assert res['prefLabel'] == ['testrootnodelabel@en']
    assert res['definition'] == ['testrootnodedefinition@en']

def test_hlist_read_node_02(client, token_headers, testfullhlist):
    header = token_headers[1]

    response = client.get('/admin/hlist/hyha/testfullhlist/nodeBA', headers=header)
    res = response.json
    pprint(res)
    assert res['nodeid'] == 'nodeBA'
    assert res['prefLabel'] == ['testrootnodelabel@en']
    assert res['definition'] == ['testrootnodedefinition@en']

def test_hlist_read_node_nonexistent(client, token_headers, testfullhlist):
    header = token_headers[1]

    response = client.get('/admin/hlist/hyha/testfullhlist/nodeXX', headers=header)
    assert response.status_code == 404
    res = response.json
    print(res)

def test_hlist_read_node_hlist_wrong(client, token_headers, testfullhlist):
    header = token_headers[1]

    response = client.get('/admin/hlist/hyha/gaga/nodeA', headers=header)
    assert response.status_code == 404
    res = response.json
    print(res)

def test_hlist_read_node_project_wrong(client, token_headers, testfullhlist):
    header = token_headers[1]

    response = client.get('/admin/hlist/gaga/testfullhlist/nodeA', headers=header)
    assert response.status_code == 404
    res = response.json
    print(res)

def test_hlist_read_node_invalid_name(client, token_headers, testfullhlist):
    header = token_headers[1]

    response = client.get('/admin/hlist/hyha/testfullhlist/0123', headers=header)
    assert response.status_code == 403
    res = response.json
    print(res)

def test_hlist_read_node_invalid_hlist(client, token_headers, testfullhlist):
    header = token_headers[1]

    response = client.get('/admin/hlist/hyha/0123/nodeA', headers=header)
    assert response.status_code == 403
    res = response.json
    print(res)

def test_hlist_read_node_invalid_project(client, token_headers, testfullhlist):
    header = token_headers[1]

    response = client.get('/admin/hlist/0123/testfullhlist/nodeA', headers=header)
    assert response.status_code == 403
    res = response.json
    print(res)


