import os
from pathlib import Path

from flask_cors import CORS

from oldaplib.src.oldaplogging import set_logger

from oldap_api.factory import factory

app = factory()
set_logger(app.logger)

uploaddir = Path(os.getcwd()) /  'uploads'

if not uploaddir.exists():
    uploaddir.mkdir()
app.config['UPLOAD_FOLDER'] = str(uploaddir)

tmpdir = Path(os.getcwd()) / 'tmp'
if not tmpdir.exists():
    tmpdir.mkdir()

app.config['TMP_FOLDER'] = tmpdir
CORS(app, expose_headers=["Content-Disposition"])


if __name__ == '__main__':
    app.run(debug=True)