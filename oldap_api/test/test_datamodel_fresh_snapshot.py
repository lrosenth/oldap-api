"""Administrative reads must observe graph deletion despite an older model cache."""
from unittest.mock import Mock, patch
import pytest
from flask import Flask
from oldap_api.views.datamodelling_views import datamodel_bp
from oldaplib.src.helpers.oldaperror import OldapErrorNotFound


@pytest.mark.parametrize('suffix', ['', '/download'])
def test_external_graph_deletion_is_not_hidden_by_cached_model(suffix):
    app = Flask(__name__)
    app.register_blueprint(datamodel_bp)
    cached = Mock()
    cached.get_extontos.return_value = []
    cached.get_propclasses.return_value = []
    cached.get_resclasses.return_value = []
    cached.write_as_str.return_value = 'stale model snapshot'

    def read(_con, _project, *, ignore_cache=False):
        if ignore_cache:
            raise OldapErrorNotFound('Model graphs were deleted outside the API')
        return cached

    with patch('oldap_api.authentication.Connection'), patch(
        'oldap_api.views.datamodelling_views.DataModel.read', side_effect=read
    ):
        response = app.test_client().get('/admin/datamodel/demo' + suffix,
                                         headers={'Authorization': 'Bearer test'})
    assert response.status_code == 404
    assert 'deleted outside' in response.json['message']
    cached.write_as_str.assert_not_called()
