from flask import Flask


def factory():
    app = Flask(__name__)

    import admin
    import auth_views
    import user_views
    import project_views
    import permset_views

    app.register_blueprint(admin.bp)
    app.register_blueprint(auth_views.auth_bp)
    app.register_blueprint(user_views.user_bp)
    app.register_blueprint(project_views.project_bp)
    app.register_blueprint(permset_views.permset_bp)

    return app
