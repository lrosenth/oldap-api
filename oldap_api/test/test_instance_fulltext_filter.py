import pytest
from flask import Flask

from oldap_api.views.instance_views import parse_ftfilter_items, parse_text_search_request
from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.objectfactory import FTSearchFilter


def test_parse_ftfilter_accepts_ncname_field():
    result = parse_ftfilter_items([
        {"field": "storyContent", "query": "geschichte"},
        "AND",
        {"fieldName": "abstract", "q": "larve"},
    ])

    assert result[0] == FTSearchFilter("storyContent", "geschichte")
    assert result[1] == "AND"
    assert result[2] == FTSearchFilter("abstract", "larve")


def test_parse_ftfilter_rejects_qname_field():
    with pytest.raises(OldapErrorValue):
        parse_ftfilter_items([
            {"field": "fasnacht:storyContent", "query": "geschichte"},
        ])


def test_parse_text_search_request_accepts_ftfield_ncname():
    app = Flask(__name__)

    with app.test_request_context("/data/search/fasnacht", method="POST", json={
        "resClass": "fasnacht:Story",
        "ftField": "storyContent",
        "q": "geschichte",
    }):
        params, error = parse_text_search_request()

    assert error is None
    assert params["ftfilter"] == [FTSearchFilter("storyContent", "geschichte")]


def test_parse_text_search_request_rejects_ftfield_qname():
    app = Flask(__name__)

    with app.test_request_context("/data/search/fasnacht", method="POST", json={
        "resClass": "fasnacht:Story",
        "ftField": "fasnacht:storyContent",
        "q": "geschichte",
    }):
        params, error = parse_text_search_request()

    assert params is None
    assert error[1] == 400
