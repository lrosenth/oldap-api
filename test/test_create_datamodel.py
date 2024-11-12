from pprint import pprint


def test_create_empty_datamodel(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/datamodel/hyha', json={}, headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)


def test_fill_empty_datamodel_with_standalone_prop(client, token_headers, testemptydatamodel):
    header = token_headers[1]

    response = client.put('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "subPropertyOf": "hyha:testProp",
        "datatype": "rdf:langString",
        "name": ["Test Property@en", "Test Feld@de"],
        "description": ["Test Feld Beschreibung@de"],
        "languageIn": ["en", "fr", "it", "de"],
        "uniqueLang": True,
        "inSet": ["Kappa", "Gaga", "gugus"],
        "minLength": 1,
        "maxLength": 50,
        "pattern": "^[\w\.-]+@[a-zA-Z\d-]+(\.[a-zA-Z\d-]+)*\.[a-zA-Z]{2,}$",
        "minExclusive": 5.5,
        "minInclusive": 5.5,
        "maxExclusive": 5.5,
        "maxInclusive": 5.5,
        "lessThan": "hyha:testProp",
        "lessThanOrEquals": "hyha:testProp"
    }, headers=header)

    res = response.json
    assert response.status_code == 200
    print(res)

    response = client.get('/admin/datamodel/hyha', headers=header)
    res = response.json
    print(res)

    assert response.status_code == 200
    assert res["standaloneProperties"][0]["iri"] == "hyha:testProp2"
    assert res["standaloneProperties"][0]["subPropertyOf"] == "hyha:testProp"
    assert res["standaloneProperties"][0]["datatype"] == "rdf:langString"
    assert res["standaloneProperties"][0]["name"] == ["Test Property@en", "Test Feld@de"]
    assert res["standaloneProperties"][0]["description"] == ["Test Feld Beschreibung@de"]
    assert sorted(res["standaloneProperties"][0]["languageIn"]) == sorted(["en", "fr", "it", "de"])
    assert res["standaloneProperties"][0]["uniqueLang"] == True
    assert sorted(res["standaloneProperties"][0]["inSet"]) == sorted(["Kappa", "Gaga", "gugus"])
    assert res["standaloneProperties"][0]["minLength"] == '1'
    assert res["standaloneProperties"][0]["maxLength"] == '50'
    assert res["standaloneProperties"][0]["pattern"] == "^[\w\.-]+@[a-zA-Z\d-]+(\.[a-zA-Z\d-]+)*\.[a-zA-Z]{2,}$"
    assert res["standaloneProperties"][0]["minExclusive"] == '5.5'
    assert res["standaloneProperties"][0]["minInclusive"] == '5.5'
    assert res["standaloneProperties"][0]["maxExclusive"] == '5.5'
    assert res["standaloneProperties"][0]["maxInclusive"] == '5.5'
    assert res["standaloneProperties"][0]["lessThan"] == "hyha:testProp"
    assert res["standaloneProperties"][0]["lessThanOrEquals"] == "hyha:testProp"


