

def test_instance_delete_A(client, token_headers, testfulldatamodeltestinstances):
    header = token_headers[1]

    kirk_iri, uhura_iri, book_iri = testfulldatamodeltestinstances

    response = client.delete(f'/data/test/{book_iri}', headers=header)
    assert response.status_code == 200

    response = client.get(f'/data/test/{book_iri}', headers=header)
    assert response.status_code == 404


def test_instance_delete_B(client, token_headers, testfulldatamodeltestinstances):
    header = token_headers[1]

    kirk_iri, uhura_iri, book_iri = testfulldatamodeltestinstances

    response = client.delete(f'/data/test/{kirk_iri}', headers=header)
    assert response.status_code == 409  # in use
