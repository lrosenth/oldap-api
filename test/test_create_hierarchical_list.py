from pprint import pprint


def test_create_empty_hlist(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/hlist/hyha/testhlist', json={
        "prefLabel": ["testlabel@en"],
        "definition": ["testdefinition@en"]
    }, headers=header)

    assert response.status_code == 200
    res = response.get_json()
    print(res)

    response = client.get('/admin/hlist/hyha/testhlist', headers=header)
    res = response.json
    print(res)

def test_bad_create_empty_hlist(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/hlist/hyha/testhlist', json={
        "kappa": ["testlabel@en"],
        "definition": ["testdefinition@en"]
    }, headers=header)
    assert response.status_code == 400
    res = response.get_json()
    print(res)

    response = client.put('/admin/hlist/hyha/testhlist', json={
        "definition": ["testdefinition@en"]
    }, headers=header)
    assert response.status_code == 400
    res = response.get_json()
    print(res)

    response = client.put('/admin/hlist/hyha/testhlist', json={
        "prefLabel": [],
        "definition": ["testdefinition@en"]
    }, headers=header)
    assert response.status_code == 400
    res = response.get_json()
    print(res)

def test_dm_to_add_empty_hlist_not_found(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/hlist/doesnotexist/testhlist', json={
        "prefLabel": ["testlabel@en"],
        "definition": ["testdefinition@en"]
    }, headers=header)
    assert response.status_code == 404
    res = response.get_json()
    print(res)

def test_empty_node_already_exists(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/hlist/hyha/testhlist', json={
        "prefLabel": ["testlabel@en"],
        "definition": ["testdefinition@en"]
    }, headers=header)
    assert response.status_code == 200
    res = response.get_json()
    print(res)

    response = client.put('/admin/hlist/hyha/testhlist', json={
        "prefLabel": ["testlabel@en"],
        "definition": ["testdefinition@en"]
    }, headers=header)
    assert response.status_code == 409
    res = response.get_json()
    print(res)

def test_no_json_to_create_empty_hlist(client, token_headers):
    header = token_headers[1]
    response = client.put('/admin/hlist/hyha/testhlist', 'KEIN JSON', headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)
    assert 'message' in res
    assert res['message'] == "JSON expected. Instead received None"

def test_create_root_node(client, token_headers, testemptyhlist):
    header = token_headers[1]

    response = client.put('/admin/hlist/hyha/testhlist/nodeA', json={
        "prefLabel": ["testrootnodelabel@en"],
        "definition": ["testrootnodedefinition@en"],
        "position": "root"
    }, headers=header)
    res = response.get_json()
    print(res)
    assert response.status_code == 200

    response = client.put('/admin/hlist/hyha/testhlist/nodeB', json={
        "prefLabel": ["testrootnodelabel@en"],
        "definition": ["testrootnodedefinition@en"],
        "position": "leftOf",
        "refnode": "nodeA"
    }, headers=header)
    res = response.get_json()
    print(res)
    assert response.status_code == 200

    response = client.put('/admin/hlist/hyha/testhlist/nodeC', json={
        "prefLabel": ["testrootnodelabel@en"],
        "definition": ["testrootnodedefinition@en"],
        "position": "rightOf",
        "refnode": "nodeB"
    }, headers=header)
    res = response.get_json()
    print(res)
    assert response.status_code == 200

    response = client.get('/admin/hlist/hyha/testhlist', headers=header)
    res = response.json
    assert len(res['nodes']) == 3
    assert res['nodes'][0]["prefLabel"] == ["testrootnodelabel@en"]
    assert res['nodes'][0]["definition"] == ["testrootnodedefinition@en"]
    assert res['nodes'][0]["oldapListNodeId"] == "nodeB"
    assert res['nodes'][1]["oldapListNodeId"] == "nodeC"
    assert res['nodes'][2]["oldapListNodeId"] == "nodeA"

def test_bad_create_root_node(client, token_headers, testemptyhlist):
    header = token_headers[1]
    response = client.put('/admin/hlist/hyha/testhlist/testrootnode', json={
        "kappa": ["testrootnodelabel@en"],
        "definition": ["testrootnodedefinition@en"],
        "position": "root"
    }, headers=header)
    assert response.status_code == 400
    res = response.get_json()
    print(res)

    response = client.put('/admin/hlist/hyha/testhlist/testrootnode', json={
        "definition": ["testrootnodedefinition@en"],
        "position": "root"
    }, headers=header)
    assert response.status_code == 400
    res = response.get_json()
    print(res)

    response = client.put('/admin/hlist/hyha/testhlist/testrootnode', json={
        "prefLabel": ["testrootnodelabel@en"],
        "definition": ["testrootnodedefinition@en"],
        "position": "kappa"
    }, headers=header)
    assert response.status_code == 400
    res = response.get_json()
    print(res)

    response = client.put('/admin/hlist/hyha/testhlist/testrootnode', json={
        "prefLabel": ["testrootnodelabel@en"],
        "definition": ["testrootnodedefinition@en"],
        "position": "leftOf"
    }, headers=header)
    assert response.status_code == 400
    res = response.get_json()
    print(res)

    response = client.put('/admin/hlist/hyha/testhlist/testrootnode', json={
        "prefLabel": [],
        "definition": ["testrootnodedefinition@en"],
        "position": "root"
    }, headers=header)
    assert response.status_code == 400
    res = response.get_json()
    print(res)

