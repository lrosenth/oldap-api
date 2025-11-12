
def test_instance_modify_A(client, token_headers, testfulldatamodeltestinstances):
    header = token_headers[1]

    kirk_iri, uhura_iri, book_iri = testfulldatamodeltestinstances

    response = client.post(f'/data/test/{book_iri}', json={
        'test:title': 'Mastering the NCC-1701-A – an advanced guide'
    }, headers=header)
    assert response.status_code == 200

    response = client.get(f'/data/test/{book_iri}', headers=header)
    assert response.status_code == 200
    res = response.json
    assert set(res['test:title']) == {'Mastering the NCC-1701-A – an advanced guide'}

def test_instance_modify_B(client, token_headers, testfulldatamodeltestinstances):
    header = token_headers[1]

    kirk_iri, uhura_iri, book_iri = testfulldatamodeltestinstances

    response = client.post(f'/data/test/{kirk_iri}', json={
        'schema:givenName': {'add': ['T.'], 'del': ['Tiberius']}
    }, headers=header)
    assert response.status_code == 200

    response = client.get(f'/data/test/{kirk_iri}', headers=header)
    assert response.status_code == 200
    res = response.json
    assert set(res['schema:givenName']) == {'James', 'T.'}

def test_instance_modify_C(client, token_headers, testfulldatamodeltestinstances):
    header = token_headers[1]

    kirk_iri, uhura_iri, book_iri = testfulldatamodeltestinstances

    response = client.put('/data/test/Person', json={
        'schema:familyName': 'Scott',
        'schema:givenName': 'Montgomery',
        'oldap:grantsPermission': 'oldap:GenericView'
    }, headers=header)
    res = response.json
    scotty_iri = res['iri']

    response = client.post(f'/data/test/{book_iri}', json={
        'test:title': 'Mastering the NCC-1701-A – an advanced guide',
        'test:author': {'add': [scotty_iri], 'del': [uhura_iri]}
    }, headers=header)
    assert response.status_code == 200

    response = client.get(f'/data/test/{book_iri}', headers=header)
    assert response.status_code == 200
    res = response.json
    assert set(res['test:title']) == {'Mastering the NCC-1701-A – an advanced guide'}
    assert set(res['test:author']) == {kirk_iri, scotty_iri}

