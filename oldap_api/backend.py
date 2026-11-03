"""One explicit backend choice for all API-owned connections."""
import os
from oldaplib.src.connection import Connection as GraphDBConnection
from oldaplib.src.helpers.oldaperror import OldapErrorConfiguration


def backend_name():
    """Keep GraphDB as default; reject typos rather than silently falling back."""
    name = os.getenv('OLDAP_BACKEND', 'graphdb')
    if name not in {'graphdb', 'jena'}:
        raise OldapErrorConfiguration('OLDAP_BACKEND must be graphdb or jena.')
    return name


def create_connection(**kwargs):
    """Construct the selected connection with the existing caller's keywords."""
    if backend_name() == 'graphdb':
        return GraphDBConnection(**kwargs)
    from oldaplib.src.jena_connection import JenaConnection
    return JenaConnection(**kwargs)


def validate_backend():
    """Reject incomplete Jena settings before the API begins serving requests."""
    if backend_name() == 'jena':
        from oldaplib.src.jena_connection import JenaSettings
        JenaSettings.from_environment()
        if not os.getenv('OLDAP_JENA_IDENTITY_KEY'):
            raise OldapErrorConfiguration('Jena requires a private identity-verification key.')