def test_node_already_exists(client, token_headers, testemptyhlist):
    header = token_headers[1]

    response = client.put('/admin/hlist/hyha/testhlist/nodeA', json={
        "prefLabel": ["testrootnodelabel@en"],
        "definition": ["testrootnodedefinition@en"],
        "position": "root"
    }, headers=header)
    res = response.get_json()
    print(res)
    assert response.status_code == 200

    response = client.put('/admin/hlist/hyha/testhlist/nodeA', json={
        "prefLabel": ["testrootnodelabel@en"],
        "definition": ["testrootnodedefinition@en"],
        "position": "root"
    }, headers=header)
    res = response.get_json()
    print(res)
    assert response.status_code == 409
    response = client.get('/admin/hlist/hyha/testhlist', headers=header)
    res = response.json
    pprint(res)

def test_dm_to_add_empty_hlist_not_found(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/hlist/doesnotexist/testhlist', json={
        "prefLabel": ["testrootnodelabel@en"],
        "definition": ["testrootnodedefinition@en"],
    }, headers=header)
    assert response.status_code == 404
    res = response.get_json()
    print(res)

def test_create_below_node(client, token_headers, testemptyhlist):
    header = token_headers[1]

    response = client.put('/admin/hlist/hyha/testhlist/nodeA', json={
        "prefLabel": ["testrootnodelabel@en"],
        "definition": ["testrootnodedefinition@en"],
        "position": "root"
    }, headers=header)
    res = response.get_json()
    print(res)
    assert response.status_code == 200

    response = client.put('/admin/hlist/hyha/testhlist/nodeB', json={
        "prefLabel": ["testrootnodelabel@en"],
        "definition": ["testrootnodedefinition@en"],
        "position": "belowOf",
        "refnode": "nodeA"
    }, headers=header)
    res = response.get_json()
    print(res)
    assert response.status_code == 200

    response = client.get('/admin/hlist/hyha/testhlist', headers=header)
    res = response.json
    pprint(res)
    assert res['nodes'][0]["oldapListNodeId"] == "nodeA"
    assert res['nodes'][0]["nodes"][0]["oldapListNodeId"] == "nodeB"

    response = client.put('/admin/hlist/hyha/testhlist/nodeC', json={
        "prefLabel": 1234,
        "definition": ["testrootnodedefinition@en"],
        "position": "belowOf",
        "refnode": "nodeB"
    }, headers=header)
    res = response.get_json()
    print(res)
    assert response.status_code == 400

def test_no_json_to_add_node(client, token_headers, testemptyhlist):
    header = token_headers[1]
    response = client.put('/admin/hlist/hyha/testhlist/nodeB', 'KEIN JSON', headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)
    assert 'message' in res
    assert res['message'] == "JSON expected. Instead received None"


def test_dm_to_add_node_not_found(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/hlist/hyha/testhlist/nodeB', json={
        "prefLabel": ["testrootnodelabel@en"],
        "definition": ["testrootnodedefinition@en"],
        "position": "root"
    }, headers=header)
    assert response.status_code == 404
    res = response.get_json()
    print(res)

def test_bad_token(client, token_headers):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.put('/admin/hlist/hyha/testhlist', json={
        "prefLabel": ["testlabel@en"],
        "definition": ["testdefinition@en"]
    }, headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"

    response = client.put('/admin/hlist/hyha/testhlist/testrootnode', json={
        "prefLabel": ["testrootnodelabel@en"],
        "definition": ["testrootnodedefinition@en"],
        "position": "root"
    }, headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"

    response = client.put('/admin/hlist/hyha/testhlist/testrootnode', json={
        "prefLabel": ["testrootnodelabel@en"],
        "definition": ["testrootnodedefinition@en"],
        "position": "root"
    }, headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"


def test_no_permission(client, token_headers, testemptyhlist):
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

    response2 = client.put('/admin/hlist/hyha/testhlist', json={
        "prefLabel": ["testlabel@en"],
        "definition": ["testdefinition@en"]
    }, headers=headers)
    res2 = response2.json
    print(res2)
    assert response2.status_code == 403

    response2 = client.put('/admin/hlist/hyha/testhlist/nodeB', json={
        "prefLabel": ["testrootnodelabel@en"],
        "definition": ["testrootnodedefinition@en"],
        "position": "root",
    }, headers=headers)
    res2 = response2.json
    print(res2)
    assert response2.status_code == 403

