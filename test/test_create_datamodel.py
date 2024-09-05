def test_create_empty_datamodel(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/datamodel/hyha', json={}, headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)


def test_fill_empty_datamodel_with_standalone_prop(client, token_headers, testhalffulldatamodelstandaloneprop):
    header = token_headers[1]

    response = client.put('/admin/datamodel/hyha/property', json={
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
    }, headers=header)

    res = response.json
    print(res)


def test_fill_empty_datamodel_with_resource(client, token_headers, testemptydatamodel):
    header = token_headers[1]

    response = client.put('/admin/datamodel/hyha/resource', json={
        "iri": "hyha:Sheep",
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
    my_list = [item.strip() for item in res["resources"][0]["hasProperty"][0]["property"]["in"].strip("()").split(",")]
    assert sorted(my_list) == sorted(["Kappa", "Gaga", "gugus"])
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
