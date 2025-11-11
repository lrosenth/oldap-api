
def test_instance_read(client, token_headers, testfulldatamodelwithinstances):
    header = token_headers[1]

    response = client.get(f'/data/hyha/{testfulldatamodelwithinstances}', headers=header)
    assert response.status_code == 200

    res = response.json
    assert res['rdf:type'] == ['hyha:Lion']
    assert res['hyha:mammalName'] == ['Cat']
    assert res['hyha:preyScheme'] == ['Deer']
