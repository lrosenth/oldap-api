from oldap_api import create_app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=app.config['OLDAP_API_PORT'])