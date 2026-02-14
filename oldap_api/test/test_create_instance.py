
def test_create_instance(client, token_headers, testfulldatamodelresourcesimple):
    header = token_headers[1]

    response = client.put('/data/hyha/SimpleSheep', json={
        'iri': 'MySimpleSheep',
        'testProp3': "Waseliwas",
        'attachedToRole': {'oldap:Unknown': 'DATA_VIEW'}
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    assert 'iri' in res
    assert 'message' in res

def test_create_instance_URN(client, token_headers, testfulldatamodelresourcesimple):
    header = token_headers[1]

    response = client.put('/data/hyha/SimpleSheep', json={
        'testProp3': "Waseliwas mit URN",
        'attachedToRole': {'oldap:Unknown': 'DATA_VIEW'}
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    assert 'iri' in res
    assert 'message' in res

def test_create_instance_URN(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.put('/data/hyha/Sheep', json={
        'testProp2': ["a test@en", "ein Test@de", "un teste@fr"],
        'attachedToRole': {'oldap:Unknown': 'DATA_VIEW'}
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
        'attachedToRole': {'oldap:Unknown': 'DATA_VIEW'}
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
        'attachedToRole': {'oldap:Unknown': 'DATA_VIEW'}
    }, headers=header)
    assert response.status_code == 200

def test_create_instance_mediaobject(client, token_headers, testemptydatamodel):
    header = token_headers[1]

    response = client.put('/data/hyha/shared:MediaObject', json={
        'dcterms:type': 'dcmitype:StillImage',
        'originalName': 'Cat.tif',
        'originalMimeType': 'image/tiff',
        'serverUrl': 'http://iiif.oldap.org/iiif/3/',
        'imageId': 'cat.tif',
        'protocol': 'iiif',
        'derivativeName': 'iiif.tif',
        'path': 'xxx',
        'attachedToRole': {'oldap:Unknown': 'DATA_VIEW'}
    }, headers=header)
    print(response.json)
    assert response.status_code == 200
