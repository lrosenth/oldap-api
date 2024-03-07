from typing import Dict, Set

import jwt
from flask import Blueprint, request, jsonify
from omaslib.src.connection import Connection
from omaslib.src.enums.permissions import AdminPermission
from omaslib.src.helpers.datatypes import AnyIRI, NCName, QName
from omaslib.src.helpers.observable_set import ObservableSet
from omaslib.src.helpers.omaserror import OmasError
from omaslib.src.in_project import InProjectClass
from omaslib.src.user import User

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.route('/hello', methods=['GET'])
def hello():
    return 'hello world!'

# Function to log into a user
@bp.route('/auth', methods=['GET', 'POST'])
def login():
    if request.is_json:
        data = request.get_json()
        username = data['userid']
        password = data['password']
        try:
            con = Connection(server='http://localhost:7200',
                             repo="omas",
                             userId=username,
                             credentials=password,
                             context_name="DEFAULT")
            resp = jsonify({'message': 'Login succeeded', 'token': con.token})
            return resp
        except OmasError as err:
            return jsonify({'message': str(err)}), 401
    else:
        return jsonify({"error": "Invalid content type, JSON required"}), 400


# Function to create a user
@bp.route('/user/<userid>', methods=['PUT'])
def create_user(userid):
    # We get a html request with a header that contains a user token as well as a body with a json
    # that contains user information
    # TODO: Check for optional fields... Firstname, Lastname und Passwort sind necessary, rest ist optional
    # TODO: All responses need to be the same as in the yaml file described
    # TODO: die "has_permissions" muss auch noch per json übergeben werden können
    out = request.headers['Authorization']
    b, token = out.split()
    if request.is_json:
        data = request.get_json()
        try:
            familyname = str(data['familyName'])
            givenname = str(data['givenName'])
            credentials = str(data['password'])
        except KeyError:
            # ToDo: Missing field - error message
            pass

        inprojects = data.get('inProjects', None)
        haspermissions = data.get('hasPermissions', None)

        # If "inproject" is given by the creation json, fill it...
        in_project_dict: Dict[str | QName | AnyIRI, Set[AdminPermission] | ObservableSet[AdminPermission]] = {}
        if inprojects is not None:
            for item in inprojects:
                project_name = item["project"]
                permissions = {AdminPermission(f'omas:{x}') for x in item["permissions"]}  # TODO AdminPermission kann eine fehlermeldung geben wenn x nicht richtig ist
                in_project_dict[AnyIRI(project_name)] = permissions

        if haspermissions is not None:
            permission_set = {QName(f'omas:{x}') for x in haspermissions}
        else:
            permission_set = None

        try:
            con = Connection(server='http://localhost:7200',
                             repo="omas",
                             token=token,
                             context_name="DEFAULT")
            user = User(con=con,
                        userId=NCName(userid),
                        familyName=familyname,
                        givenName=givenname,
                        credentials=credentials,
                        inProject=in_project_dict,
                        hasPermissions=permission_set)  # TODO: Wie löst man hier, dass haspermissions optional sein kann? -> am anfang auf none initiieren // TODO: hasPermissions durchiterieren
            print(str(user))
            user.create()
        except OmasError as error:
            print("=====>", error)
            return "Failure!!!!!!!!!!!!"
    else:
        return jsonify({"message": "JSON expected. Instead received {request.content_type}"}), 400
    return "User Created!!"


# Function to read the contents of a user
@bp.route('/user/<userid>', methods=['GET'])
def read_users(userid):

    # TODO: Was kommt zurück wenn optional nicht definiert ist??? -> leerer array
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
        "userIri": str(user.userIri),
        "userId": str(user.userId),
        "family_name": str(user.familyName),
        "given_name": str(user.givenName),
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
    # TODO: Fehlerbehandlung wenn user nicht existiert
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
        firstname = data.get("givenName", None)
        lastname = data.get("familyName", None)
        password = data.get("password", None)
        inprojects = data.get('inProjects', None)
        haspermissions = data.get('hasPermissions', None)

        in_project_dict: Dict[str | QName | AnyIRI, Set[AdminPermission] | ObservableSet[AdminPermission]] = {}

        if inprojects is not None:
            for item in inprojects:
                project_name = item["project"]
                permissions = {AdminPermission(f'omas:{x}') for x in item["permissions"]}  # TODO AdminPermission kann eine fehlermeldung geben wenn x nicht den zulässigen strings (adminoldap use) entspricht
                in_project_dict[QName(project_name)] = permissions

        permission_set = None
        if haspermissions is not None:
            permission_set = {QName(f'omas:{x}') for x in haspermissions}

        con = Connection(server='http://localhost:7200',
                         repo="omas",
                         token=token,
                         context_name="DEFAULT")

        user2 = User.read(con=con, userId=userid)  # read the user from the triple store

        if firstname:
            user2.givenName = firstname
        if lastname:
            user2.familyName = lastname
        if password:
            user2.credentials = password
        if in_project_dict:
            user2.inProject = InProjectClass(in_project_dict)
        if permission_set:
            user2.hasPermissions = permission_set

        try:
            user2.update()
        except Exception as e:
            print("=====>", e)

        return "user updated"
