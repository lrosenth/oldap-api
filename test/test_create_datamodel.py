def test_create_datamodel(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/datamodel/hyha', json={}, headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)

def test_fill_empty_datamodel_with_standalone_prop(client, token_headers, testfulldatamodel):
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
        # "pattern": "^[\w\.-]+@[a-zA-Z\d-]+(\.[a-zA-Z\d-]+)*\.[a-zA-Z]{2,}$",
        "minExclusive": 5.5,
        "minInclusive": 5.5,
        "maxExclusive": 5.5,
        "maxInclusive": 5.5,
        "lessThan": "hyha:testProp",
        "lessThanOrEquals": "hyha:testProp"
    }, headers=header)

    res = response.json
    print(res)

def test_read_datamodel(client, token_headers, testfulldatamodel):
    header = token_headers[1]

    response = client.get('/admin/datamodel/hyha', headers=header)

    res = response.json
    print(res)
