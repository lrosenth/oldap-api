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


# Function to log into a user
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

# Function to create a user
@bp.route('/user/<userid>', methods=['PUT'])
def create_user(userid):
    # We get a html request with a header that contains a user token as well as a body with a json
    # that contains user information
    # TODO: Check for optional fields... Firstname, Lastname und Passwort sind necessary, rest ist optional

    # TODO: die "has_permissions" muss auch noch per json übergeben werden können
    out = request.headers['Authorization']
    b, token = out.split()
    if request.is_json:
        data = request.get_json()
        userid = data.get('NCName', None)  # TODO: Ist userid wirklich optional?
        familyname = data['lastname']
        givenname = data['firstname']
        credentials = data['password']
        inproject = data.get('in_projects', None)

        # If "inproject" is given by the creation json, fill it...
        if inproject is not None:
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
                        hasPermissions={QName('omas:GenericView')})  # TODO: Wie löst man hier, dass haspermissions optional sein kann?
            user.create()
        except OmasError as error:
            print(error)
    return "User Created!!"


# Function to read the contents of a user
@bp.route('/user/<userid>', methods=['GET'])
def read_users(userid):

    # TODO: Was kommt zurück wenn optional nicht definiert ist???
    out = request.headers['Authorization']
    b, token = out.split()

    con = Connection(server='http://localhost:7200',
                     repo="omas",
                     token=token,
                     context_name="DEFAULT")

    # Das hier ist dann die Read Anfrage!
    user = User.read(con=con, userId=userid)

    # Building the response json
    answer = {
        "useriri": str(user.userIri),
        "userid": str(user.userId),
        "lastname": str(user.familyName),
        "firstname": str(user.givenName),
        "in_projects": [],
        "has_permissions": [str(x) for x in user.hasPermissions]
    }

    for projname, permissions in user.inProject.items():
        proj = {"project": str(projname), "permissions": [x.value for x in permissions]}
        answer["in_projects"].append(proj)

    return jsonify(answer)


# Function to delete a user
@bp.route('/user/<userid>', methods=['DELETE'])
def delete_user(userid):

    out = request.headers['Authorization']
    b, token = out.split()

    con = Connection(server='http://localhost:7200',
                     repo="omas",
                     token=token,
                     context_name="DEFAULT")

    user3 = User.read(con=con, userId=userid)
    user3.delete()

    return "user deleted"


# Function to alter/modify a user
@bp.route('/user/<userid>', methods=['POST'])
def modify_user(userid):

    out = request.headers['Authorization']
    b, token = out.split()

    if request.is_json:
        data = request.get_json()
        firstname = data.get("firstname", None)
        lastname = data.get("lastname", None)
        password = data.get("password", None)
        in_project = data.get("in_project", None)
        has_permissions = data.get("has_permissions", None)

        con = Connection(server='http://localhost:7200',
                         repo="omas",
                         token=token,
                         context_name="DEFAULT")

        user2 = User.read(con=con, userId=userid)  # read the user from the triple store

        if firstname is not None:
            user2.givenName = firstname
        if lastname is not None:
            user2.familyName = lastname
        if password is not None:
            user2.credentials = password
        if in_project is not None:
            user2.in_project = in_project
        if has_permissions is not None:
            user2.has_permissions = has_permissions

        user2.update()

        return "user updated"
