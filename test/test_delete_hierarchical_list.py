from pprint import pprint


def test_del_hlist_node_recursively(client, token_headers, testfullhlist):
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

    # Liste der zu überprüfenden Werte
    required_nodes = {"nodeC", "nodeA", "nodeB", "nodeBA", "nodeBC"}

    # Funktion zum Durchsuchen der Liste (rekursiv)
    def extract_oldapListNodeIds(nodes, found_nodes):
        for node in nodes:
            if "oldapListNodeId" in node:
                found_nodes.add(node["oldapListNodeId"])
            if "nodes" in node:
                extract_oldapListNodeIds(node["nodes"], found_nodes)

    # Überprüfung
    found_nodes = set()
    extract_oldapListNodeIds(res, found_nodes)

    # Ergebnis ausgeben
    missing_nodes = required_nodes - found_nodes
    assert not missing_nodes


# Funktion zum Durchsuchen der Liste (rekursiv)
def extract_oldapListNodeIds(nodes, found_nodes):
    for node in nodes:
        if "oldapListNodeId" in node:
            found_nodes.add(node["oldapListNodeId"])
        if "nodes" in node:
            extract_oldapListNodeIds(node["nodes"], found_nodes)


def test_del_hlist_node_non_recursively(client, token_headers, testfullhlist):
    header = token_headers[1]

    response = client.delete('/admin/hlist/hyha/testfullhlist/nodeBBBA', headers=header)

    assert response.status_code == 200
    res = response.get_json()
    print(res)

    response = client.get('/admin/hlist/hyha/testfullhlist', headers=header)
    res = response.json
    pprint(res)

    # Liste der zu überprüfenden Werte
    required_nodes = {"nodeA", "nodeB", "nodeC", "nodeBA", "nodeBB", "nodeBC", "nodeBBA", "nodeBBB", "nodeBBC"}

    # Überprüfung
    found_nodes = set()
    extract_oldapListNodeIds(res, found_nodes)

    # Ergebnis ausgeben
    missing_nodes = required_nodes - found_nodes
    assert not missing_nodes


def test_del_hlist_node_non_recursively_but_still_nodes_attached(client, token_headers, testfullhlist):
    header = token_headers[1]

    response = client.delete('/admin/hlist/hyha/testfullhlist/nodeBB', query_string={
        "recursive": False
    }, headers=header)

    assert response.status_code == 409
