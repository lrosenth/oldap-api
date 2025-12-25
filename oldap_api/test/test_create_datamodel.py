from pprint import pprint

from oldaplib.src.xsd.iri import Iri


def test_create_empty_datamodel(client, token_headers, testproject):
    header = token_headers[1]

    response = client.put('/admin/datamodel/testproject', headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)

def test_fill_empty_datamodel_with_extonto(client, token_headers, testemptydatamodel):
    header = token_headers[1]

    response = client.put('/admin/datamodel/hyha/extonto/crm', json={
        'namespaceIri': 'http://www.cidoc-crm.org/cidoc-crm/',
        'label': 'CIDOC CRM'
    }, headers=header)
    assert response.status_code == 200

    response = client.get('/admin/datamodel/hyha', headers=header)
    res = response.json
    assert response.status_code == 200
    assert res['externalOntologies'][0]['namespaceIri'] == "http://www.cidoc-crm.org/cidoc-crm/"


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
        "pattern": r"^[\w\.-]+@[a-zA-Z\d-]+(\.[a-zA-Z\d-]+)*\.[a-zA-Z]{2,}$",
        "minExclusive": 5.5,
        "minInclusive": 5.5,
        "maxExclusive": 5.5,
        "maxInclusive": 5.5,
        "lessThan": "hyha:testProp",
        "lessThanOrEquals": "hyha:testProp"
    }, headers=header)

    assert response.status_code == 200

    response = client.get('/admin/datamodel/hyha', headers=header)
    res = response.json

    assert response.status_code == 200

    for ele in res["standaloneProperties"]:
        if Iri(ele["iri"]).prefix != "hyha":
            continue

        assert ele["iri"] == "hyha:testProp2"
        assert ele["subPropertyOf"] == "hyha:testProp"
        assert ele["datatype"] == "rdf:langString"
        assert set(ele["name"]) == set(["Test Property@en", "Test Feld@de"])
        assert ele["description"] == ["Test Feld Beschreibung@de"]
        assert sorted(ele["languageIn"]) == sorted(["en", "fr", "it", "de"])
        assert ele["uniqueLang"] == True
        assert sorted(ele["inSet"]) == sorted(["Kappa", "Gaga", "gugus"])
        assert ele["minLength"] == 1
        assert ele["maxLength"] == 50
        assert ele["pattern"] == r"^[\w\.-]+@[a-zA-Z\d-]+(\.[a-zA-Z\d-]+)*\.[a-zA-Z]{2,}$"
        assert ele["minExclusive"] == 5.5
        assert ele["minInclusive"] == 5.5
        assert ele["maxExclusive"] == 5.5
        assert ele["maxInclusive"] == 5.5
        assert ele["lessThan"] == "hyha:testProp"
        assert ele["lessThanOrEquals"] == "hyha:testProp"

def test_fill_empty_datamodel_with_prop_class_valid(client, token_headers, testemptydatamodel):
    header = token_headers[1]

    response = client.put('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "type": ["StatementProperty"],
        "subPropertyOf": "hyha:testProp",
        "class": "hyha:TestKappa",
        "name": ["Test Property@en", "Test Feld@de"],
        "description": ["Test Feld Beschreibung@de"],
        "inverseOf": "hyha:testProp_XYZ",
        "equivalentProperty": "hyha:testProp",
    }, headers=header)
    assert response.status_code == 200

    response = client.get('/admin/datamodel/hyha', headers=header)
    assert response.status_code == 200
    res = response.json

    for ele in res["standaloneProperties"]:
        if Iri(ele["iri"]) != "hyha:testProp2":
            continue
        assert ele["iri"] == "hyha:testProp2"
        assert ele["type"] == ["StatementProperty"]
        assert set(ele["name"]) == {"Test Property@en", "Test Feld@de"}
        assert ele['subPropertyOf'] == 'hyha:testProp'
        assert ele['toClass'] == 'hyha:TestKappa'
        assert ele['inverseOf'] == 'hyha:testProp_XYZ'
        assert ele['equivalentProperty'] == 'hyha:testProp'

