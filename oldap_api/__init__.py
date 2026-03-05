import os
from pathlib import Path
from flask_cors import CORS
import logging

from oldap_api.factory import factory
from oldaplib.src.cachesingleton import CacheSingletonRedis

def create_app():
    app = factory()

    cfg = os.getenv("APP_ENV", "Prod")
    app.config.from_object(f"oldap_api.config.{cfg}")

    uploaddir = Path(app.config['UPLOAD_FOLDER'])
    if not uploaddir.exists():
        uploaddir.mkdir()

    tmpdir = Path(app.config['TMP_FOLDER'])
    if not tmpdir.exists():
        tmpdir.mkdir()

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

    #CORS(app, origins="*", expose_headers=["Content-Disposition"])
    CORS(app,
         resources={r"/*": {"origins": "*"}},
         supports_credentials=False,
         expose_headers=["Content-Disposition"])

    cache = CacheSingletonRedis()
    cache.clear()

    app.logger.info(f"Redis cache cleared.")
    return app