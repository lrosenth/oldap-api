
def test_instance_read(client, token_headers, testfulldatamodelwithinstances):
    header = token_headers[1]

    response = client.get(f'/data/hyha/{testfulldatamodelwithinstances}', headers=header)
    assert response.status_code == 200

    res = response.json
    assert res['rdf:type'] == ['hyha:Lion']
    assert res['hyha:mammalName'] == ['Cat']
    assert res['hyha:preyScheme'] == ['Deer']

def test_instance_read_nonexistent(client, token_headers, testfulldatamodelwithinstances):
    header = token_headers[1]

    response = client.get(f'/data/hyha/hyha:nonexistent', headers=header)
    assert response.status_code == 404

def test_instance_read_wrong_prefix(client, token_headers, testfulldatamodelwithinstances):
    header = token_headers[1]

    response = client.get(f'/data/hyha/test:nonexistent', headers=header)
    assert response.status_code == 404
    res = response.json
    print(res)

def test_instance_read_invalid_iri(client, token_headers, testfulldatamodelwithinstances):
    header = token_headers[1]

    response = client.get(f'/data/hyha/gaga', headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_instance_read_inexisting_project(client, token_headers, testfulldatamodelwithinstances):
    header = token_headers[1]

    response = client.get(f'/data/testit/{testfulldatamodelwithinstances}', headers=header)
    assert response.status_code == 404
    res = response.json
    print(res)


