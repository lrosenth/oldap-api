import pytest
import coverage

from app import app

def test_create_user(client, auth, app):
    with app.app_context():
