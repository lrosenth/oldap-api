"""Dating must retain uncertainty for detail, list and media consumers."""
import pytest
from flask import Flask


@pytest.fixture(autouse=True)
def structured_request():
    with Flask(__name__).test_request_context(headers={'Accept': 'application/json; dating=structured'}):
        yield


from oldap_api.views.instance_views import (
    _instance_read_json, _sanitize_instance_datatype, to_json_compatible_value,
)
from oldaplib.src.objectfactory import ResourceReadResult
from oldaplib.src.xsd.dating import Dating, DatePrecision, OldapCalendar
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.iri import Iri


def test_detail_and_search_keep_verbatim_precision_and_calendar():
    value = Dating((1515,), verbatimDate='[um 1515]')
    expected = {'dateStart': [1515], 'dateEnd': [1515],
                'verbatimDate': '[um 1515]', 'datePrecision': 'YEAR', 'inCalendar': 'GREGORIAN'}
    assert _sanitize_instance_datatype(value) == expected
    assert to_json_compatible_value({'fasnacht:dating': [value]}) == {'fasnacht:dating': [expected]}
    cls = Xsd_QName('fasnacht:ArchiveObject', validate=False)
    read = ResourceReadResult(resource_class=cls, asserted_types=(cls,), properties={},
                              data={'fasnacht:dating': [value]})
    assert _instance_read_json(read) == {'fasnacht:dating': [expected]}


def test_bounded_ranges_calendar_and_before_references_survive():
    earlier = Dating((1930,), (1939,), datePrecision=DatePrecision.DECADE,
                     verbatimDate='[193-?]', inCalendar=OldapCalendar.JULIAN,
                     iri=Iri('urn:uuid:date-1'))
    later = Dating((1940,), iri=Iri('urn:uuid:date-2'))
    value = Dating((1930,), (1939,), before={later}, inCalendar=OldapCalendar.JULIAN,
                   datePrecision=DatePrecision.DECADE, verbatimDate='[193-?]', iri=earlier.iri)
    encoded = to_json_compatible_value(value)
    assert encoded['dateStart'] == [1930]
    assert encoded['dateEnd'] == [1939]
    assert encoded['datePrecision'] == 'DECADE'
    assert encoded['inCalendar'] == 'JULIAN'
    assert encoded['verbatimDate'] == '[193-?]'
    assert encoded['iri'] == 'urn:uuid:date-1'
    assert encoded['before'] == ['urn:uuid:date-2']


def test_default_representation_remains_legacy():
    with Flask(__name__).test_request_context(headers={'Accept': 'application/json'}):
        value = Dating((1515,), verbatimDate='[um 1515]')
        assert _sanitize_instance_datatype(value) == str(value)
        assert to_json_compatible_value(value) == str(value)


def test_search_batches_only_dates_and_omits_unreadable(monkeypatch):
    from types import SimpleNamespace
    from oldap_api.views import instance_views as views
    prop = Xsd_QName('fasnacht:dating', validate=False)
    cls = Xsd_QName('fasnacht:ArchiveObject', validate=False)
    calls = []
    class Factory:
        def __init__(self, **kwargs):
            pass
        def createObjectInstance(self, name):
            return SimpleNamespace(resolved_properties=lambda: {
                prop: SimpleNamespace(datatype=None, toClass='oldap:Dating'),
                Xsd_QName('schema:name', validate=False): SimpleNamespace(datatype='string'),
            })
        def read_summaries(self, iris, include_properties):
            calls.append(len(iris))
            assert include_properties == {prop}
            return {iri: ResourceReadResult(resource_class=cls, asserted_types=(cls,), properties={},
                     data={str(prop): [Dating((1515,), verbatimDate='[um 1515]')]})
                    for iri in iris if str(iri) != 'urn:uuid:missing'}
    monkeypatch.setattr(views, 'ResourceInstanceFactory', Factory)
    rows = [{'iri': f'urn:uuid:{i}', 'resclass': cls, 'schema:name': ['Title'],
             'fasnacht:dating': ['urn:uuid:date'], 'score': 3} for i in range(100)]
    rows.append(dict(rows[0], iri='urn:uuid:missing'))
    views._expand_search_dating(None, 'fasnacht', rows, {prop, 'schema:name'})
    assert calls == [100, 1]
    assert rows[0]['fasnacht:dating'][0]['verbatimDate'] == '[um 1515]'
    assert all(row['schema:name'] == ['Title'] and row['score'] == 3 for row in rows)
    assert 'fasnacht:dating' not in rows[-1]
