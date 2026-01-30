import pytest
from pprint import pprint


def test_instance_read(client, token_headers, testfulldatamodelwithinstances):
    header = token_headers[1]

    response = client.get(f'/data/hyha/{testfulldatamodelwithinstances}', headers=header)
    assert response.status_code == 200

    res = response.json
    print("\n")
    pprint(res)
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

def test_retrieving_mediaobject(client, token_headers, testfulldatamodelwithmediaobject):
    header = token_headers[1]

    response = client.get(f'/data/mediaobject/id/xayb01.tif', headers=header)
    assert response.status_code == 200
    res = response.json
    assert res['graph'] == 'hyha:data'
    assert res['permval'] == '2'
    assert res['shared:originalMimeType'] == 'image/tiff'
    assert res['shared:originalName'] == 'test.tif'
    assert res['shared:path'] == 'britnet'
    assert res['shared:protocol'] == 'iiif'
    assert res['shared:serverUrl'] == 'https://iiif.oldap.org'

def test_retrieving_derived_mediaobject(client, token_headers, testfulldatamodelwithderivedmediaobject):
    header = token_headers[1]

    response = client.get(f'/data/mediaobject/id/DCS_0001.tif', headers=header)
    assert response.status_code == 200
    res = response.json
    assert res['graph'] == 'hyha:data'
    assert res['permval'] == '2'
    assert res['shared:originalMimeType'] == 'image/tiff'
    assert res['shared:originalName'] == 'shakespeare.tif'
    assert res['shared:path'] == 'britnet'
    assert res['shared:protocol'] == 'iiif'
    assert res['shared:serverUrl'] == 'https://iiif.oldap.org'
    assert res['hyha:hasCaption'] == ['This is a test caption']

def test_retrieving_derived_mediaobject_by_iri(client, token_headers, testfulldatamodelwithderivedmediaobject):
    header = token_headers[1]

    iri = testfulldatamodelwithderivedmediaobject

    response = client.get(f'/data/mediaobject/iri/{iri}', headers=header)
    assert response.status_code == 200
    res = response.json
    assert res['graph'] == 'hyha:data'
    assert res['permval'] == '2'
    assert res['shared:originalMimeType'] == 'image/tiff'
    assert res['shared:originalName'] == 'shakespeare.tif'
    assert res['shared:path'] == 'britnet'
    assert res['shared:protocol'] == 'iiif'
    assert res['shared:serverUrl'] == 'https://iiif.oldap.org'
    assert res['hyha:hasCaption'] == ['This is a test caption']


