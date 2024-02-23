from typing import Dict, Set

import jwt
from flask import Blueprint, request, jsonify
from omaslib.src.connection import Connection
from omaslib.src.helpers.datatypes import AnyIRI, NCName, QName
from omaslib.src.helpers.observable_set import ObservableSet
from omaslib.src.helpers.omaserror import OmasError
from omaslib.src.helpers.permissions import AdminPermission
from omaslib.src.user import User

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

@bp.route('/user/<userid>', methods=['PUT'])
def create_user(userid):
    # We get a html request with a header that contains a user token as well as a body with a json
    # that contains user information
    # TODO: Check for optional fields
    out = request.headers['Authorization']
    b, token = out.split()
    if request.is_json:
        data = request.get_json()
        userid = data['NCName']
        familyname = data['lastname']
        givenname = data['firstname']
        credentials = data['password']
        inproject = data['in_projects']

        in_project_dict: Dict[str | QName | AnyIRI, Set[AdminPermission] | ObservableSet[AdminPermission]] = {}
        for item in inproject:
            project_name = item["project"]
            permissions = {AdminPermission(x) for x in item["permissions"]}
            in_project_dict[AnyIRI(project_name)] = permissions

        try:
            con = Connection(server='http://localhost:7200',
                             repo="omas",
                             token=token,
                             context_name="DEFAULT")
            user = User(con=con,
                        userId=NCName(userid),
                        family_name=familyname,
                        given_name=givenname,
                        credentials=credentials,
                        inProject=in_project_dict,
                        hasPermissions={QName('omas:GenericView')})
            user.create()
        except OmasError as error:
            print(error)
    return "User Created!!"
# @bp.route('/user/<userid>', methods=['GET'])
# def read_users(userid):
#     # hier das Token aus dem Header auslesen!
#
#     con = Connection(server='http://localhost:7200',
#                      repo="omas",
#                      token=token,
#                      context_name="DEFAULT")
#
#     # Das hier ist dann die Read Anfrage!
#     user = User.read(con=self._connection, userId="rosenth")
