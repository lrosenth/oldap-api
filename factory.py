from flask import Flask


def factory():
    app = Flask(__name__)

    from views import auth_views
    from views import user_views
    from views import project_views
    from views import permset_views

    app.register_blueprint(auth_views.auth_bp)
    app.register_blueprint(user_views.user_bp)
    app.register_blueprint(project_views.project_bp)
    app.register_blueprint(permset_views.permset_bp)

    return app
