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
        pprint(ele)
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

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"add": ["NewKappa@en"], "del": ["Kappa@de"]},
    }, headers=header)
    response = client.get('/admin/datamodel/hyha', headers=header)
    res = response.json
    for ele in res["standaloneProperties"]:
        if Iri(ele["iri"]).prefix != "hyha":
            continue
        print(ele["name"])
        assert ele["name"] == ["NewKappa@en"]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": ["kappa@z"],
    }, headers=header)
    res = response.json
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": ["kappa@zz"],
    }, headers=header)
    res = response.json
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": ["z"],
    }, headers=header)
    res = response.json
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"add": ["NewKappa"], "del": ["Kappa"]},
    }, headers=header)
    res = response.json
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"add": ["a"]},
    }, headers=header)
    res = response.json
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"del": ["a"]},
    }, headers=header)
    res = response.json
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"del": ["Kappa"]},
    }, headers=header)
    res = response.json
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"add": ["NewKappa@zz"]},
    }, headers=header)
    res = response.json
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"add": ["NewKappa@gaga"], "del": ["Kappa@gaga"]},
    }, headers=header)
    res = response.json
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"del": ["Kappa@gaga"]},
    }, headers=header)
    res = response.json
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"del": ["Kappa@zz"]},
    }, headers=header)
    res = response.json
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": None,
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 200
    response = client.get('/admin/datamodel/hyha', headers=header)
    assert response.status_code == 200
    res = response.json
    for ele in res["standaloneProperties"]:
        if Iri(ele["iri"]).prefix != "hyha":
            continue
        assert "name" not in ele

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": "gaga",
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        None: "gaga",
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={}, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "languageIn": None,
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 200
    response = client.get('/admin/datamodel/hyha', headers=header)
    assert response.status_code == 200
    res = response.json
    pprint(res)
    for item in res["standaloneProperties"]:
        if item["iri"] == "hyha:testProp2":
            assert "languageIn" not in item

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "minLength": None,
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 200
    response = client.get('/admin/datamodel/hyha', headers=header)
    assert response.status_code == 200
    res = response.json
    for ele in res["standaloneProperties"]:
        if Iri(ele["iri"]).prefix != "hyha":
            continue
        assert "minLength" not in ele

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "languageIn": [],
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "languageIn": {"add": "gaga", "kappa": "gigi"},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "languageIn": {"add": "gaga", "del": "gigakappa", "kappa": "gigi"},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "languageIn": [None],
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "languageIn": {"add": "kappa"},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "languageIn": {"add": []},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "languageIn": {"add": [None]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "languageIn": {"del": "kappa"},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "languageIn": {"del": []},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "languageIn": {"del": [None]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "languageIn": {"del": "kappa"},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "inSet": [],
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "inSet": [None],
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "inSet": {"add": ["kappa"], "doesnotexist": ["kappa2"]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "inSet": {"add": []},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "inSet": {"add": [None]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "inSet": {"del": []},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "inSet": {"del": [None]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": [],
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": [None],
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"add": ["kappa"], "doesnotexist": ["kappa2"]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"add": []},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"add": [None]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"del": []},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"del": [None]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400


def test_modify_standaloneprop_string(client, token_headers, testfulldatamodelstandalonepropstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp3', json={
        "name": ["kappa@de"],
        "description": ["gigakappa@de"],
        # "inSet": ["gugus"],
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

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp3', json={
        "inSet": None,
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 200
    response = client.get('/admin/datamodel/hyha', headers=header)
    assert response.status_code == 200
    res = response.json
    for ele in res["standaloneProperties"]:
        if Iri(ele["iri"]).prefix != "hyha":
            continue
        assert "inSet" not in ele


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

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": ["Edeutsch kappa@de"],
        "comment": ["english kappa@en"],
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 200
    response = client.get('/admin/datamodel/hyha', headers=header)
    res = response.json
    pprint(res)
    assert res["resources"][0]["label"] == ["Edeutsch kappa@de"]
    assert res["resources"][0]["comment"] == ["english kappa@en"]

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": ["Edeutsch kappa@d"],
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": ["Edeutsch kappa@zz"],
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": ["d"],
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": {"add": ["Ein Test@z"], "del": ["Eine Buchseite@de"]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": {"del": ["Eine Buchseite@d"]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": {"add": ["Ei"]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": {"del": ["Ei"]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": {"add": ["Ein Test@zz"]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": {"del": ["Eine Buchseite@zz"]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": "kappa",
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": None,
    }, headers=header)
    res = response.json
    print(res)
    response = client.get('/admin/datamodel/hyha', headers=header)
    res = response.json
    pprint(res)
    for resource in res["resources"]:
        if resource["iri"] == "hyha:Sheep":
            assert resource["label"] is None

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": [],
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": {},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": {"add": []},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": {"add": [None]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": {"del": []},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": {"del": [None]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400


def test_bad_token_standaloneprop(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.post('/admin/datamodel/hyha/hyha:testProp/mod', headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"

def test_bad_token_resource(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.post('/admin/datamodel/hyha/hyha:testProp2', headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"

def test_cantfind_dm_to_modify(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/doesnotexist/hyha:testProp/mod', headers=header)
    assert response.status_code == 404
    res = response.json
    print(res)

    response = client.post('/admin/datamodel/kappadoesnotexist/property/hyha:testProp2', headers=header)
    assert response.status_code == 404
    res = response.json
    print(res)

def test_cantfind_dm_to_modify_resource(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/doesnotexist/hyha:testProp2', headers=header)
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
    for ele in res["resources"]:
        if Iri(ele["iri"]).prefix != "hyha:sheep":
            continue
        assert ele["maxCount"] == 4
        assert ele["minCount"] == 2
        assert ele["order"] == 42
        for item in ele["hasProperty"]:
            if item["property"]["iri"] == "hyha:testProp2":
                assert item["property"]["name"] == "pappakappa@de"
                assert set(item["property"]["languageIn"]) == set["zu", "en", "it", "de"]
        assert "inSet" not in ele

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

def test_bad_fields_modify_resource(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "Doesnotexist": "kappa1234",
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={

    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": [None],
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": {"gaga": "kappa"},
    }, headers=header)
    res = response.json
    print(res)


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

def test_no_permission_to_modify_attribute_in_has_propresource(client, token_headers, testfulldatamodelresource):
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
    response2 = client.post('/admin/datamodel/hyha/hyha:Sheep/hyha:testProp2', json={
        "property": {
            "name": ["pappakappa@de"],
            "languageIn": {"add": ["zu"], "del": ["fr"]}
        },
        "maxCount": 4,
        "minCount": 2,
        "order": 42
    }, headers=headers)
    res2 = response2.json
    print(res2)
    assert response2.status_code == 404


def test_no_permission_modify_standalone_prop(client, token_headers, testfulldatamodelstandaloneproplangstring):
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

    response2 = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"add": ["NewKappa@en"], "del": ["Kappa@de"]},
    }, headers=headers)
    res2 = response2.json
    print(res2)
    assert response2.status_code == 404

def test_no_permission_modify_resource(client, token_headers, testfulldatamodelresource):
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

    response2 = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
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
    }, headers=headers)
    res2 = response2.json
    print(res2)
    assert response2.status_code == 404
