from oldap_api import create_app

app = create_app()  # Gunicorn will import this

#CORS(app, origins="*", expose_headers=["Content-Disposition"])