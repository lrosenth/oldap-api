import os
from pathlib import Path
from flask_cors import CORS

from oldaplib.src.oldaplogging import set_logger
from oldap_api.factory import factory

def create_app():
    app = factory()
    set_logger(app.logger)

    cfg = os.getenv("APP_ENV", "Prod")
    app.config.from_object(f"oldap_api.config.{cfg}")

    uploaddir = Path(app.config['UPLOAD_FOLDER'])
    if not uploaddir.exists():
        uploaddir.mkdir()

    tmpdir = Path(app.config['TMP_FOLDER'])
    if not tmpdir.exists():
        tmpdir.mkdir()

    #CORS(app, origins="*", expose_headers=["Content-Disposition"])
    CORS(app,
         resources={r"/*": {"origins": "*"}},
         supports_credentials=False,
         expose_headers=["Content-Disposition"])

    return app