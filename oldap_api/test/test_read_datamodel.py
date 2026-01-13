from pprint import pprint

def test_read_datamodel_extontos(client, token_headers, testdatamodelwithexternalontology):
    header = token_headers[1]

    response = client.get('/admin/datamodel/hyha', headers=header)

    res = response.json
    assert response.status_code == 200
    assert len(res['externalOntologies']) == 1


def test_read_standaloneporp_datamodel_A(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.get('/admin/datamodel/hyha', headers=header)

    res = response.json
    pprint(res)
    assert response.status_code == 200

def test_read_standaloneporp_datamodel_B(client, token_headers, testfulldatamodelpropwithtype):
    header = token_headers[1]

    response = client.get('/admin/datamodel/hyha', headers=header)

    res = response.json
    pprint(res)
    assert response.status_code == 200

def test_read_standaloneporp_datamodel_C(client, token_headers, testfulldatamodelresourcedatatypesB):
    header = token_headers[1]

    response = client.get('/admin/datamodel/hyha', headers=header)

    res = response.json
    pprint(res)
    assert response.status_code == 200
    hasprops = res['resources'][0]['hasProperty']
    for hasprop in hasprops:
        if hasprop['property']['iri'] == 'hyha:titleB':
            assert hasprop['property']['type'] == ['SymmetricProperty']
        if hasprop['property']['iri'] == 'hyha:numPagesB':
            assert hasprop['property']['type'] == ['TransitiveProperty']


def test_bad_token(client, token_headers):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.get('/admin/datamodel/hyha', headers=header)
    assert response.status_code == 403
    res = response.json
    print(res)
    assert res["message"] == "Connection failed: Wrong credentials"


def test_read_nonexisting_dm(client, token_headers, testrole):
    header = token_headers[1]

    response = client.get('/admin/datamodel/doesnotexist', headers=header)

    assert response.status_code == 404
    res = response.json
    print(res)

def test_download_dm(client, token_headers):
    header = token_headers[1]

    response = client.get('/admin/datamodel/shared/download', headers=header)
    assert response.status_code == 200
    assert response.headers["Content-Type"] == 'application/trig'
    cd = response.headers.get("Content-Disposition", "")
    assert "attachment" in cd
    assert 'filename="shared.trig"' in cd
    data = response.data.decode("utf-8")
    assert data.startswith("\n@prefix")

def test_read_shared(client, token_headers):
    header = token_headers[1]

    response = client.get('/admin/datamodel/shared', headers=header)
    assert response.status_code == 200
    res = response.json
    pprint(res)

