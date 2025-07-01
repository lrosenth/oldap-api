from pprint import pprint

# Funktion zum Durchsuchen der Liste (rekursiv)
def extract_oldapListNodeIds(hlist, found_nodes):
    for node in hlist['nodes']:
        if "oldapListNodeId" in node:
            found_nodes.add(node["oldapListNodeId"])
        if "nodes" in node:
            extract_oldapListNodeIds(node, found_nodes)


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

    # Überprüfung
    found_nodes = set()
    extract_oldapListNodeIds(res, found_nodes)

    # Ergebnis ausgeben
    missing_nodes = required_nodes - found_nodes
    assert not missing_nodes

def test_bad_del_hlist_node_recursively(client, token_headers, testfullhlist):
    header = token_headers[1]

    response = client.delete('/admin/hlist/hyha/testfullhlist/nodeBB', query_string={
        "kappa": True
    }, headers=header)

    assert response.status_code == 400
    res = response.get_json()
    print(res)

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
    res = response.get_json()
    print(res)
    assert response.status_code == 409

def test_node_to_delete_not_found(client, token_headers, testfullhlist):
    header = token_headers[1]

    response = client.delete('/admin/hlist/hyha/testfullhlist/nodeKAPPA', query_string={
        "recursive": False
    }, headers=header)
    assert response.status_code == 404
    res = response.get_json()
    print(res)

    response = client.delete('/admin/hlist/hyha/testfullhlist/nodeKAPPA', query_string={
        "recursive": True
    }, headers=header)
    assert response.status_code == 404
    res = response.get_json()
    print(res)

def test_bad_token(client, token_headers, testfullhlist):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.delete('/admin/hlist/hyha/testfullhlist/nodeBB', query_string={
        "recursive": True
    }, headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"

def test_no_permission(client, token_headers, testfullhlist):
    header = token_headers[1]

    client.put('/admin/user/rosmankappa', json={
        "givenName": "Kappauser",
        "familyName": "KappaKappatest",
        "email": "kappa@kappa.com",
        "password": "kappa1234",
        "inProjects": [
            {
                "project": "http://www.salsah.org/version/2.0/SwissBritNet",
            }
        ],
        "hasPermissions": [
            "GenericRestricted"
        ]
    }, headers=header)

    login = client.post('/admin/auth/rosmankappa', json={'password': 'kappa1234'})
    token = login.json['token']
    headers = {
        'Authorization': f'Bearer {token}'
    }

    response2 = client.delete('/admin/hlist/hyha/testfullhlist/nodeA', query_string={
        "recursive": False
    }, headers=headers)
    res2 = response2.json
    print(res2)
    assert response2.status_code == 403

    response2 = client.delete('/admin/hlist/hyha/testfullhlist/nodeA', query_string={
        "recursive": True
    }, headers=headers)
    res2 = response2.json
    print(res2)
    assert response2.status_code == 403
