import os
from pathlib import Path

class Base:
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", str(Path(os.getcwd()) / 'uploads'))
    TMP_FOLDER = os.getenv("UPLOAD_FOLDER", str(Path(os.getcwd()) / 'tmp'))


class Dev(Base):
    DEBUG = True
    OLDAP_API_PORT = os.getenv("OLDAP_API_PORT", 8000)
    LOG_LEVEL = "DEBUG"


class Prod(Base):
    DEBUG = False
    OLDAP_API_PORT = os.getenv("OLDAP_API_PORT", 8000)
    LOG_LEVEL = "INFO"