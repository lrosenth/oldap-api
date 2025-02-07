
def test_search_user_by_userId(client, token_headers, testproject):
    header = token_headers[1]

    response = client.get('/admin/user/search', query_string={
        "userId": "rosenth"
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    assert res == ['https://orcid.org/0000-0003-1681-4036']

def test_search_user_by_familyName(client, token_headers, testproject):
    header = token_headers[1]

    response = client.get('/admin/user/search', query_string={
        "familyName": "Rosenthaler"
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    assert res == ['https://orcid.org/0000-0003-1681-4036']

def test_search_user_by_givenName(client, token_headers, testproject):
    header = token_headers[1]

    response = client.get('/admin/user/search', query_string={
        "givenName": "Lukas"
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    assert res == ['https://orcid.org/0000-0003-1681-4036']

def test_search_user_by_projectId(client, token_headers, testproject):
    header = token_headers[1]

    response = client.get('/admin/user/search', query_string={
        "inProject": "oldap:HyperHamlet"
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    assert set(res) == {'https://orcid.org/0000-0003-1681-4036',
                        'https://orcid.org/0000-0003-1485-4923',
                        'https://orcid.org/0000-0001-9277-3921'}

def test_bad_token(client, token_headers):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.get('/admin/user/search', query_string={
        "userId": "rosenth"
    }, headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"

def test_no_label_or_comment(client, token_headers):
    header = token_headers[1]

    response = client.get('/admin/user/search', query_string={
        "nouserunderthisnumber": "kappa"
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    assert 'message' in res

def test_not_found_search(client, token_headers):
    header = token_headers[1]

    response = client.get('/admin/user/search', query_string={
        "userId": "doesnotexist"
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    assert res == []

def test_no_query_params(client, token_headers):
    header = token_headers[1]
    response = client.get('/admin/user/search', headers=header)
    assert response.status_code == 200
    res = response.json
    assert set(res) == {'https://orcid.org/0000-0003-1681-4036',
                        'https://orcid.org/0000-0003-1485-4923',
                        'urn:uuid:7e56b6c4-42e5-4a9d-94cf-d6e22577fb4b',
                        'https://orcid.org/0000-0001-9277-3921',
                        'https://orcid.org/0000-0002-7403-9595',
                        'urn:uuid:3c9bdb26-2451-443c-9ece-edf285639dcc'}

def test_empty_query_params(client, token_headers):
    header = token_headers[1]
    response = client.get('/admin/user/search', query_string={}, headers=header)
    assert response.status_code == 200
    res = response.json
    assert set(res) == {'https://orcid.org/0000-0003-1681-4036',
                        'https://orcid.org/0000-0003-1485-4923',
                        'urn:uuid:7e56b6c4-42e5-4a9d-94cf-d6e22577fb4b',
                        'https://orcid.org/0000-0001-9277-3921',
                        'https://orcid.org/0000-0002-7403-9595',
                        'urn:uuid:3c9bdb26-2451-443c-9ece-edf285639dcc'}

def test_json_with_unknown_fields(client, token_headers, testproject):
    header = token_headers[1]

    response = client.get('/admin/user/search', query_string={
        "kappa": "dduck"
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    assert 'message' in res

