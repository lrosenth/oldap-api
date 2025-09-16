import os
from pathlib import Path


class Base:
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", str(Path(os.getcwd()) / 'uploads'))
    TMP_FOLDER = os.getenv("UPLOAD_FOLDER", str(Path(os.getcwd()) / 'tmp'))


class Dev(Base): DEBUG = True
class Prod(Base): DEBUG = False