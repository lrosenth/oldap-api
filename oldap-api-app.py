from flask_cors import CORS

from factory import factory

app = factory()
CORS(app)

if __name__ == '__main__':
    app.run(debug=True)