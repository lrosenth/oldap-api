def test_modify_standaloneprop_langstring(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]


    response = client.post('/admin/datamodel/hyha/hyha:testProp2/mod', json={
        "name": ["kappa@de"],
        "description": ["gigakappa@de"],
        #"languageIn": ["en", "de"],
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
    assert res["standaloneProperties"][0]["name"] == ["kappa@de"]
    assert res["standaloneProperties"][0]["description"] == ["gigakappa@de"]
    assert set(res["standaloneProperties"][0]["languageIn"]) == set(["en", "de", "zu"])
    assert res["standaloneProperties"][0]["uniqueLang"] == True
    assert res["standaloneProperties"][0]["minLength"] == '2'
    assert res["standaloneProperties"][0]["maxLength"] == '51'
    assert res["standaloneProperties"][0]["pattern"] == "kappa"
    assert res["standaloneProperties"][0]["minExclusive"] == '5.6'
    assert res["standaloneProperties"][0]["minInclusive"] == '5.6'
    assert res["standaloneProperties"][0]["maxExclusive"] == '5.6'
    assert res["standaloneProperties"][0]["maxInclusive"] == '5.6'

def test_modify_standaloneprop_string(client, token_headers, testfulldatamodelstandalonepropstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/hyha:testProp3/mod', json={
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

def test_modify_resource(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.post('/admin/datamodel/mod/hyha/hyha:Sheep', json={
        "closed": False,
        "label": ["Ein Test@de"],
        "comment": ["A test comment@en"],
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
    print(res)
    assert res["resources"][0]["closed"] == False
    assert res["resources"][0]["label"] == ["Ein Test@de"]
    assert res["resources"][0]["comment"] == ["A test comment@en"]
