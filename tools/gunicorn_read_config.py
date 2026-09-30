"""Local experiment only: reject non-catalog operations and identify workers.

Load explicitly with Gunicorn --config. Never use as production configuration.
All workers use the normal WSGI application; hooks add only a read-route boundary
and a PID response header so cold-worker coverage can be established.
"""
import os
from flask import request


def post_worker_init(worker):
    """Apply the same compact JSON behavior as the native debug=False service."""
    app = worker.wsgi
    app.debug = False

    @app.before_request
    def read_only():
        """Refuse mutations, including writable routes reached with POST."""
        path = request.path
        allowed = (request.method == "GET" and (
            path in {"/health", "/status", "/admin/datamodel/fasnacht", "/admin/datamodel/shared"}
            or path.startswith(("/data/fasnacht/", "/data/textsearch/fasnacht", "/admin/hlist/fasnacht/"))
        )) or (request.method == "POST" and path in {
            "/data/search/fasnacht", "/data/summaries/fasnacht", "/admin/auth/unknown"})
        if not allowed:
            return {"message": "Read-only experiment."}, 405

    @app.after_request
    def identify_worker(response):
        """Expose only the test worker PID for preflight coverage checks."""
        response.headers["X-Load-Worker"] = str(os.getpid())
        return response
