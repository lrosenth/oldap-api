from pprint import pprint


def test_modify_hlist_01(client, token_headers, testfullhlist):
    header = token_headers[1]

    response = client.post('/admin/hlist/hyha/testfullhlist', json={
        "prefLabel": ["testlabel new@en"],
        "definition": ["testdefinition new@en"]
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)

    response = client.get('/admin/hlist/hyha/testfullhlist', headers=header)
    res = response.json
    assert res["definition"] == ["testdefinition new@en"]
    assert res["prefLabel"] == ["testlabel new@en"]

def test_modify_hlist_02(client, token_headers, testfullhlist):
    header = token_headers[1]

    response = client.post('/admin/hlist/hyha/testfullhlist', json={
        "prefLabel": {"add": ["testlabel new@en", "testlabel neu@de"]},
        "definition": None
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)

    response = client.get('/admin/hlist/hyha/testfullhlist', headers=header)
    res = response.json
    assert set(res["prefLabel"]) == {"testlabel new@en", "testlabel neu@de"}
    assert res.get("definition") == None

def test_modify_node_01(client, token_headers, testfullhlist):
    header = token_headers[1]

    response = client.post('/admin/hlist/hyha/testfullhlist/nodeA', json={
        "prefLabel": ["kappa@de"],
        "definition": ["gaga@en"],
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)

    response = client.get('/admin/hlist/hyha/testfullhlist', headers=header)
    res = response.json
    assert res['nodes'][0]["oldapListNodeId"] == 'nodeA'
    assert res['nodes'][0]["definition"] == ["gaga@en"]
    assert res['nodes'][0]["prefLabel"] == ['kappa@de']

def test_modify_node_02(client, token_headers, testfullhlist):
    header = token_headers[1]

    response = client.post('/admin/hlist/hyha/testfullhlist/nodeBB', json={
        "prefLabel": {"add": ["KAPPA1234@zu"]}
    }, headers=header)
    assert response.status_code == 200
    res = response.get_json()
    print(res)
    response = client.get('/admin/hlist/hyha/testfullhlist', headers=header)
    res = response.json
    pprint(res)


def test_cant_find_node_to_modify_preflabel(client, token_headers, testfullhlist):
    header = token_headers[1]

    response = client.post('/admin/hlist/hyha/testfullhlist/nodeDoesNotExist', json={
        "prefLabel": "kappa@de",
        "definition": "gaga",
    }, headers=header)
    assert response.status_code == 404
    res = response.json
    print(res)

def test_double_language_tag(client, token_headers, testfullhlist):
    header = token_headers[1]

    response = client.post('/admin/hlist/hyha/testfullhlist/nodeA', json={
        "prefLabel": "kappa@de@de",
        "definition": "gaga",
    }, headers=header)
    # assert response.status_code == 404
    res = response.json
    print(res)
    response = client.get('/admin/hlist/hyha/testfullhlist', headers=header)
    res = response.json
    pprint(res)

def test_bad_json(client, token_headers, testfullhlist):
    header = token_headers[1]

    response = client.post('/admin/hlist/hyha/testfullhlist/nodeA', json={
        "doesnotexist": "kappa@de",
        "definition": "gaga",
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

    response = client.post('/admin/hlist/hyha/testfullhlist/nodeA', json={
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

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
        "hasRole": {"oldap:Unknown": "DATA_VIEW"},
    }, headers=header)

    login = client.post('/admin/auth/rosmankappa', json={'password': 'kappa1234'})
    token = login.json['token']
    headers = {
        'Authorization': f'Bearer {token}'
    }

    response2 = client.post('/admin/hlist/hyha/testfullhlist/nodeA', json={
        "prefLabel": ["kappa@de"],
        "definition": ["gaga@en"],
    }, headers=headers)
    res2 = response2.json
    print(res2)
    assert response2.status_code == 403

def test_bad_token(client, token_headers):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.post('/admin/hlist/hyha/testfullhlist/nodeA', json={
        "prefLabel": "kappa@de",
        "definition": "gaga",
    }, headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"