def test_fill_empty_datamodel_with_resource(client, token_headers, testemptydatamodel):
    header = token_headers[1]

    response = client.put('/admin/datamodel/hyha/hyha:Sheep', json={
        # "superclass": "hyha:Animal",
        "label": [
            "Eine Buchseite@de",
            "A page of a book@en"
        ],
        "comment": [
            "Eine Buchseite@de",
            "A page of a book@en"
        ],
        "closed": True,
        "hasProperty": [
            {
                "property": {
                    "iri": "hyha:testProp2",
                    "subPropertyOf": "hyha:testProp",
                    "datatype": "rdf:langString",
                    "name": ["Test Property@en", "Test Feld@de"],
                    "description": ["Test Feld Beschreibung@de"],
                    "languageIn": ["en", "fr", "it", "de"],
                    "uniqueLang": True,
                    "inSet": ["Kappa", "Gaga", "gugus"],
                    "minLength": 1,
                    "maxLength": 50,
                    "pattern": "^[\w\.-]+@[a-zA-Z\d-]+(\.[a-zA-Z\d-]+)*\.[a-zA-Z]{2,}$",
                    "minExclusive": 5.5,
                    "minInclusive": 5.5,
                    "maxExclusive": 5.5,
                    "maxInclusive": 5.5,
                    "lessThan": "hyha:testProp",
                    "lessThanOrEquals": "hyha:testProp"
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
    res = response.json
    print(res)

    assert response.status_code == 200
    assert res["resources"][0]["iri"] == "hyha:Sheep"
    assert res["resources"][0]["label"] == ["Eine Buchseite@de", "A page of a book@en"]
    assert res["resources"][0]["comment"] == ["Eine Buchseite@de", "A page of a book@en"]
    assert res["resources"][0]["closed"] == True
    assert res["resources"][0]["hasProperty"][0]["property"]["iri"] == "hyha:testProp2"
    assert res["resources"][0]["hasProperty"][0]["property"]["subPropertyOf"] == "hyha:testProp"
    assert res["resources"][0]["hasProperty"][0]["property"]["datatype"] == "rdf:langString"
    assert res["resources"][0]["hasProperty"][0]["property"]["name"] == ["Test Property@en", "Test Feld@de"]
    assert res["resources"][0]["hasProperty"][0]["property"]["description"] == ["Test Feld Beschreibung@de"]
    assert sorted(res["resources"][0]["hasProperty"][0]["property"]["languageIn"]) == sorted(["en", "fr", "it", "de"])
    assert res["resources"][0]["hasProperty"][0]["property"]["uniqueLang"] == True
    assert sorted(res["resources"][0]["hasProperty"][0]["property"]["inSet"]) == sorted(["Kappa", "Gaga", "gugus"])
    assert res["resources"][0]["hasProperty"][0]["property"]["minLength"] == '1'
    assert res["resources"][0]["hasProperty"][0]["property"]["maxLength"] == '50'
    assert res["resources"][0]["hasProperty"][0]["property"]["pattern"] == "^[\w\.-]+@[a-zA-Z\d-]+(\.[a-zA-Z\d-]+)*\.[a-zA-Z]{2,}$"
    assert res["resources"][0]["hasProperty"][0]["property"]["minExclusive"] == '5.5'
    assert res["resources"][0]["hasProperty"][0]["property"]["minInclusive"] == '5.5'
    assert res["resources"][0]["hasProperty"][0]["property"]["maxExclusive"] == '5.5'
    assert res["resources"][0]["hasProperty"][0]["property"]["maxInclusive"] == '5.5'
    assert res["resources"][0]["hasProperty"][0]["property"]["lessThan"] == 'hyha:testProp'
    assert res["resources"][0]["hasProperty"][0]["property"]["lessThanOrEquals"] == "hyha:testProp"
    assert res["resources"][0]["hasProperty"][0]["maxCount"] == '3'
    assert res["resources"][0]["hasProperty"][0]["minCount"] == '1'
    assert res["resources"][0]["hasProperty"][0]["order"] == '1.0'


def test_bad_fill_empty_datamodel_with_resource(client, token_headers, testemptydatamodel):
    header = token_headers[1]

    response = client.put('/admin/datamodel/hyha/hyha:Sheep', json={
        # "superclass": "hyha:Animal",
        "label": [
            "Eine Buchseite@de",
            "A page of a book@en"
        ],
        "comment": [
            "Eine Buchseite@de",
            "A page of a book@en"
        ],
        "closed": True,
        "hasProperty": [
            {
                "RandomStuff": "abcdefg",
                "property": {
                    "iri": "hyha:testProp2",
                    "subPropertyOf": "hyha:testProp",
                    "datatype": "rdf:langString",
                    "name": ["Test Property@en", "Test Feld@de"],
                    "description": ["Test Feld Beschreibung@de"],
                    "languageIn": ["en", "fr", "it", "de"],
                    "uniqueLang": True,
                    "in": ["Kappa", "Gaga", "gugus"],
                    "minLength": 1,
                    "maxLength": 50,
                    "pattern": "^[\w\.-]+@[a-zA-Z\d-]+(\.[a-zA-Z\d-]+)*\.[a-zA-Z]{2,}$",
                    "minExclusive": 5.5,
                    "minInclusive": 5.5,
                    "maxExclusive": 5.5,
                    "maxInclusive": 5.5,
                    "lessThan": "hyha:testProp",
                    "lessThanOrEquals": "hyha:testProp"
                },
                "maxCount": 3,
                "minCount": 1,
                "order": 1
            }
        ]
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.put('/admin/datamodel/hyha/hyha:Sheep', json={
        "hasProperty": [
            {
                "maxCount": 3,
                "minCount": 1,
                "order": 1
            }
        ]
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.put('/admin/datamodel/hyha/hyha:Sheep', json={
        "hasProperty": [
            {
                "doesnotexist": "kappa",
                "maxCount": 3,
                "minCount": 1,
                "order": 1
            }
        ]
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.put('/admin/datamodel/hyha/hyha:Sheep', json={
        "hasProperty": [
            {
                "property": {
                    "doesnotexist": "kappa",
                    "iri": "hyha:testProp2",
                    "subPropertyOf": "hyha:testProp",
                    "datatype": "rdf:langString",
                    "name": ["Test Property@en", "Test Feld@de"],
                    "description": ["Test Feld Beschreibung@de"],
                    "languageIn": ["en", "fr", "it", "de"],
                    "uniqueLang": True,
                    "minLength": 1,
                    "maxLength": 50,
                    "pattern": "^[\w\.-]+@[a-zA-Z\d-]+(\.[a-zA-Z\d-]+)*\.[a-zA-Z]{2,}$",
                    "minExclusive": 5.5,
                    "minInclusive": 5.5,
                    "maxExclusive": 5.5,
                    "maxInclusive": 5.5,
                    "lessThan": "hyha:testProp",
                    "lessThanOrEquals": "hyha:testProp"
                },
                "maxCount": 3,
                "minCount": 1,
                "order": 1
            }
        ]
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400


    response = client.put('/admin/datamodel/hyha/hyha:Sheep', json={
        "hasProperty": [
            {
                "property": {
                    "doesnotexist": "kappa",
                },
                "maxCount": 3,
                "minCount": 1,
                "order": 1
            }
        ]
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400


def test_bad_token(client, token_headers):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.put('/admin/datamodel/hyha', json={}, headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"

    response = client.put('/admin/datamodel/hyha/property', json={}, headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"

    response = client.put('/admin/datamodel/hyha/resource', json={}, headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"

    response = client.put('/admin/datamodel/hyha/resource/test', json={}, headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"



def test_bad_json_fields_in_create_property(client, token_headers, testemptydatamodel):
    header = token_headers[1]

    response = client.put('/admin/datamodel/hyha/property/doesnotexist', json={
        "lessThanOrEquals": "hyha:testProp"
    }, headers=header)
    res = response.json
    assert response.status_code == 400
    print(res)

    response = client.put('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "subPropertyOf": "hyha:testProp",
        "name": ["Test Property@en", "Test Feld@de"],
        "description": ["Test Feld Beschreibung@de"],
        "languageIn": ["en", "fr", "it", "de"],
        "uniqueLang": True,
        "inSet": ["Kappa", "Gaga", "gugus"],

    }, headers=header)
    res = response.json
    assert response.status_code == 400
    print(res)

    response = client.put('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "subPropertyOf": "hyha:testProp",
        "datatype": "rdf:langString",
        "class": "aToclass",
        "name": ["Test Property@en", "Test Feld@de"],
        "description": ["Test Feld Beschreibung@de"],
        "languageIn": ["en", "fr", "it", "de"],
        "uniqueLang": True,
        "inSet": ["Kappa", "Gaga", "gugus"],

    }, headers=header)
    res = response.json
    assert response.status_code == 400
    print(res)

    response = client.put('/admin/datamodel/hyha/property/hyha:Sheep', json={
        # "superclass": "hyha:Animal",
        "Thisdoesnotexist": "kappa kappa",
    }, headers=header)
    res = response.json
    assert response.status_code == 400
    print(res)

    response = client.put('/admin/datamodel/hyha/property/hyha:Sheep', json={
        "hasProperty": [
            {
                "maxCount": 3,
                "minCount": 1,
                "order": 1
            }
        ]
    }, headers=header)
    res = response.json
    assert response.status_code == 400
    print(res)

    response = client.put('/admin/datamodel/hyha/property/hyha:Sheep', json={
        "hasProperty": [
            {
                "property": {
                "doesnotexist": "kappa"
            },
                "maxCount": 3,
                "minCount": 1,
                "order": 1
            }
        ]
    }, headers=header)
    res = response.json
    assert response.status_code == 400
    print(res)

def test_not_find_superclass_when_creating_resource(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.put('/admin/datamodel/hyha/hyha:Sheep', json={
        "superclass": 1234,
    }, headers=header)
    res = response.json
    assert response.status_code == 403
    print(res)

def test_dm_to_add_resource_to_not_found(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/datamodel/doesnotexist/resource', json={
        "comment": "kappa",
    }, headers=header)

    res = response.json
    print(res)
    assert response.status_code == 400

def test_create_prop_in_resource(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.put('/admin/datamodel/hyha/hyha:Sheep/hyha:newprop', json={
        "subPropertyOf": "hyha:testProp",
        "datatype": "rdf:langString",
        "name": ["New Test Property@en", "New Test Feld@de"],
        "description": ["New Test Feld Beschreibung@de"],
        "languageIn": ["en", "fr", "it", "de"],
        "uniqueLang": True,
        "inSet": ["Kappa", "Gaga", "gugus"],
        "minLength": 1,
        "maxLength": 50,
        "pattern": "^[\w\.-]+@[a-zA-Z\d-]+(\.[a-zA-Z\d-]+)*\.[a-zA-Z]{2,}$",
        "minExclusive": 5.5,
        "minInclusive": 5.5,
        "maxExclusive": 5.5,
        "maxInclusive": 5.5,
        "lessThan": "hyha:testProp",
        "lessThanOrEquals": "hyha:testProp",
        "minCount": 1,
        "maxCount": 2,
        "order": 2
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 200

    response = client.get('/admin/datamodel/hyha', headers=header)
    res = response.json
    pprint(res)
