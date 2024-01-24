import jwt
from flask import Blueprint, request, jsonify
from omaslib.src.connection import Connection
from omaslib.src.helpers.omaserror import OmasError

bp = Blueprint('admin', __name__, url_prefix='/admin')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.is_json:
        data = request.get_json()
        username = data['userid']
        password = data['password']
        try:
            con = Connection(server='http://localhost:7200',
                             repo="omas",
                             userid=username,
                             credentials=password,
                             context_name="DEFAULT")
            resp = jsonify({'message': 'Erfolgreich eingeloggd', 'Token': con.token})
            return resp
        except OmasError:
            pass
    else:
        return jsonify({"error": "Invalid content type, JSON required"}), 400
