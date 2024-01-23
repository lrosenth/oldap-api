from flask import Flask


def factory():
    app = Flask(__name__)

    import admin
    app.register_blueprint(admin.bp)

    return app
