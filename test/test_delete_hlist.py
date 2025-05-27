from pprint import pprint


def test_delete_hlist(client, token_headers, testemptyhlist):
    header = token_headers[1]

    response = client.delete('/admin/hlist/hyha/testhlist', headers=header)
    assert response.status_code == 200
    res = response.get_json()
    print(res)

    response = client.get('/admin/hlist/hyha/testhlist', headers=header)
    assert response.status_code == 404
    res = response.json
    print(res)

def test_delete_full_hlist(client, token_headers, testfullhlist):
    header = token_headers[1]

    response = client.delete('/admin/hlist/hyha/testfullhlist', headers=header)
    print(response.text)

    response = client.get('/admin/hlist/hyha/testfullhlist', headers=header)
    assert response.status_code == 404
    res = response.json
    print(res)

def test_list_in_use(client, token_headers, testemptydatamodel, testfullhlist):
    header = token_headers[1]

    response = client.get('/admin/hlist/hyha/testfullhlist', headers=header)
    hlist = response.json

    response = client.put('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "class": hlist['nodeClassIri'],
        "name": ["SELECTION@en", "SELECTION@de"],
    }, headers=header)

    response = client.delete('/admin/hlist/hyha/testfullhlist', headers=header)
    assert response.status_code == 409
    print(response.text)


