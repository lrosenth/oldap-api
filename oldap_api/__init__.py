import os
from pathlib import Path
from flask_cors import CORS
import logging

from oldaplib.src.oldaplogging import set_logger
from oldap_api.factory import factory

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
    set_logger(app.logger)

    app.logger.info(f"Logging initialized at level {level_name}")
    app.logger.info(f"Using config {cfg}")
    app.logger.info(f"Upload folder: {uploaddir}")
    app.logger.info(f"Tmp folder: {tmpdir}")

    #CORS(app, origins="*", expose_headers=["Content-Disposition"])
    CORS(app,
         resources={r"/*": {"origins": "*"}},
         supports_credentials=False,
         expose_headers=["Content-Disposition"])

    return app