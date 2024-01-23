import jwt

from flask import Flask, request, jsonify, Blueprint
from omaslib.src.connection import Connection
from omaslib.src.helpers.omaserror import OmasError


bp = Blueprint('auth', __name__, url_prefix='/admin')

@bp.route('/login', methods=['POST'])
def admin_login():
    if request.is_json:
        data = request.get_json()

        if 'token' in data:
            try:
                con = Connection(server='http://localhost:7200',
                                 repo="omas",
                                 userid="rosenth",
                                 credentials="RioGrande",
                                 context_name="DEFAULT")
                return con.token
            except OmasError:
                pass

        else:  # falls kein token kommt
            pass
    else:  # Fehlerbehandlung wenn kein json klommt
        pass


# @bp.route('/login', methods=['POST'])
# def login_user():
#     if request.is_json:
#         data = request.get_json()
#         # Username und PW werden in Datenbank gespeichert...
#         username = data['username']
#         password = data['password']
#
#         # öffnet connection zu paps datenbank
#         # con = Connection()
#
#         # Token wird erstellt
#         random_payload = {'Random Payload': 3.14159265358979}
#         token = jwt.encode(random_payload, 'kappa', algorithm="HS256")
#         resp = jsonify({'message': 'Erfolgreich eingeloggd', 'Token': token})
#         return resp
#     else:
#         return jsonify({"error": "Invalid content type, JSON required"}), 400
#
#
# @bp.route('/asking', methods=['POST'])
# def asking():
#     out = request.headers['Authorization']
#     b, token = out.split()
#     return check_token(token)
#
#
# def check_token(token):
#     try:
#         jwt.decode(token, "kappa", algorithms=["HS256"])
#     except jwt.InvalidTokenError:
#         resp = jsonify({"message": "Invalid Token"}), 401
#         return resp
#     # Schreibe in Datenbank oder führe befehle aus
#     return jsonify({"message": "Request performed successfully"})
#
#
# # Beispiel für protected route. Wird anhand des sessiontokens bewertet.
# @app.route('/some_protected_route')
# def protected_route():
#     if 'session_token' in session:
#         return f"Willkommen zurück, {session['username']}!"
#     else:
#         return "Bitte zuerst anmelden", 401
