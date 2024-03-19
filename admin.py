from typing import Dict, Set

import jwt
from flask import Blueprint, request, jsonify
from omaslib.src.connection import Connection
from omaslib.src.enums.permissions import AdminPermission
from omaslib.src.helpers.datatypes import AnyIRI, NCName, QName
from omaslib.src.helpers.observable_set import ObservableSet
from omaslib.src.helpers.omaserror import OmasError, OmasErrorNotFound, OmasErrorAlreadyExists, OmasErrorValue
from omaslib.src.in_project import InProjectClass
from omaslib.src.user import User

bp = Blueprint('admin', __name__, url_prefix='/admin')


# Function to log into a user
@bp.route('/auth/<userid>', methods=['POST'])
def login(userid):
    if request.is_json:
        data = request.get_json()
        password = data.get('password')
        if password is None:
            return jsonify({"message": "Invalid content type, JSON required"}), 400
        try:
            con = Connection(server='http://localhost:7200',
                             repo="omas",
                             userId=userid,
                             credentials=password,
                             context_name="DEFAULT")
            resp = jsonify({'message': 'Login succeeded', 'token': con.token})
            return resp
        except OmasErrorNotFound as err:
            return jsonify({'message': str(err)}), 404
        except OmasError as err:
            return jsonify({'message': str(err)}), 401
    else:
        return jsonify({"message": "Invalid content type, JSON required"}), 400


@bp.route('/auth/<userid>', methods=['DELETE'])
def logout(userid):
    #
    # TODO: how to make a logout??? OMASLIB does not yet have a solution! So we just return 200
    return '', 200


# Function to create a user
@bp.route('/user/<userid>', methods=['PUT'])
def create_user(userid):
    # We get a html request with a header that contains a user token as well as a body with a json
    # that contains user information
    out = request.headers['Authorization']
    b, token = out.split()
    if request.is_json:
        data = request.get_json()
        try:
            familyname = str(data['familyName'])
            givenname = str(data['givenName'])
            credentials = str(data['password'])
        except KeyError as error:
            return jsonify({'message': f'Missing field {str(error)}'}), 400

        inprojects = data.get('inProjects', None)
        haspermissions = data.get('hasPermissions', None)

        # If "inproject" is given by the creation json, fill it...
        in_project_dict: Dict[str | QName | AnyIRI, Set[AdminPermission] | ObservableSet[AdminPermission]] = {}
        if inprojects is not None:
            for item in inprojects:
                project_name = item["project"]
                try:
                    if item.get("permissions") is not None:
                        permissions = {AdminPermission(f'omas:{x}') for x in item["permissions"]}
                    else:
                        permissions = set()
                except ValueError as error:
                    return jsonify({'message': f'The given project project permission is not a valid one'}), 400
                try:
                    in_project_dict[AnyIRI(project_name)] = permissions
                except OmasErrorValue as error:
                    return jsonify({'message': f'The given projectname is not a valid anyIri'}), 400

        # If "haspermissions" is given by the creation json, fill it...
        if haspermissions is not None:
            try:
                permission_set = {QName(f'omas:{x}') for x in haspermissions}
            except OmasErrorValue as error:
                return jsonify({'message': f'The given permission is not a QName'}), 400
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
                        hasPermissions=permission_set)
            user.create()
        except OmasErrorAlreadyExists as error:
            return jsonify({"message": str(error)}), 409
        except OmasErrorValue as error:
            return jsonify({'message': str(error)}), 400

    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400
    return jsonify({"message": f"User {userid} created", "userIri": f"{userid}"})


# Function to read the contents of a user
@bp.route('/user/<userid>', methods=['GET'])
def read_users(userid):

    # TODO: Was kommt zurück wenn optional nicht definiert ist??? -> leerer array
    out = request.headers['Authorization']
    b, token = out.split()

    try:
        con = Connection(server='http://localhost:7200',
                         repo="omas",
                         token=token,
                         context_name="DEFAULT")
    except OmasError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"})

    try:
        user = User.read(con=con, userId=userid)
    except OmasErrorNotFound as error:
        return jsonify({"message": f'User {userid} not found'}), 404

    # TODO: Abfangen, dass in projects und has permissions empty sein könnten!!
    # Building the response json
    answer = {
        "userIri": str(user.userIri),
        "userId": str(user.userId),
        "family_name": str(user.familyName),
        "given_name": str(user.givenName),
        "in_projects": [],
        "has_permissions": [str(x) for x in user.hasPermissions] if user.hasPermissions else []
    }

    for projname, permissions in user.inProject.items():
        proj = {"project": str(projname), "permissions": [x.value for x in permissions] if permissions else []}
        answer["in_projects"].append(proj)

    return jsonify(answer)


# Function to delete a user
@bp.route('/user/<userid>', methods=['DELETE'])
def delete_user(userid):
    
    out = request.headers['Authorization']
    b, token = out.split()

    try:
        con = Connection(server='http://localhost:7200',
                         repo="omas",
                         token=token,
                         context_name="DEFAULT")
    except OmasError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"})

    try:
        user3 = User.read(con=con, userId=userid)
        user3.delete()
    except OmasErrorNotFound as error:
        return jsonify({"message": str(error)})

    return jsonify({"message": f"User {userid} deleted"})


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
