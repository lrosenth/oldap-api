from typing import Dict, Set

import jwt
from flask import Blueprint, request, jsonify
from omaslib.src.connection import Connection
from omaslib.src.dtypes.namespaceiri import NamespaceIRI
from omaslib.src.enums.permissions import AdminPermission
from omaslib.src.helpers.langstring import LangString
from omaslib.src.helpers.observable_set import ObservableSet
from omaslib.src.helpers.omaserror import OmasError, OmasErrorNotFound, OmasErrorAlreadyExists, OmasErrorValue, \
    OmasErrorUpdateFailed
from omaslib.src.helpers.tools import str2qname_anyiri
from omaslib.src.in_project import InProjectClass
from omaslib.src.project import Project
from omaslib.src.user import User
from omaslib.src.xsd.iri import Iri
from omaslib.src.xsd.xsd_anyuri import Xsd_anyURI
from omaslib.src.xsd.xsd_date import Xsd_date
from omaslib.src.xsd.xsd_ncname import Xsd_NCName
from omaslib.src.xsd.xsd_qname import Xsd_QName
from omaslib.src.xsd.xsd_string import Xsd_string

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
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400


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
    try:
        Xsd_NCName(userid)
    except OmasErrorValue as err:
        print("in Except")
        return jsonify({"message": str(err)}), 400
    out = request.headers['Authorization']
    b, token = out.split()
    if request.is_json:
        data = request.get_json()
        try:
            familyname = Xsd_string(data['familyName'])
            givenname = Xsd_string(data['givenName'])
            credentials = Xsd_string(data['password'])
        except KeyError as error:
            return jsonify({'message': f'Missing field {str(error)}'}), 400

        inprojects = data.get('inProjects', None)
        haspermissions = data.get('hasPermissions', None)

        # If "inproject" is given by the creation json, fill it...
        in_project_dict: Dict[str | Iri, Set[AdminPermission] | ObservableSet[AdminPermission]] = {}
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
                    in_project_dict[Iri(project_name)] = permissions
                except OmasErrorValue as error:
                    return jsonify({'message': f'The given projectname is not a valid anyIri'}), 400

        # If "haspermissions" is given by the creation json, fill it...
        if haspermissions is not None:
            try:
                permission_set = {Xsd_QName(f'omas:{x}') for x in haspermissions}
            except OmasErrorValue as error:
                return jsonify({'message': f'The given permission is not a QName'}), 400
        else:
            permission_set = set()

        try:
            con = Connection(server='http://localhost:7200',
                             repo="omas",
                             token=token,
                             context_name="DEFAULT")
            user = User(con=con,
                        userId=userid,
                        familyName=familyname,
                        givenName=givenname,
                        credentials=credentials,
                        inProject=in_project_dict,
                        hasPermissions=permission_set,
                        isActive=True)
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
        return jsonify({"message": f"Connection failed: {str(error)}"}), 401

    try:
        user = User.read(con=con, userId=userid)
    except OmasErrorNotFound as error:
        return jsonify({"message": f'User {userid} not found'}), 404

    # TODO: Abfangen, dass in projects und has permissions empty sein könnten!!
    # Building the response json
    answer = {
        "userIri": Iri(user.userIri),
        "userId": str(user.userId),
        "family_name": Iri(user.familyName),
        "given_name": Iri(user.givenName),
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
        return jsonify({"message": f"Connection failed: {str(error)}"}), 401

    try:
        user3 = User.read(con=con, userId=userid)
        user3.delete()
    except OmasErrorNotFound as error:
        return jsonify({"message": str(error)})

    return jsonify({"message": f"User {userid} deleted"})


# Function to alter/modify a user
@bp.route('/user/<userid>', methods=['POST'])
def modify_user(userid):
    # TODO: Modify isActive
    out = request.headers['Authorization']
    b, token = out.split()

    if request.is_json:
        data = request.get_json()
        firstname = data.get("givenName", None)
        lastname = data.get("familyName", None)
        password = data.get("password", None)
        inprojects = data.get('inProjects', None)
        haspermissions = data.get('hasPermissions', None)

        if firstname is None and lastname is None and password is None and inprojects is None and haspermissions is None:
            return jsonify({"message": "Either the firstname, lastname, password, inProjects or hasPermissions needs to be modified"}), 400

        in_project_dict: Dict[str | Iri, Set[AdminPermission] | ObservableSet[AdminPermission]] = {}

        if inprojects is not None:
            for item in inprojects:
                project_name = item["project"]

                if item.get("permissions") is not None:
                    try:
                        permissions = {AdminPermission(f'omas:{x}') for x in item["permissions"]}
                    except ValueError as error:
                        return jsonify({'message': f'The given project permission is not a valid one'}), 400
                else:
                    permissions = set()
                try:
                    in_project_dict[Iri(project_name)] = permissions
                except OmasErrorValue as error:
                    return jsonify({'message': f'The given projectname is not a valid anyIri'}), 400

        if haspermissions is not None:
            try:
                permission_set = {Iri(f'omas:{x}') for x in haspermissions}
            except OmasErrorValue as error:
                return jsonify({'message': f'The given permission is not a QName'}), 400
        else:
            permission_set = None

        try:
            con = Connection(server='http://localhost:7200',
                             repo="omas",
                             token=token,
                             context_name="DEFAULT")
        except OmasError as error:
            return jsonify({"message": f"Connection failed: {str(error)}"})

        try:
            user2 = User.read(con=con, userId=Xsd_NCName(userid))  # read the user from the triple store
        except OmasErrorNotFound as error:
            return jsonify({"message": str(error)})

        if firstname:
            user2.givenName = Xsd_string(firstname)
        if lastname:
            user2.familyName = Xsd_string(lastname)
        if password:
            user2.credentials = Xsd_string(password)
        if in_project_dict:
            user2.inProject = InProjectClass(in_project_dict)
        if in_project_dict == {}:
            user2.inProject = InProjectClass()
        if permission_set:
            user2.hasPermissions = permission_set
        if permission_set == set():
            user2.hasPermissions = set()

        try:
            user2.update()
        except OmasErrorUpdateFailed as error:
            return jsonify({"message": str(error)})
        except OmasErrorValue as error:
            return jsonify({"message": str(error)})
        except OmasError as error:
            return jsonify({"message": str(error)})

        return jsonify({"message": "User updated successfully"}), 200

    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400


@bp.route('/project/<projectid>', methods=['POST'])
def create_project(projectid):

    out = request.headers['Authorization']
    b, token = out.split()

    if request.is_json:
        data = request.get_json()
        projectIri = data.get("projectIri", None)
        projectShortName = projectid  # Necessary
        label = data.get("label", None)  # Necessary
        comment = data.get('comment', None)  # Necessary
        namespaceIri = data.get('namespaceIri', None)  # Necessary
        projectStart = data.get('projectStart', None)
        projectEnd = data.get('projectEnd', None)

        if label is None or comment is None or namespaceIri is None:
            return jsonify({"message": f"To create a project, at least the projectshortname, label, comment and namespaceIri are required"}), 400

        try:
            con = Connection(server='http://localhost:7200',
                             repo="omas",
                             token=token,
                             context_name="DEFAULT")

            project = Project(con=con,
                              projectShortName=projectShortName,
                              label=label,
                              namespaceIri=NamespaceIRI(namespaceIri),
                              comment=LangString(comment),
                              projectStart=Xsd_date(projectStart),
                              projectEnd=Xsd_date(projectEnd)
                              )
            project.create()

        except OmasErrorValue as error:
            return jsonify({'message': str(error)}), 400
        except OmasError as error:
            return jsonify({'message': str(error)})
        except Exception as error:  # TODO: Way to generic -- Debugging purposes. DELETE THIS EXCEPTION!!
            return jsonify({'message': str(error)})

        return jsonify({"message": "Project successfully created"}), 200
    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400


# @bp.route('/project/<projectid>', methods=['DELETE'])
# def create_project(projectid):
#
#     out = request.headers['Authorization']
#     b, token = out.split()
#
#     try:
#         con = Connection(server='http://localhost:7200',
#                          repo="omas",
#                          token=token,
#                          context_name="DEFAULT")
#
#         project = Project.read(con=con, projectIri=projectIri)
#         project.delete()
#     except OmasErrorValue as error:
#         pass
#