def test_fill_empty_datamodel_with_prop_class_invalid_A(client, token_headers, testemptydatamodel):
    header = token_headers[1]

    response = client.put('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "subPropertyOf": "hyha:testProp",
        "class": 1234,
        "name": ["Test Property@en", "Test Feld@de"],
        "description": ["Test Feld Beschreibung@de"],
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    assert res['message'] == 'Invalid value for QName "1234" (type: int)'


def test_fill_empty_datamodel_with_prop_class_invalid_B(client, token_headers, testemptydatamodel):
    header = token_headers[1]

    response = client.put('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "subPropertyOf": "hyha:testProp",
        "class": "rdfx:langString",
        "name": ["Test Property@en", "Test Feld@de"],
        "description": ["Test Feld Beschreibung@de"],
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    assert res['message'] == 'The prefix "rdfx" is not known in the context.'

def test_fill_empty_datamodel_with_prop_class_invalid_C(client, token_headers, testemptydatamodel):
    header = token_headers[1]

    response = client.put('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "subPropertyOf": "hyha:testProp",
        "class": "rdf:langString",
        "name": ["Test Property@en", "Test Feld@de"],
        "description": ["Test Feld Beschreibung@de"],
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    assert res['message'] == 'A class that has a prefix of "rdf", "rdfs" and "xml" is not allowed.'

def test_fill_empty_datamodel_with_prop_class_invalid_D(client, token_headers, testemptydatamodel):
    header = token_headers[1]

    response = client.put('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "subPropertyOf": "hyha:testProp",
        "class": "xml:Date",
        "name": ["Test Property@en", "Test Feld@de"],
        "description": ["Test Feld Beschreibung@de"],
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    assert res['message'] == 'A class that has a prefix of "rdf", "rdfs" and "xml" is not allowed.'

def test_could_not_find_project_to_fill_standaloneprop(client, token_headers, testemptydatamodel):
    header = token_headers[1]

    response = client.put('/admin/datamodel/doesnotexist/property/hyha:testProp2', json={
        "subPropertyOf": "hyha:testProp",
        "datatype": "rdf:langString",
        "name": ["Test Property@en", "Test Feld@de"],
        "description": ["Test Feld Beschreibung@de"],
    }, headers=header)

    assert response.status_code == 404
    res = response.json
    print(res)
    assert res['message'] == 'Project with IRI/shortname "doesnotexist" not found.'

def test_standaloneprop_already_exists(client, token_headers, testemptydatamodel):
    header = token_headers[1]

    response = client.put('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "subPropertyOf": "hyha:testProp",
        "datatype": "rdf:langString",
        "name": ["Test Property@en", "Test Feld@de"],
        "description": ["Test Feld Beschreibung@de"],
    }, headers=header)

    assert response.status_code == 200
    res = response.json

    response = client.put('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "subPropertyOf": "hyha:testProp",
        "datatype": "rdf:langString",
        "name": ["Test Property@en", "Test Feld@de"],
        "description": ["Test Feld Beschreibung@de"],
    }, headers=header)
    assert response.status_code == 409
    res = response.json
    assert res['message'] == 'The property class "hyha:testProp2" already exists. It cannot be replaced. Update/delete it.'

def test_fill_empty_datamodel_with_standalone_prop_class(client, token_headers, testemptydatamodel):
    header = token_headers[1]

    response = client.put('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "subPropertyOf": "hyha:testProp",
        "class": "hyha:kappa",
        "name": ["Test Property@en", "Test Feld@de"],
        "description": ["Test Feld Beschreibung@de"],
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 200


    response = client.put('/admin/datamodel/hyha/property/hyha:testProp4', json={
        "subPropertyOf": "hyha:testProp",
        "class": "hyha:kappa",
        # "class": 1234,
        "name": ["Test Property@en", "Test Feld@de"],
        "description": ["kappa@de"],
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 200


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
                    "pattern": r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$",
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
    assert set(res["resources"][0]["label"]) == set(["Eine Buchseite@de", "A page of a book@en"])
    assert set(res["resources"][0]["comment"]) == set(["Eine Buchseite@de", "A page of a book@en"])
    assert res["resources"][0]["closed"] == True
    assert res["resources"][0]["hasProperty"][0]["property"]["iri"] == "hyha:testProp2"
    assert res["resources"][0]["hasProperty"][0]["property"]["subPropertyOf"] == "hyha:testProp"
    assert res["resources"][0]["hasProperty"][0]["property"]["datatype"] == "rdf:langString"
    assert set(res["resources"][0]["hasProperty"][0]["property"]["name"]) == set(["Test Property@en", "Test Feld@de"])
    assert res["resources"][0]["hasProperty"][0]["property"]["description"] == ["Test Feld Beschreibung@de"]
    assert sorted(res["resources"][0]["hasProperty"][0]["property"]["languageIn"]) == sorted(["en", "fr", "it", "de"])
    assert res["resources"][0]["hasProperty"][0]["property"]["uniqueLang"] == True
    assert sorted(res["resources"][0]["hasProperty"][0]["property"]["inSet"]) == sorted(["Kappa", "Gaga", "gugus"])
    assert res["resources"][0]["hasProperty"][0]["property"]["minLength"] == 1
    assert res["resources"][0]["hasProperty"][0]["property"]["maxLength"] == 50
    assert res["resources"][0]["hasProperty"][0]["property"]["pattern"] == r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$"
    assert res["resources"][0]["hasProperty"][0]["property"]["minExclusive"] == 5.5
    assert res["resources"][0]["hasProperty"][0]["property"]["minInclusive"] == 5.5
    assert res["resources"][0]["hasProperty"][0]["property"]["maxExclusive"] == 5.5
    assert res["resources"][0]["hasProperty"][0]["property"]["maxInclusive"] == 5.5
    assert res["resources"][0]["hasProperty"][0]["property"]["lessThan"] == 'hyha:testProp'
    assert res["resources"][0]["hasProperty"][0]["property"]["lessThanOrEquals"] == "hyha:testProp"
    assert res["resources"][0]["hasProperty"][0]["maxCount"] == 3
    assert res["resources"][0]["hasProperty"][0]["minCount"] == 1
    assert res["resources"][0]["hasProperty"][0]["order"] == 1.0

def test_resource_already_exists(client, token_headers, testemptydatamodel):
    header = token_headers[1]

    response = client.put('/admin/datamodel/hyha/hyha:Sheep', json={
        "comment": [
            "Eine Buchseite@de",
            "A page of a book@en"
        ]}, headers=header)
    res = response.json
    assert response.status_code == 200

    response = client.put('/admin/datamodel/hyha/hyha:Sheep', json={
        "comment": [
            "Eine Buchseite@de",
            "A page of a book@en"
        ]}, headers=header)
    res = response.json
    assert response.status_code == 409
    assert res['message'] == 'The resource class "hyha:Sheep" already exists. It cannot be replaced. Update/delete it.'

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
        "pattern": r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$",
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

def test_prop_in_resource_already_exists(client, token_headers, testfulldatamodelresource):
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
        "pattern": r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$",
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
        "pattern": r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$",
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
    assert response.status_code == 409

def test_create_empty_prop_in_resource(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.put('/admin/datamodel/hyha/hyha:Sheep/hyha:newprop', json={}, headers=header)
    res = response.json
    assert response.status_code == 200

    response = client.get('/admin/datamodel/hyha', headers=header)
    assert response.status_code == 200
    res = response.json

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
                    "pattern": r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$",
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
        "doesnotexist": "kappa:kappanial",
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
                    "pattern": r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$",
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
                    "pattern": r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$",
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

    response = client.put('/admin/datamodel/hyha/property/test', json={}, headers=header)
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

    response = client.put('/admin/datamodel/hyha/hyha:Sheep/hyha:newprop', json={
        "doesnotexist": "kappa",
        "subPropertyOf": "hyha:testProp",
        "datatype": "rdf:langString",
        "name": ["New Test Property@en", "New Test Feld@de"],
        "description": ["New Test Feld Beschreibung@de"],
        "languageIn": ["en", "fr", "it", "de"],
        "uniqueLang": True,
        "inSet": ["Kappa", "Gaga", "gugus"],
        "minLength": 1,
        "maxLength": 50,
        "pattern": r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$",
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
    assert response.status_code == 400
    print(res)

    response = client.put('/admin/datamodel/hyha/hyha:Sheep/hyha:newprop', json={
        "doesnotexist": "kappa",
        "subPropertyOf": "hyha:testProp",
        "datatype": "rdf:langString",
        "name": ["New Test Property@en", "New Test Feld@de"],
        "description": ["New Test Feld Beschreibung@de"],
        "languageIn": ["en", "fr", "it", "de"],
        "uniqueLang": True,
        "inSet": ["Kappa", "Gaga", "gugus"],
        "minLength": 1,
        "maxLength": 50,
        "pattern": r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$",
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
    assert response.status_code == 400
    print(res)


def test_not_find_superclass_when_creating_resource(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.put('/admin/datamodel/hyha/hyha:Sheep', json={
        "superclass": 1234,
    }, headers=header)
    res = response.json
    assert response.status_code == 400
    print(res)

def test_dm_to_add_resource_to_not_found(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/datamodel/doesnotexist/resource', json={
        "comment": "kappa",
    }, headers=header)

    res = response.json
    print(res)
    assert response.status_code == 404

def test_dm_to_add_property_to_not_found(client, token_headers):
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
        "pattern": r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$",
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
    assert response.status_code == 404

