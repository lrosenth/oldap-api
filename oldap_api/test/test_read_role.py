import re
from pprint import pprint


def test_read_permissionset(client, token_headers, testrole):
    header = token_headers[1]

    response = client.get('/admin/role/oldap/testrole', headers=header)

    assert response.status_code == 200
    res = response.json

    iso_datetime_regex = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?([+-]\d{2}:\d{2}|Z)$"

    assert res['roleIri'] == 'oldap:testrole'
    assert res['creator'] == 'https://orcid.org/0000-0003-1681-4036'
    assert re.match(iso_datetime_regex, res['created'])
    assert res['contributor'] == 'https://orcid.org/0000-0003-1681-4036'
    assert re.match(iso_datetime_regex, res['modified'])
    assert res['definedByProject'] == 'oldap:SystemProject'
    assert res['roleId'] == 'testrole'
    assert set(res['label']) == {'testPerm@en', 'test@de'}
    assert set(res['comment']) == {'For testing@en', 'Für Tests@de'}

def test_read_permissionset_by_iri(client, token_headers, testrole):
    header = token_headers[1]

    response = client.get('/admin/role/get', query_string={
        "iri": 'oldap:testrole'
    }, headers=header)

    assert response.status_code == 200
    res = response.json

    iso_datetime_regex = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?([+-]\d{2}:\d{2}|Z)$"

    assert res['roleIri'] == 'oldap:testrole'
    assert res['creator'] == 'https://orcid.org/0000-0003-1681-4036'
    assert re.match(iso_datetime_regex, res['created'])
    assert res['contributor'] == 'https://orcid.org/0000-0003-1681-4036'
    assert re.match(iso_datetime_regex, res['modified'])
    assert res['definedByProject'] == 'oldap:SystemProject'
    assert res['roleId'] == 'testrole'
    assert set(res['label']) == {'testPerm@en', 'test@de'}
    assert set(res['comment']) == {'For testing@en', 'Für Tests@de'}

def test_bad_token(client, token_headers):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.get('/admin/role/oldap/testrole', headers=header)
    assert response.status_code == 403
    res = response.json
    print(res)
    assert res["message"] == "Connection failed: Wrong credentials"


def test_read_nonexisting_permissionset(client, token_headers, testrole):
    header = token_headers[1]

    response = client.get('/admin/role/oldap/doesnotexist', headers=header)

    assert response.status_code == 404
    res = response.json
    print(res)
