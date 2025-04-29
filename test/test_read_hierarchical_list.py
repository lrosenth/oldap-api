from pprint import pprint

# Funktion zum Durchsuchen der Liste (rekursiv)
def extract_oldapListNodeIds(nodes, found_nodes):
    for node in nodes:
        if "oldapListNodeId" in node:
            found_nodes.add(node["oldapListNodeId"])
        if "nodes" in node:
            extract_oldapListNodeIds(node["nodes"], found_nodes)

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

