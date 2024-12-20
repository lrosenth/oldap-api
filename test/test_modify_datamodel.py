from pprint import pprint

from oldaplib.src.xsd.iri import Iri


def test_modify_standaloneprop_langstring(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": ["kappa@de"],
        "description": ["gigakappa@de"],
        "languageIn": {'add': ['zu'], 'del': ['fr', 'it']},
        "uniqueLang": True,
        "minLength": 2,
        "maxLength": 51,
        "pattern": "kappa",
        "minExclusive": 5.6,
        "minInclusive": 5.6,
        "maxExclusive": 5.6,
        "maxInclusive": 5.6,
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)

    response = client.get('/admin/datamodel/hyha', headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)

    for ele in res["standaloneProperties"]:
        if Iri(ele["iri"]).prefix != "hyha":
            continue

        assert ele["name"] == ["kappa@de"]
        assert ele["description"] == ["gigakappa@de"]
        assert set(ele["languageIn"]) == set(["en", "de", "zu"])
        assert ele["uniqueLang"] == True
        assert ele["minLength"] == '2'
        assert ele["maxLength"] == '51'
        assert ele["pattern"] == "kappa"
        assert ele["minExclusive"] == '5.6'
        assert ele["minInclusive"] == '5.6'
        assert ele["maxExclusive"] == '5.6'
        assert ele["maxInclusive"] == '5.6'

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "languageIn": ["en", "de"],
    }, headers=header)
    assert response.status_code == 200
    response = client.get('/admin/datamodel/hyha', headers=header)
    res = response.json

    for ele in res["standaloneProperties"]:
        if Iri(ele["iri"]).prefix != "hyha":
            continue

        assert set(ele["languageIn"]) == set(["en", "de", ])


def test_modify_standaloneprop_string(client, token_headers, testfulldatamodelstandalonepropstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp3', json={
        "name": ["kappa@de"],
        "description": ["gigakappa@de"],
        #"inSet": ["gugus"],
        "inSet": {"add": ["gigi"], "del": ["gugus", "Gaga"]},
        "minLength": 2,
        "maxLength": 51,
        "pattern": "kappa",
        "minExclusive": 5.6,
        "minInclusive": 5.6,
        "maxExclusive": 5.6,
        "maxInclusive": 5.6,
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)

    response = client.get('/admin/datamodel/hyha', headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)
    for ele in res["standaloneProperties"]:
        if Iri(ele["iri"]).prefix != "hyha":
            continue

        assert ele["name"] == ["kappa@de"]
        assert ele["description"] == ["gigakappa@de"]
        assert set(ele["inSet"]) == set(["gigi", "Kappa"])
        assert ele["minLength"] == '2'
        assert ele["maxLength"] == '51'
        assert ele["pattern"] == "kappa"
        assert ele["minExclusive"] == '5.6'
        assert ele["minInclusive"] == '5.6'
        assert ele["maxExclusive"] == '5.6'
        assert ele["maxInclusive"] == '5.6'

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp3', json={
        "inSet": ["gugus"],
    }, headers=header)
    assert response.status_code == 200
    res = response.json

    response = client.get('/admin/datamodel/hyha', headers=header)
    assert response.status_code == 200
    res = response.json

    for ele in res["standaloneProperties"]:
        if Iri(ele["iri"]).prefix != "hyha":
            continue

        assert ele["inSet"] == ["gugus"]


def test_modify_resource(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "closed": False,
        #"label": ["Ein Test@de"],
        #"comment": ["A test comment@en"],
        "label": {"add": ["Ein Test@zu"], "del": ["Eine Buchseite@de"]},
        "comment": {"add": ["Ein Test@zu"], "del": ["A page of a book@en"]},
        "hasProperty": [
            {
                "property": {
                    "iri": "hyha:testProp2",
                    "uniqueLang": False,
                },
                "maxCount": 3,
                "minCount": 1,
                "order": 1
            }
        ]
    }, headers=header)
    res = response.json
    print(res)

    response = client.get('/admin/datamodel/hyha', headers=header)
    assert response.status_code == 200
    res = response.json
    pprint(res)
    assert res["resources"][0]["closed"] == False
    assert set(res["resources"][0]["label"]) == set(['A page of a book@en', "Ein Test@zu"])
    assert set(res["resources"][0]["comment"]) == set(["Eine Buchseite@de", "Ein Test@zu"])

def test_bad_token_standaloneprop(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.post('/admin/datamodel/hyha/hyha:testProp/mod', headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"

def test_cantfind_dm_to_modify(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/doesnotexist/hyha:testProp/mod', headers=header)

    assert response.status_code == 404

    res = response.json
    print(res)


def test_modify_attribute_in_has_prop(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/hyha:Sheep/hyha:testProp2', json={
        "property": {
            "name": ["pappakappa@de"],
            "languageIn": {"add": ["zu"], "del": ["fr"]}
        },
        "maxCount": 4,
        "minCount": 2,
        "order": 42
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)

    response = client.get('/admin/datamodel/hyha', headers=header)
    assert response.status_code == 200
    res = response.json
    pprint(res)

    # response = client.post('/admin/datamodel/hyha/hyha:Sheep/hyha:testProp2', json={
    #     "property": {
    #         "name": ["pappakappa@de"],
    #         "languageIn": {"add": ["zu"], "del": ["fr"]}
    #     },
    #     "maxCount": 4,
    #     "minCount": 2,
    #     "order": 42
    # }, headers=header)
    # assert response.status_code == 200
    # res = response.json
    # print(res)
    #
    # response = client.get('/admin/datamodel/hyha', headers=header)
    # assert response.status_code == 200
    # res = response.json
    # pprint(res)


def test_unknown_json_fields_for_property_modifier(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/hyha:Sheep/hyha:testProp2', json={
        "Doesnotexist": "kappa1234",
        "property": {
            "name": ["pappakappa@de"],
            "languageIn": {"add": ["zu"], "del": ["fr"]}
        },
        "maxCount": 4,
        "minCount": 2,
        "order": 42
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

    response = client.post('/admin/datamodel/hyha/hyha:Sheep/hyha:testProp2', json={}, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_unknown_json_fields_for_property_in_property_modifier(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/hyha:Sheep/hyha:testProp2', json={
        "property": {
            "doesnotexist": "kappa1234",
            "name": ["pappakappa@de"],
            "languageIn": {"add": ["zu"], "del": ["fr"]}
        },
        "maxCount": 4,
        "minCount": 2,
        "order": 42
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

    response = client.post('/admin/datamodel/hyha/hyha:Sheep/hyha:testProp2', json={}, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

    response = client.post('/admin/datamodel/hyha/hyha:Sheep/hyha:testProp2', json={
        "property": {},
        "maxCount": 4,
        "minCount": 2,
        "order": 42
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

    response = client.post('/admin/datamodel/hyha/hyha:Sheep/hyha:testProp2', json={}, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_bad_fields_modify_property(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/hyha:Sheep/hyha:testProp2', json={
        "property": {
            "name": ["pappakappa@de"],
            "languageIn": {"add": ["zu"], "del": ["fr"]}
        },
        "maxCount": 4,
        "minCount": 2,
        "order": 42
    }, headers=header)

def test_bad_fields_in_modify_attribute_in_has_prop(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/hyha:Sheep/hyha:testProp2', json={
        "property": {
            "name": ["pappakappa@de"],
            "languageIn": {"add": "zu"}
        }
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

    response = client.post('/admin/datamodel/hyha/hyha:Sheep/hyha:testProp2', json={
        "property": {
            "name": ["pappakappa@de"],
            "languageIn": {"del": "zu"}
        }
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)
