"""Build a process-local API without invalidating shared object caches."""

import os
from pathlib import Path
from flask_cors import CORS
import logging
import click

from oldaplib.src.connection import Connection
from oldaplib.src.mutation_gate import mutation_gate

from oldap_api.factory import factory
from oldap_api.redis_config import validate_redis_database_separation
from oldaplib.src.cachesingleton import CacheSingletonRedis

def create_app():
    """Initialize routes, configuration and project prefixes before serving.

    Each process loads prefixes through the library's normal anonymous read
    connection. The connection/token is discarded; request authentication keeps
    creating independent connections. GraphDB and anonymous access must be
    available at startup. Shared cache invalidation is an explicit CLI action,
    never a side effect of worker startup or replacement.
    """
    app = factory()

    cfg = os.getenv("APP_ENV", "Prod")
    app.config.from_object(f"oldap_api.config.{cfg}")
    validate_redis_database_separation(production=cfg == "Prod")

    uploaddir = Path(app.config['UPLOAD_FOLDER'])
    if not uploaddir.exists():
        uploaddir.mkdir(parents=True, exist_ok=True)

    tmpdir = Path(app.config['TMP_FOLDER'])
    if not tmpdir.exists():
        tmpdir.mkdir(parents=True, exist_ok=True)

    level_name = app.config.get("LOG_LEVEL", "INFO")
    level = logging.getLevelName(level_name)
    app.logger.setLevel(level)

    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
    )
    for handler in app.logger.handlers:
        handler.setFormatter(fmt)


    lib_logger = logging.getLogger("oldaplib")  # or your package root name
    lib_logger.setLevel(app.logger.level)

    # Option A (recommended): let oldaplib propagate to root/app handlers
    lib_logger.propagate = True


    app.logger.info(f"Logging initialized at level {level_name}")
    app.logger.info(f"Using config {cfg}")
    app.logger.info(f"Upload folder: {uploaddir}")
    app.logger.info(f"Tmp folder: {tmpdir}")

    allowed_origins = [
        origin.strip()
        for origin in os.getenv("OLDAP_AUTH_ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    ]
    CORS(app,
         resources={r"/*": {"origins": allowed_origins or "*"}},
         supports_credentials=bool(allowed_origins),
         expose_headers=["Content-Disposition"])

    # Token-based connections skip prefix discovery. Bootstrap before accepting
    # requests so a cold worker can serve a token issued by another process.
    Connection(context_name="DEFAULT")

    @app.cli.command("clear-object-cache")
    def clear_object_cache():
        """Invalidate only the object cache during a quiescent maintenance window.

        Refuse an occupied/uncertain writer gate. CacheSingletonRedis also
        checks separation from the writer database immediately before clearing.
        Readers must be drained by the operator to prevent stale repopulation.
        """
        with mutation_gate(wait_seconds=0):
            CacheSingletonRedis().clear()
        click.echo("OLDAP object cache cleared; writer coordination preserved.")

    app.logger.info("Project context initialized; shared object cache preserved.")
    return app
