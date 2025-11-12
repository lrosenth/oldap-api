
def test_create_instance(client, token_headers, testfulldatamodelresourcesimple):
    header = token_headers[1]

    response = client.put('/data/hyha/SimpleSheep', json={
        'iri': 'MySimpleSheep',
        'testProp3': "Waseliwas",
        'grantsPermission': 'oldap:GenericView'
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    assert 'iri' in res
    assert 'message' in res

def test_create_instance_URN(client, token_headers, testfulldatamodelresourcesimple):
    header = token_headers[1]

    response = client.put('/data/hyha/SimpleSheep', json={
        'testProp3': "Waseliwas mit URN",
        'grantsPermission': 'oldap:GenericView'
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    assert 'iri' in res
    assert 'message' in res

def test_create_instance_URN(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.put('/data/hyha/Sheep', json={
        'testProp2': ["a test@en", "ein Test@de", "un teste@fr"],
        'grantsPermission': 'oldap:GenericView'
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    assert 'iri' in res
    assert 'message' in res

def test_create_instance_props(client, token_headers, testfulldatamodelresourcedatatypes):
    header = token_headers[1]

    response = client.put('/data/hyha/Book', json={
        'title': ["Die Geschichte der ASD@de", "L'Histoire de l'ASD@fr"],
        'numPages': 123,
        'publishingDate': "2026-01-01",
        'grantsPermission': 'oldap:GenericView'
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    assert 'iri' in res
    assert 'message' in res

def test_create_instance_with_superclass(client, token_headers, testfulldatamodelresourcesuperclasses):
    header = token_headers[1]

    response = client.put('/data/hyha/Lion', json={
        'mammalName': 'Cat',
        'preyScheme': 'Cows',
        'grantsPermission': 'oldap:GenericView'
    }, headers=header)
    assert response.status_code == 200

