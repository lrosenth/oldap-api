import requests
import os

from flask import Flask, jsonify
from oldap_api.version import __version__
from datetime import datetime, UTC


def factory():
    app = Flask(__name__)

    # Simple status endpoint
    @app.route("/status", methods=["GET"])
    def status():
        return jsonify({"status": "ok"}), 200

    # Health check
    @app.route("/health", methods=["GET"])
    def health():
        graphdb_url = os.getenv("OLDAP_TS_SERVER", "http://localhost:7200")

        try:
            r = requests.get(
                f"{graphdb_url}/rest/repositories",
                headers={"Accept": "application/json"},
                timeout=2,
            )
            if r.status_code == 200:
                graphdb_status = "up, repository oldap not found"
                repositories = r.json()
                for repo in repositories:
                    if repo['id'] == 'oldap':
                        graphdb_status = "reachable"
            else:
                graphdb_status = "error"
        except Exception:
            graphdb_status = "unreachable"

        return jsonify({
            "status": "ok" if graphdb_status == "reachable" else "degraded",
            "version": f'v{__version__}',
            "services": {
                "graphdb": graphdb_status
            },
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z")
        }), 200

    from oldap_api.views import auth_views
    from oldap_api.views import user_views
    from oldap_api.views import project_views
    from oldap_api.views import role_views
    from oldap_api.views import datamodelling_views
    from oldap_api.views import hierarchical_list_views
    from oldap_api.views import resource_views
    from oldap_api.views import instance_views

    app.register_blueprint(auth_views.auth_bp)
    app.register_blueprint(user_views.user_bp)
    app.register_blueprint(project_views.project_bp)
    app.register_blueprint(role_views.role_bp)
    app.register_blueprint(datamodelling_views.datamodel_bp)
    app.register_blueprint(hierarchical_list_views.hierarchical_list_bp)
    app.register_blueprint(resource_views.resource_bp)
    app.register_blueprint(instance_views.instance_bp)

    @app.get("/_routes")
    def _routes():
        return {
            "rules": [
                {"rule": str(r), "endpoint": r.endpoint, "methods": sorted(r.methods)}
                for r in app.url_map.iter_rules()
            ]
        }
    return app
