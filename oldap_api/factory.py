from flask import Flask


def factory():
    app = Flask(__name__)

    from oldap_api.views import auth_views
    from oldap_api.views import user_views
    from oldap_api.views import project_views
    from oldap_api.views import permset_views
    from oldap_api.views import datamodelling_views
    from oldap_api.views import hierarchical_list_views
    from oldap_api.views import resource_views

    app.register_blueprint(auth_views.auth_bp)
    app.register_blueprint(user_views.user_bp)
    app.register_blueprint(project_views.project_bp)
    app.register_blueprint(permset_views.permset_bp)
    app.register_blueprint(datamodelling_views.datamodel_bp)
    app.register_blueprint(hierarchical_list_views.hierarchical_list_bp)
    app.register_blueprint(resource_views.resource_bp)

    return app
