from pprint import pprint


def test_create_empty_hlist(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/hlist/hyha/testhlist', json={
        "label": ["testlabel@en"],
        "definition": ["testdefinition@en"]
    }, headers=header)

    assert response.status_code == 200
    res = response.get_json()
    print(res)

    response = client.get('/admin/hlist/hyha/testhlist', headers=header)
    res = response.json
    print(res)

def test_create_root_node(client, token_headers, testemptyhlist):
    header = token_headers[1]

    response = client.put('/admin/hlist/hyha/testhlist/testrootnode', json={
        "label": ["testrootnodelabel@en"],
        "definition": ["testrootnodedefinition@en"],
        "position": "root"
    }, headers=header)
    res = response.get_json()
    print(res)
    assert response.status_code == 200

    response = client.get('/admin/hlist/hyha/testhlist', headers=header)
    res = response.json
    assert len(res) == 1
    assert res[0]["prefLabel"] == ["testrootnodelabel@en"]
    assert res[0]["definition"] == ["testrootnodedefinition@en"]

def test_create_right_node(client, token_headers, testemptyhlist):
    header = token_headers[1]

    response = client.put('/admin/hlist/hyha/testhlist/testrootnode', json={
        "label": ["testrootnodelabel@en"],
        "definition": ["testrootnodedefinition@en"],
        "position": "root"
    }, headers=header)
    res = response.get_json()
    print(res)
    assert response.status_code == 200

    response = client.put('/admin/hlist/hyha/testhlist/nodeA', json={
        "label": ["testrootnodelabel@en"],
        "definition": ["testrootnodedefinition@en"],
        "position": "right",
        "refnode": "testrootnode"
    }, headers=header)
    res = response.get_json()
    print(res)
    assert response.status_code == 200
