

def test_create_instance(client, token_headers, testfulldatamodelresourcesimple):
    header = token_headers[1]

    response = client.put('/data/hyha/SimpleSheep', json={
        'iri': 'MySimpleSheep',
        'hyha:testProp3': "Waseliwas",
        'oldap:grantsPermission': 'oldap:GenericView'
    }, headers=header)
    print(response.text)