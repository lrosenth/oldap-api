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

    response = client.get('/data/hyha/get/hyha:MySimpleSheep', headers=header)
    assert response.status_code == 200
    res = response.json
    assert res['hyha:testProp3'] == ['Waseliwas']
