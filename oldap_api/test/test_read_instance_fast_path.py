"""GraphDB-independent regression tests for the instance-read fast path."""

from types import SimpleNamespace
from unittest.mock import Mock

from flask import Flask

from oldap_api.views import instance_views
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.enums.datapermissions import DataPermission
from oldaplib.src.helpers.context import Context
from oldaplib.src.objectfactory import ResourceReadResult
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_string import Xsd_string


def test_read_instance_uses_factory_result_without_preliminary_query(monkeypatch):
    """The route must obtain type provenance from the main factory read."""
    app = Flask(__name__)
    context_name = "READ_INSTANCE_FAST_PATH"
    context = Context(name=context_name)
    context["chama"] = NamespaceIRI("http://chama.salsah.org/ns/")

    connection = SimpleNamespace(context_name=context_name, query=Mock())
    concrete_type = Xsd_QName("chama:CataloguedPhotograph", validate=False)
    inferred_type = Xsd_QName("oldap:Thing", validate=False)
    result = ResourceReadResult(
        resource_class=concrete_type,
        asserted_types=(concrete_type,),
        properties={},
        data={
            "rdf:type": [concrete_type, inferred_type],
            "schema:name": [Xsd_string("K-36 #488 im Panorama")],
            Xsd_QName("oldap:attachedToRole"): {
                Xsd_QName("oldap:Unknown"): DataPermission.DATA_VIEW,
                Xsd_QName("chama:Editors"): DataPermission.DATA_UPDATE,
            },
        },
    )

    factory = Mock()
    factory.read_data.return_value = result
    factory_constructor = Mock(return_value=factory)
    monkeypatch.setattr(instance_views, "authenticated_connection", lambda: connection)
    monkeypatch.setattr(instance_views, "ResourceInstanceFactory", factory_constructor)

    with app.test_request_context("/data/chama/chama:IMG_1751"):
        response, status = instance_views.read_instance.__wrapped__(
            "chama",
            "chama:IMG_1751",
        )

    assert status == 200
    assert response.get_json() == {
        "rdf:type": ["chama:CataloguedPhotograph"],
        "schema:name": ["K-36 #488 im Panorama"],
        "oldap:attachedToRole": {
            "oldap:Unknown": "DATA_VIEW",
            "chama:Editors": "DATA_UPDATE",
        },
        "virtual:inferredTypes": ["oldap:Thing"],
    }
    connection.query.assert_not_called()
    factory_constructor.assert_called_once_with(con=connection, project="chama")
    factory.read_data.assert_called_once_with(Iri("chama:IMG_1751"))


def test_summary_endpoint_batches_metadata_and_media_delivery(monkeypatch):
    """One additive request returns readable summaries and media capabilities."""
    app = Flask(__name__)
    context_name = "RESOURCE_SUMMARY_ENDPOINT"
    context = Context(name=context_name)
    context["chama"] = NamespaceIRI("http://chama.salsah.org/ns/")

    media_iri = Iri("chama:IMG_1751", validate=False)
    concrete_type = Xsd_QName("chama:CataloguedPhotograph", validate=False)
    connection = SimpleNamespace(
        context_name=context_name,
        userIri=Iri("oldap:User", validate=False),
        userid="rosenth",
        userdata=SimpleNamespace(
            hasRole={Xsd_QName("oldap:Unknown"): DataPermission.DATA_VIEW}
        ),
        issue_media_token=Mock(return_value="summary-capability"),
    )
    read_result = ResourceReadResult(
        resource_class=concrete_type,
        asserted_types=(concrete_type,),
        properties={},
        data={
            "rdf:type": [concrete_type, Xsd_QName("oldap:Thing")],
            "schema:name": [Xsd_string("K-36 #488 im Panorama")],
            "shared:mediaAccessMode": [Xsd_string("local")],
            "shared:protocol": [Xsd_string("iiif")],
            "shared:serverUrl": [Xsd_string("https://media.example/iiif/3/")],
            "shared:assetId": [Xsd_string("IMG 1751")],
            Xsd_QName("oldap:attachedToRole"): {
                Xsd_QName("oldap:Unknown"): DataPermission.DATA_VIEW,
            },
        },
    )
    factory = Mock()
    factory.read_summaries.return_value = {media_iri: read_result}
    factory_constructor = Mock(return_value=factory)
    monkeypatch.setattr(instance_views, "authenticated_connection", lambda: connection)
    monkeypatch.setattr(instance_views, "ResourceInstanceFactory", factory_constructor)

    with app.test_request_context(
        "/data/summaries/chama",
        method="POST",
        json={
            "iris": ["chama:IMG_1751", "chama:Hidden"],
            "includeProperties": ["schema:name"],
            "includeMediaDelivery": True,
        },
    ):
        response, status = instance_views.summarize_instances.__wrapped__("chama")

    assert status == 200
    assert response.get_json() == {
        "resources": [
            {
                "iri": "chama:IMG_1751",
                "resclass": "chama:CataloguedPhotograph",
                "data": {
                    "rdf:type": ["chama:CataloguedPhotograph"],
                    "schema:name": ["K-36 #488 im Panorama"],
                    "virtual:inferredTypes": ["oldap:Thing"],
                },
                "mediaDelivery": {
                    "kind": "iiif-image",
                    "infoUrl": "https://media.example/iiif/3/IMG%201751/info.json",
                    "capability": "summary-capability",
                },
            }
        ]
    }
    factory.read_summaries.assert_called_once()
    requested = factory.read_summaries.call_args.kwargs
    assert requested["iris"] == [Iri("chama:IMG_1751"), Iri("chama:Hidden")]
    assert Xsd_QName("schema:name") in requested["include_properties"]
    assert Xsd_QName("shared:assetId") in requested["include_properties"]
    connection.issue_media_token.assert_called_once()
    token_claims = connection.issue_media_token.call_args.args[0]
    assert token_claims["projectShortName"] == "chama"
    assert token_claims["id"] == "IMG 1751"
    assert token_claims["assetId"] == "IMG 1751"
