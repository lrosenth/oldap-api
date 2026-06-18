
import string
import random

import pytest
from flask import Flask

from oldap_api.views.instance_views import parse_hlfilter_items, parse_search_filter_items, parse_text_search_request
from oldaplib.src.objectfactory import CompOp, HLSearchFilter, SearchFilter
try:
    from oldaplib.src.objectfactory import LinkedResourceSearchFilter
except ImportError:
    LinkedResourceSearchFilter = None
from oldaplib.src.xsd.listnode import HListNodeRef
from oldaplib.src.xsd.xsd_qname import Xsd_QName

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


def test_parse_search_filter_not_exists_defaults_value_to_property():
    if not hasattr(CompOp, "NOT_EXISTS"):
        pytest.skip("Requires oldaplib with CompOp.NOT_EXISTS.")

    res = parse_search_filter_items([
        {
            "property": "test:optionalProperty",
            "op": "NOT_EXISTS"
        }
    ])

    assert len(res) == 1
    assert isinstance(res[0], SearchFilter)
    assert getattr(res[0].op, "name", res[0].op) == "NOT_EXISTS"
    assert isinstance(res[0].value, Xsd_QName)
    assert str(res[0].value) == "test:optionalProperty"


def test_parse_search_filter_linked_resource():
    if LinkedResourceSearchFilter is None:
        pytest.skip("Requires oldaplib with LinkedResourceSearchFilter.")

    res = parse_search_filter_items([
        {
            "linkProperty": "fasnacht:associatedOrganisation",
            "linkedClass": "fasnacht:Organisation",
            "property": "fasnacht:organisationTaxonomy",
            "op": "EQ",
            "value": "L-xxxx:Guggenmusik",
            "type": "qname",
            "checkLinkedPermissions": True
        }
    ])

    assert len(res) == 1
    assert isinstance(res[0], LinkedResourceSearchFilter)
    assert str(res[0].linkProp) == "fasnacht:associatedOrganisation"
    assert str(res[0].linkedClass) == "fasnacht:Organisation"
    assert str(res[0].prop) == "fasnacht:organisationTaxonomy"
    assert res[0].op == CompOp.EQ
    assert str(res[0].value) == "L-xxxx:Guggenmusik"
    assert res[0].checkLinkedPermissions is True


def test_parse_text_search_request_accepts_linked_resource_filter():
    if LinkedResourceSearchFilter is None:
        pytest.skip("Requires oldaplib with LinkedResourceSearchFilter.")

    app = Flask(__name__)
    with app.test_request_context("/data/search/fasnacht/class/fasnacht:CarnivalThing", method="POST", json={
        "filter": [
            {
                "linkProperty": "fasnacht:associatedOrganisation",
                "linkedClass": "fasnacht:Organisation",
                "property": "fasnacht:organisationTaxonomy",
                "op": "==",
                "value": "L-xxxx:Guggenmusik",
                "type": "qname",
                "checkLinkedPermissions": "true"
            }
        ]
    }):
        params, error = parse_text_search_request(resclass="fasnacht:CarnivalThing")

    assert error is None
    assert params["resClass"] == Xsd_QName("fasnacht:CarnivalThing")
    assert isinstance(params["filter"][0], LinkedResourceSearchFilter)
    assert params["filter"][0].checkLinkedPermissions is True


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
