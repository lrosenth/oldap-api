def test_create_datamodel(client, token_headers):
    header = token_headers[1]

    response = client.put('/admin/datamodel/hyha', json={}, headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)

def test_fill_empty_datamodel_with_standalone_prop(client, token_headers, testemptydatamodel):
    header = token_headers[1]

    response = client.put('/admin/datamodel/hyha/property', json={
        "iri": "hyha:testProp",
        "datatype": "xsd:string",
        "name": ["Test Property@en", "Test Feld@de"],
        "description": ["Test Feld Beschreibung@de"],
        "uniqueLang": True
    }, headers=header)

    res = response.json
    print(res)
