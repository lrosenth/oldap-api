"""History endpoints retain ordinary update guards and route conventions."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from flask import Flask

from oldap_api.views import instance_views as views
from oldaplib.src.helpers.oldaperror import OldapErrorNoPermission, OldapErrorNotFound
from oldaplib.src.resource_history import ResourceHistory, PropertyHistoryEntry
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_datetimestamp import Xsd_dateTimeStamp
from oldaplib.src.xsd.xsd_string import Xsd_string


@pytest.fixture
def api(monkeypatch):
    app = Flask(__name__)
    app.register_blueprint(views.instance_bp)
    con = object()
    monkeypatch.setattr(views, 'authenticated_connection', lambda: con)
    entry = PropertyHistoryEntry(Iri('urn:test:history'), Xsd_dateTimeStamp('2026-01-01T00:00:00Z'),
        Iri('urn:test:editor'), Iri('urn:test:one'), Xsd_QName('schema:name'), (Xsd_string('Before@en'),))
    return app, con, entry


def test_routes_resolve_before_generic_instance_routes(api):
    app, _, _ = api
    adapter = app.url_map.bind('localhost')
    for path, method, endpoint in [
        ('/data/history/hist/https://example.org/one', 'GET', 'instance.instance_history'),
        ('/data/history/hist/urn:test:one/restore', 'POST', 'instance.restore_instance_history'),
    ]:
        assert adapter.match(path, method=method)[0] == endpoint


def test_history_list_shape_filter_and_paging(api, monkeypatch):
    app, con, entry = api
    listing = Mock(return_value=[entry])
    monkeypatch.setattr(ResourceHistory, '__init__', lambda *args: None)
    monkeypatch.setattr(ResourceHistory, 'list', listing)
    with app.test_request_context('/?property=schema:name&limit=2&offset=4'):
        response, status = views.instance_history.__wrapped__('hist', 'urn:test:one')
    assert status == 200
    assert response.get_json()['items'][0]['values'] == ['Before@en']
    listing.assert_called_once_with(Iri('urn:test:one'), property_iri='schema:name', limit=2, offset=4)


@pytest.mark.parametrize('error,status', [(OldapErrorNoPermission('denied'), 403),
                                        (OldapErrorNotFound('missing'), 404)])
def test_history_does_not_bypass_read_permissions(api, monkeypatch, error, status):
    app, _, _ = api
    monkeypatch.setattr(ResourceHistory, '__init__', lambda *args: None)
    monkeypatch.setattr(ResourceHistory, 'list', Mock(side_effect=error))
    with app.test_request_context('/'):
        assert views.instance_history.__wrapped__('hist', 'urn:test:one')[1] == status


def test_restore_passes_typed_values_to_shared_update_path(api, monkeypatch):
    app, con, entry = api
    monkeypatch.setattr(ResourceHistory, '__init__', lambda *args: None)
    monkeypatch.setattr(ResourceHistory, 'get', Mock(return_value=entry))
    update = Mock(return_value=('ordinary result', 200))
    monkeypatch.setattr(views, '_update_instance_data', update)
    with app.test_request_context('/', method='POST', json={'historyIri': str(entry.iri)}):
        assert views.restore_instance_history.__wrapped__('hist', 'urn:test:one') == ('ordinary result', 200)
    update.assert_called_once_with('hist', 'urn:test:one', {'schema:name': list(entry.values)},
                                   connection=con, annotation_restore=(entry.property_iri, ()))


@pytest.mark.parametrize('payload', [None, [], {}, {'historyIri': 1},
                                      {'historyIri': 'urn:test:history', 'property': 'oldap:createdBy'}])
def test_restore_rejects_ambiguous_payloads(api, payload):
    app, _, _ = api
    with app.test_request_context('/', method='POST', json=payload):
        assert views.restore_instance_history.__wrapped__('hist', 'urn:test:one')[1] == 400


def test_manual_and_history_share_structure_restriction(api):
    _, _, _ = api
    cls = type('Archive', (), {'name': Xsd_QName('shared:ArchiveUnit'), 'superclass': {}})
    error = views._apply_instance_update_payload(cls(), {'shared:parentArchiveUnit': ['urn:test:parent']})
    assert 'archive-move' in error


@pytest.mark.parametrize('resource_class,property_name,values,handler,payload', [
    ('shared:ArchiveUnit', 'shared:parentArchiveUnit', (Iri('urn:old:parent'),),
     '_move_archive_unit_data', {'shared:parentArchiveUnit': 'urn:old:parent'}),
    ('shared:ArchiveUnit', 'schema:position', (3,),
     '_move_archive_unit_data', {'shared:parentArchiveUnit': 'urn:current:parent', 'schema:position': 3}),
    ('shared:StagingFolder', 'shared:inStagingFolder', (Iri('urn:old:folder'),),
     '_move_staging_folder_data', {'shared:inStagingFolder': 'urn:old:folder'}),
])
def test_hierarchy_restore_uses_existing_move_commands(api, monkeypatch, resource_class,
                                                       property_name, values, handler, payload):
    from dataclasses import replace
    app, con, entry = api
    entry = replace(entry, property_iri=Xsd_QName(property_name), values=values)
    cls = type('Hierarchy', (), {'name': Xsd_QName(resource_class), 'superclass': {},
                                'get': lambda *args: [Iri('urn:current:parent')],
                                'resolved_properties': lambda self: {}})

    def initialize(self, *args):
        self.factory = SimpleNamespace(read=lambda iri: cls())

    monkeypatch.setattr(ResourceHistory, '__init__', initialize)
    monkeypatch.setattr(ResourceHistory, 'get', Mock(return_value=entry))
    move = Mock(return_value=('moved', 200))
    monkeypatch.setattr(views, handler, move)
    with app.test_request_context('/', method='POST', json={'historyIri': str(entry.iri)}):
        assert views.restore_instance_history.__wrapped__('hist', 'urn:test:one') == ('moved', 200)
    move.assert_called_once_with('hist', 'urn:test:one', payload, connection=con)


@pytest.mark.parametrize('existing_policy', [False, True])
def test_annotated_hierarchy_restore_is_rejected_before_move(api, monkeypatch, existing_policy):
    from dataclasses import replace
    app, con, entry = api
    entry = replace(entry, property_iri=Xsd_QName('shared:parentArchiveUnit'),
                    values=(Iri('urn:old:parent'),), annotations=() if existing_policy else ({'iri':'urn:visit'},))
    prop = SimpleNamespace(reifierShapes=['shared:VisitShape'], reificationRequired=None)
    cls = type('Hierarchy', (), {'name': Xsd_QName('shared:ArchiveUnit'), 'superclass': {},
        'resolved_properties': lambda self: {entry.property_iri: prop} if existing_policy else {}})
    def initialize(self, *args):
        self.factory = SimpleNamespace(read=lambda iri: cls())
    monkeypatch.setattr(ResourceHistory, '__init__', initialize)
    monkeypatch.setattr(ResourceHistory, 'get', Mock(return_value=entry))
    move = Mock()
    monkeypatch.setattr(views, '_move_archive_unit_data', move)
    with app.test_request_context('/', method='POST', json={'historyIri':str(entry.iri)}):
        response, status = views.restore_instance_history.__wrapped__('hist','urn:test:one')
    assert status == 400 and 'Annotated hierarchy' in response.json['message']
    move.assert_not_called()
