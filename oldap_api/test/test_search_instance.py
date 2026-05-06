
import string
import random

from oldap_api.views.instance_views import parse_hlfilter_items
from oldaplib.src.objectfactory import HLSearchFilter
from oldaplib.src.xsd.listnode import HListNodeRef

def test_instance_textsearch_A(client, token_headers, testemptydatamodeltest):
    header = token_headers[1]

    response = client.get(f'/data/textsearch/test', query_string={
        "searchString": "waseliwas",
        "countOnly": "true"
    }, headers=header)
    assert response.status_code == 200
    res = response.json

    assert res['count'] == 4


def test_instance_textsearch_B(client, token_headers, testemptydatamodeltest):
    header = token_headers[1]

    response = client.get(f'/data/textsearch/test', query_string={
        "searchString": "waseliwas",
    }, headers=header)
    assert response.status_code == 200
    res = response.json

    assert len(res) == 4


def test_instance_text_count_resclass_A(client, token_headers, testemptydatamodeltest):
    header = token_headers[1]

    response = client.post(f'/data/search/test/class/test:Sort', json={
        "countOnly": True
    }, headers=header)
    assert response.status_code == 200
    res = response.json

    assert res['count'] == 3


def test_instance_text_get_resclass_A(client, token_headers, testemptydatamodeltest):
    header = token_headers[1]

    response = client.post(f'/data/search/test', json={
        "resClass": "test:Sort",
        "includeProperties": ["test:aString", "test:anInteger"]
    }, headers=header)
    assert response.status_code == 200
    res = response.json

    assert len(res) == 3
    assert res[0]['iri'] == 'test:Item1'
    assert res[0]['resclass'] == 'test:Sort'


def test_instance_text_post_count_resclass_A(client, token_headers, testemptydatamodeltest):
    header = token_headers[1]

    response = client.post(f'/data/search/test', json={
        "resClass": "test:Sort",
        "countOnly": True
    }, headers=header)
    assert response.status_code == 200
    res = response.json

    assert res['count'] == 3


def test_instance_text_post_with_resclass_A(client, token_headers, testemptydatamodeltest):
    header = token_headers[1]

    response = client.post(f'/data/search/test/class/test:Sort', json={
        "includeProperties": ["test:aString", "test:anInteger"],
        "sortBy": [{"property": "test:aString", "direction": "asc"}]
    }, headers=header)
    assert response.status_code == 200
    res = response.json

    assert len(res) == 3
    assert res[0]['iri'] == 'test:Item1'


def test_instance_text_post_filter_A(client, token_headers, testemptydatamodeltest):
    header = token_headers[1]

    response = client.post(f'/data/search/test', json={
        "resClass": "test:Sort",
        "filter": [
            {
                "property": "test:anInteger",
                "op": ">",
                "value": 0,
                "type": "integer"
            }
        ]
    }, headers=header)
    assert response.status_code == 200
    res = response.json

    assert len(res) == 3


def test_parse_hlfilter_items_structured_node_ref():
    res = parse_hlfilter_items([
        {
            "property": "test:category",
            "node": {
                "listId": "StoryKeywords",
                "nodeId": "ObjekteUndSammlungen"
            }
        }
    ])

    assert len(res) == 1
    assert isinstance(res[0], HLSearchFilter)
    assert isinstance(res[0].node, HListNodeRef)
    assert str(res[0].node.listId) == "StoryKeywords"
    assert str(res[0].node.nodeId) == "ObjekteUndSammlungen"


def test_instance_allofclass_A(client, token_headers, testemptydatamodeltest):
    header = token_headers[1]

    response = client.get(f'/data/ofclass/test', query_string={
        "resClass": "test:Sort",
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    assert len(res) == 3
    assert res[0]['iri'] == 'test:Item1'
    assert res[1]['iri'] == 'test:Item2'
    assert res[2]['iri'] == 'test:Item3'

def test_instance_allofclass_B(client, token_headers, testemptydatamodeltest):
    header = token_headers[1]

    response = client.get(f'/data/ofclass/test', query_string={
        "resClass": "test:Sort",
        "sortBy[]": ["test:aString|asc"]
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    assert len(res) == 3
    assert res[0]['iri'] == 'test:Item1'
    assert res[1]['iri'] == 'test:Item2'
    assert res[2]['iri'] == 'test:Item3'

def test_instance_allofclass_C(client, token_headers, testemptydatamodeltest):
    header = token_headers[1]

    response = client.get(f'/data/ofclass/test', query_string={
        "resClass": "test:Sort",
        "sortBy[]": ["test:anInteger|desc"]
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    assert len(res) == 3
    assert {x['iri'] for x in res} == {'test:Item1', 'test:Item2', 'test:Item3'}


def test_instance_allofclass_image_object(client, token_headers, testfulldatamodelwithderivedmediaobject):
    header = token_headers[1]

    response = client.get(f'/data/ofclass/hyha', query_string={
        "resClass": "hyha:ImageObject",
        "sortBy[]": ['test:modificationDate|desc']
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)
