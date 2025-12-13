from pprint import pprint


def test_create_instance(client, token_headers, testfulldatamodelresourcesimple):
    header = token_headers[1]

    response = client.put('/data/hyha/SimpleSheep', json={
        'iri': 'MySimpleSheep',
        'hyha:testProp3': "Waseliwas",
        'oldap:grantsPermission': 'oldap:GenericView'
    }, headers=header)
    assert response.status_code == 200
    assert response.json['iri'] == 'hyha:MySimpleSheep'

    response = client.get('/data/hyha/hyha:MySimpleSheep', headers=header)
    assert response.status_code == 200
    res = response.json
    assert res['hyha:testProp3'] == ['Waseliwas']

def test_create_instance2(client, token_headers, testfulldatamodelresourcesimple):
    header = token_headers[1]

    response = client.put('/data/hyha/shared:MediaObject', json={
        'shared:originalName': 'orig-image-file.tif',
        'shared:originalMimeType': 'image/tiff',
        'shared:serverUrl': 'http://iiif.oldap.org/iiif/3/',
        'shared:imageId': 'a67dcf8d.jp2',
        'shared:protocol': 'iiif',
        'shared:path': 'gaga/gugus',
        'oldap:grantsPermission': ['oldap:GenericView', 'britnet:Editor']
    }, headers=header)
    assert response.status_code == 200
    print(response.json)
