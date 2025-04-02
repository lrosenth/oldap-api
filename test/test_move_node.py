from pprint import pprint

def build_tree(nodes):
    tree = {}
    for node in nodes:
        node_id = node.get('oldapListNodeId')
        if 'nodes' in node:
            tree[node_id] = build_tree(node['nodes'])
        else:
            tree[node_id] = []
    return tree

def test_move_node(client, token_headers, testfullhlist):
    header = token_headers[1]

    response = client.post('/admin/hlist/hyha/testfullhlist/nodeBB/move', json={
        "leftOf": "nodeA"
    }, headers=header)
    assert response.status_code == 200
    res = response.get_json()
    print(res)
    response = client.get('/admin/hlist/hyha/testfullhlist', headers=header)
    res = response.json
    expected_tree = {
        "nodeBB": {
            "nodeBBA": [],
            "nodeBBB": {
                "nodeBBBA": []
            },
            "nodeBBC": []
        },
        "nodeA": [],
        "nodeB": {
            "nodeBA": [],
            "nodeBC": []
        },
        "nodeC": []
    }
    actual_tree = build_tree(res)
    assert actual_tree == expected_tree

    response = client.post('/admin/hlist/hyha/testfullhlist/nodeBB/move', json={
        "belowOf": "nodeBC"
    }, headers=header)
    assert response.status_code == 200
    res = response.get_json()
    print(res)
    response = client.get('/admin/hlist/hyha/testfullhlist', headers=header)
    res = response.json
    expected_tree = {
        "nodeA": [],
        "nodeB": {
            "nodeBA": [],
            "nodeBC": {
                "nodeBB": {
                    "nodeBBA": [],
                    "nodeBBB": {
                        "nodeBBBA": []
                    },
                    "nodeBBC": []
                },
            }
        },
        "nodeC": []
    }
    actual_tree = build_tree(res)
    assert actual_tree == expected_tree

    response = client.post('/admin/hlist/hyha/testfullhlist/nodeBBB/move', json={
        "rightOf": "nodeBC"
    }, headers=header)
    assert response.status_code == 200
    res = response.get_json()
    print(res)
    response = client.get('/admin/hlist/hyha/testfullhlist', headers=header)
    res = response.json
    expected_tree = {
        "nodeA": [],
        "nodeB": {
            "nodeBA": [],
            "nodeBC": {
                "nodeBB": {
                    "nodeBBA": [],
                    "nodeBBC": []
                },
            },
            "nodeBBB": {
                "nodeBBBA": []
            },
        },
        "nodeC": []
    }
    actual_tree = build_tree(res)
    assert actual_tree == expected_tree

def test_bad_move_node(client, token_headers, testfullhlist):
    header = token_headers[1]

    response = client.post('/admin/hlist/hyha/testfullhlist/nodeBB/move', json={
        "kappa": "nodeA"
    }, headers=header)
    assert response.status_code == 400
    res = response.get_json()
    print(res)

    response = client.post('/admin/hlist/hyha/testfullhlist/nodeBB/move', json={
    }, headers=header)
    assert response.status_code == 400
    res = response.get_json()
    print(res)

    response = client.post('/admin/hlist/hyha/testfullhlist/nodeBB/move', json={
        "leftOf": "nodeA",
        "rightOf": "nodeA"
    }, headers=header)
    assert response.status_code == 400
    res = response.get_json()
    print(res)

def test_move_vather_node_below_of_children(client, token_headers, testfullhlist):
    header = token_headers[1]

    response = client.post('/admin/hlist/hyha/testfullhlist/nodeBB/move', json={
        "belowOf": "nodeBBA"
    }, headers=header)
    # assert response.status_code == 200
    res = response.get_json()
    print(res)

    response = client.get('/admin/hlist/hyha/testfullhlist', headers=header)
    res = response.json
    pprint(res)


def test_cant_find_node_to_move(client, token_headers, testfullhlist):
    header = token_headers[1]

    response = client.post('/admin/hlist/hyha/testfullhlist/doesnotexist/move', json={
        "leftOf": "nodeA"
    }, headers=header)
    assert response.status_code == 404
    res = response.get_json()
    print(res)

def test_bad_token(client, token_headers):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.post('/admin/hlist/hyha/testfullhlist/nodeBB/move', json={
        "leftOf": "nodeA"
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

    response2 = client.post('/admin/hlist/hyha/testfullhlist/nodeBB/move', json={
        "leftOf": "nodeA"
    }, headers=headers)
    res2 = response2.json
    print(res2)
    assert response2.status_code == 403










