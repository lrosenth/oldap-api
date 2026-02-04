
import string
import random

def test_instance_textsearch_A(client, token_headers, testemptydatamodeltest):
    header = token_headers[1]

    response = client.get(f'/data/textsearch/test', query_string={
        "searchString": "waseliwas",
        "countOnly": "true"
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)

    assert res['count'] == 4

    #assert len(res) == 4


def test_instance_textsearch_B(client, token_headers, testemptydatamodeltest):
    header = token_headers[1]

    response = client.get(f'/data/textsearch/test', query_string={
        "searchString": "waseliwas",
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)

    assert len(res) == 4

def test_instance_allofclass_A(client, token_headers, testemptydatamodeltest):
    header = token_headers[1]

    response = client.get(f'/data/ofclass/test', query_string={
        "resClass": "test:Page",
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)

def test_instance_allofclass_B(client, token_headers, testemptydatamodeltest):
    header = token_headers[1]

    response = client.get(f'/data/ofclass/test', query_string={
        "resClass": "test:Book",
        "sortBy[]": ["test:author|asc"]
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)

    #assert len(res) == 4

def test_instance_allofclass_image_object(client, token_headers, testfulldatamodelwithderivedmediaobject):
    header = token_headers[1]

    response = client.get(f'/data/ofclass/hyha', query_string={
        "resClass": "hyha:ImageObject",
        "sortBy[]": ['test:modificationDate|desc']
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)
