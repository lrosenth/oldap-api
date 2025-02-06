"""
This script is part of a RESTful API for managing functionalities of oldaplib.
It uses Flask and oldaplib to perform CRUD operations on user, project data, permissionsets and more.
The API offers endpoints for creating, reading, updating, searching and deleting functions to interact with the database.

Available endpoints:
- POST /admin/auth/<userid>: Logs in a user and returns a token.
- DELETE /admin/auth/<userid>: Logs out a user.

The implementation includes error handling and validation for most operations.
"""

from flask import request, jsonify, Blueprint
from oldaplib.src.connection import Connection
from oldaplib.src.helpers.oldaperror import OldapErrorNotFound, OldapError

auth_bp = Blueprint('auth', __name__, url_prefix='/admin')


@auth_bp.route('/auth/<userid>', methods=['POST'])
def login(userid):
    """
    Viewfunction to log into a user. A JSON is expected with the password. The userid is given via the URL parameter.
    The JSON that needs to be provided has the following form: json={'password': '*******'}
    :param userid: The userid of the loginaccount.
    :return: A JSON with the token that has the following form:
    json={'message': 'Login succeeded', 'token': token}
    """
    if request.is_json:
        data = request.get_json()
        password = data.get('password')
        if password is None:
            return jsonify({"message": "Invalid content type, JSON required"}), 400
        try:
            con = Connection(server='http://localhost:7200',
                             repo="oldap",
                             userId=userid,
                             credentials=password,
                             context_name="DEFAULT")
            resp = jsonify({'message': 'Login succeeded', 'token': con.token}), 200
            return resp
        except OldapErrorNotFound as err:
            return jsonify({'message': str(err)}), 404
        except OldapError as error:
            return jsonify({"message": f"Connection failed: {str(error)}"}), 403
    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400


@auth_bp.route('/auth/<userid>', methods=['DELETE'])
def logout(userid):
    """
    Viewfunction to log out of a user.
    :param userid: The userid of the logout account.
    :return:
    """
    # TODO: how to make a logout??? oldaplib does not yet have a solution! So we just return 200
    return '', 200
