"""
This script is part of a RESTful API for managing functionalities of oldaplib.
It uses Flask and oldaplib to perform CRUD operations on user, project data, permissionsets and more.
The API offers endpoints for creating, reading, updating, searching and deleting functions to interact with the database.

Available endpoints:
- PUT /admin/user/<userid>: Creates a new user.
- GET /admin/user/<userid>: Reads the data of a user.
- DELETE /admin/user/<userid>: Deletes a user.
- POST /admin/user/<userid>: Modify the data of a user.

The implementation includes error handling and validation for most operations.
"""

from typing import Dict, Set

from flask import jsonify, request, Blueprint
from oldaplib.src.connection import Connection
from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.helpers.observable_set import ObservableSet
from oldaplib.src.helpers.oldaperror import OldapErrorValue, OldapError, OldapErrorAlreadyExists, OldapErrorNotFound, \
    OldapErrorNoPermission, OldapErrorUpdateFailed
from oldaplib.src.user import User
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_string import Xsd_string

user_bp = Blueprint('user', __name__, url_prefix='/admin')


@user_bp.route('/user/<userid>', methods=['PUT'])
def create_user(userid):
    """
    Viewfunction to create a new user. A JSON with the necessary credentials is expected.
    The JSON has the following form:
    json={
        "givenName": "John",
        "familyName": "Doe",
        "password": "nicepw",
        "isActive": True,
        "in_projects": [{
            "permissions": ['oldap:ADMIN_USERS', (...)],
            "project": 'http://www.salsah.org/version/2.0/SwissBritNet'
            }, {...}],
        "has_permissions": ['oldap:GenericView', (...)]
    }
    :param userid: The userid of the useraccount that should be created
    :return: A JSON containing the userIri that has the following form:
    json={"message": f"User {userid} created", "userIri": f"{userid}"}
    """
    known_json_fields = {"givenName", "familyName", "password","isActive", "inProjects", "hasPermissions"}
    mandatory_json_fields = {"givenName", "familyName", "password"}
    # We get a html request with a header that contains a user token as well as a body with a json
    # that contains user information

    try:
        Xsd_NCName(userid)
    except OldapErrorValue as err:
        return jsonify({"message": str(err)}), 400
    out = request.headers['Authorization']
    b, token = out.split()
    if request.is_json:
        data = request.get_json()
        unknown_json_field = set(data.keys()) - known_json_fields
        if unknown_json_field:
            return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to create a user. Usable are {known_json_fields}. Aborded operation"}), 400

        if not mandatory_json_fields.issubset(set(data.keys())):
            return jsonify({"message": f"The Fields {mandatory_json_fields} are required to create a user. Used where {set(data.keys())}. Usablable are {known_json_fields}"}), 400

        try:
            familyname = Xsd_string(data['familyName'])
            givenname = Xsd_string(data['givenName'])
            credentials = Xsd_string(data['password'])
            isActive = data.get('isActive', True)
        except KeyError as error:  # Should not be reachable. Redundancy
            return jsonify({'message': f'Missing field {str(error)}'}), 400

        if not isinstance(isActive, bool):
            return jsonify({'message': 'Invalid input for isActive: must be a bool -- true or false'}), 400

        inprojects = data.get('inProjects', None)
        haspermissions = data.get('hasPermissions', None)

        # If "inproject" is given by the creation json, fill it...
        in_project_dict: Dict[str | Iri, Set[AdminPermission] | ObservableSet[AdminPermission]] = {}
        if inprojects is not None:
            for item in inprojects:
                project_name = item["project"]
                try:
                    if item.get("permissions") is not None:
                        permissions = {AdminPermission(f'oldap:{x}') for x in item["permissions"]}
                    else:
                        permissions = set()
                except ValueError as error:
                    return jsonify({'message': f'The given project project permission is not a valid one'}), 400
                try:
                    in_project_dict[Iri(project_name)] = permissions
                except OldapErrorValue as error:
                    return jsonify({'message': f'The given projectname is not a valid anyIri'}), 400

        # If "haspermissions" is given by the creation json, fill it...
        if haspermissions is not None:
            try:
                permission_set = {Xsd_QName(f'oldap:{x}') for x in haspermissions}
            except OldapErrorValue as error:
                return jsonify({'message': f'The given permission is not a QName'}), 400
        else:
            permission_set = set()

        try:
            con = Connection(server='http://localhost:7200',
                             repo="oldap",
                             token=token,
                             context_name="DEFAULT")
        except OldapError as error:
            return jsonify({"message": f"Connection failed: {str(error)}"}), 403
        try:
            user = User(con=con,
                        userId=userid,
                        familyName=familyname,
                        givenName=givenname,
                        credentials=credentials,
                        inProject=in_project_dict,
                        hasPermissions=permission_set,
                        isActive=isActive)
            user.create()
        except OldapErrorAlreadyExists as error:
            return jsonify({"message": str(error)}), 409
        except OldapErrorValue as error:
            return jsonify({'message': str(error)}), 400
        except OldapError as error:  # Should not be reachable... is only raised when no connection was established
            return jsonify({'message': str(error)}), 500

    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400
    return jsonify({"message": f"User {userid} created", "userIri": f"{userid}"}), 200


@user_bp.route('/user/<userid>', methods=['GET'])
def read_users(userid):
    """
    Viewfunction to retrieve the information about a user.
    :param userid: The userid of the user for that the information should be retrieved.
    :return: A JSON containing the information about the given user. It has the following form:
    json={
    'family_name': 'John',
    'given_name': 'Doe',
    'has_permissions': ['oldap:GenericView', (...)],
    'in_projects': [{
        'permissions': ['oldap:ADMIN_USERS', (...)],
        'project': 'http://www.salsah.org/version/2.0/SwissBritNet'
        }, {...}],
    'isActive': True,
    'userId': 'Jodoe',
    'userIri': 'urn:uuid:5a8fe5ef-90d7-4af8-9ea9-85173e5ee021'
    }
    """
    out = request.headers['Authorization']
    b, token = out.split()

    try:
        con = Connection(server='http://localhost:7200',
                         repo="oldap",
                         token=token,
                         context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    try:
        user = User.read(con=con, userId=userid)
    except OldapErrorNotFound as error:
        return jsonify({"message": f'User {userid} not found'}), 404

    # Building the response json
    answer = {
        "userIri": str(user.userIri),
        "userId": str(user.userId),
        "family_name": str(user.familyName),
        "isActive": bool(user.isActive),
        "given_name": str(user.givenName),
        "in_projects": [],
        "has_permissions": [str(x) for x in user.hasPermissions] if user.hasPermissions else []
    }

    if user.inProject is not None:
        for projname, permissions in user.inProject.items():
            proj = {"project": str(projname), "permissions": [x.value for x in permissions] if permissions else []}
            answer["in_projects"].append(proj)

    return jsonify(answer), 200


@user_bp.route('/user/<userid>', methods=['DELETE'])
def delete_user(userid):
    """
    Viewfunction to delete a user.
    :param userid: The userid of the user that should be deleted.
    :return: A JSON that confirms the deletion of the user that has the following form:
    json={"message": "User {userid} deleted"}
    """
    out = request.headers['Authorization']
    b, token = out.split()

    try:
        con = Connection(server='http://localhost:7200',
                         repo="oldap",
                         token=token,
                         context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    try:
        user = User.read(con=con, userId=userid)
        user.delete()
    except OldapErrorNotFound as error:
        return jsonify({"message": str(error)}), 404
    except OldapErrorNoPermission as error:
        return jsonify({"message": str(error)}), 403

    return jsonify({"message": f"User {userid} deleted"}), 200


@user_bp.route('/user/<userid>', methods=['POST'])
def modify_user(userid):
    """
    Veiwfunction to modify a user. A JSON is expected with the information that should be modified. It has the following
    form:
    json={
        "givenName": "John",
        "familyName": "Doe",
        "password": "nicepw",
        "isActive": True/False
        "in_projects": [
            {
            "project": 'http://www.salsah.org/version/2.0/SwissBritNet'
            "permissions": ['oldap:ADMIN_USERS', (...)] or
                {
                "add": ["oldap:GenericView", (...)],
                "del": ["oldap:GenericView", (...)]
                }
            }, {...}
        ],
        "has_permissions": ['oldap:GenericView', (...)] or {
        "add": ["oldap:GenericView", (...)],
        "del": ["oldap:GenericView", (...)]
        }
    }
    :param userid: The userid of the user that should be modified.
    :return: A JSON to denote the success of the operation that has the following form:
    json={"message": "User updated successfully"}
    """
    known_json_fields = {"givenName", "familyName", "password", "inProjects", "hasPermissions", "isActive"}
    out = request.headers['Authorization']
    b, token = out.split()

    if request.is_json:
        data = request.get_json()
        unknown_json_field = set(data.keys()) - known_json_fields
        if unknown_json_field:
            return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to modify a user. Usable are {known_json_fields}. Aborded operation"}), 400
        if not set(data.keys()):
            return jsonify({"message": f"At least one field must be given to modify the project. Usablable for the modify-viewfunction are {known_json_fields}"}), 400
        firstname = data.get("givenName", None)
        lastname = data.get("familyName", None)
        password = data.get("password", None)
        inprojects = data.get('inProjects', "NotSent")
        haspermissions = data.get('hasPermissions', "NotSent")
        isactive = data.get('isActive', None)

        try:
            con = Connection(server='http://localhost:7200',
                             repo="oldap",
                             token=token,
                             context_name="DEFAULT")
        except OldapError as error:
            return jsonify({"message": f"Connection failed: {str(error)}"}), 403

        try:
            user = User.read(con=con, userId=Xsd_NCName(userid))  # read the user from the triple store
        except OldapErrorNotFound as error:
            return jsonify({"message": str(error)}), 404

        if inprojects == []:
            return jsonify({"message": "If you want to modify a project pls send the projectIri that should be modifiead as well as the desired changes"}), 400
        if inprojects is None:
            user.inProject = None
        elif inprojects != "NotSent":
            if not (isinstance(inprojects, list) or isinstance(inprojects, dict)):
                return jsonify({"message": f"Either a List or a dict is expected for a modify request."}), 400
            for newproject in inprojects:
                if "project" not in newproject:
                    return jsonify({"message": "The project-field is missing in the request"}), 400
                if newproject["project"] == "":
                    return jsonify({"message": "The Name of the permissionset is missing"}), 400
                try:
                    if Iri(newproject["project"]) in user.inProject:
                        if "permissions" not in newproject:
                            return jsonify({"message": "The Permissions are missing for the project"}), 400
                        if newproject["permissions"] is None:
                            user.inProject[Iri(newproject["project"])] = None
                        elif isinstance(newproject["permissions"], list):
                            user.inProject[Iri(newproject["project"])] = {AdminPermission(f'oldap:{x}') for x in newproject["permissions"]}
                        elif isinstance(newproject["permissions"], dict):
                            if "add" in newproject["permissions"]:
                                if not isinstance(newproject["permissions"]["add"], list):
                                    return jsonify({"message": f"The add entry needs to be a list, not a string."}), 400
                                for item in newproject["permissions"]["add"]:
                                    user.inProject[newproject["project"]].add(AdminPermission(f'oldap:{item}'))
                            if "del" in newproject["permissions"]:
                                if not isinstance(newproject["permissions"]["del"], list):
                                    return jsonify({"message": f"The del entry needs to be a list, not a string."}), 400
                                for item in newproject["permissions"]["del"]:
                                    user.inProject[newproject["project"]].remove(AdminPermission(f'oldap:{item}'))
                        else:
                            return jsonify({"message": f"Either a list or a dict is expected for the content of the permissions field"}), 400
                    else:
                        return jsonify({"message": f"Project '{newproject["project"]}' to modify does not exist"}), 404
                except ValueError as error:
                    return jsonify({"message": str(error)}), 400
                except KeyError as error:
                    return jsonify({"message": f'The permission {item} is not present in the database'}), 404
                except OldapErrorValue as error:
                    return jsonify({"message": str(error)}), 400

        permission_set = None  # only needed if a list is sent
        try:
            if haspermissions != "NotSent":
                if isinstance(haspermissions, str):
                    return jsonify({"message": f"For the permissionset either a list or a dict is expected, not a string"}), 400
                if isinstance(haspermissions, list):
                    permission_set = set()
                    for item in haspermissions:
                        permission_set.add(Iri(f'oldap:{item}'))
                elif isinstance(haspermissions, dict):
                    if "add" in haspermissions:
                        if not isinstance(haspermissions["add"], list):
                            return jsonify({"message": f"The add entry needs to be a list, not a string."}), 400
                        for item in haspermissions["add"]:
                            user.hasPermissions.add(Iri(f'oldap:{item}'))
                    if "del" in haspermissions:
                        if not isinstance(haspermissions["del"], list):
                            return jsonify({"message": f"The delete entry needs to be a list, not a string."}), 400
                        for item in haspermissions["del"]:
                            try:
                                user.hasPermissions.remove(Iri(f'oldap:{item}'))
                            except AttributeError as error:
                                return jsonify({"message": f"The Element {item} does not exist and thus cant be deleted"}), 404
                    if "add" not in haspermissions and "del" not in haspermissions:
                        return jsonify({"message": f"The sended command (keyword in dict) is not known"}), 400
                elif haspermissions is None:
                    del user.hasPermissions
                else:
                    return jsonify({"message": f"Either a List or a dict is required."}), 400
        except OldapErrorValue as error:
            return jsonify({'message': f'The given permission is not a QName'}), 400

        if firstname:
            user.givenName = Xsd_string(firstname)
        if lastname:
            user.familyName = Xsd_string(lastname)
        if password:
            user.credentials = Xsd_string(password)
        if isactive is not None:
            if not isinstance(isactive, bool):
                return jsonify({'message': f'isActive needs to be a bool -- einter true or false'}), 400
            else:
                user.isActive = Xsd_boolean(isactive)
        if permission_set:
            user.hasPermissions = permission_set
        if permission_set == set():
            user.hasPermissions = set()

        try:
            user.update()
        except OldapErrorUpdateFailed as error:  # hard to test
            return jsonify({"message": str(error)}), 500
        except OldapErrorValue as error:
            return jsonify({"message": str(error)}), 404
        except OldapErrorNoPermission as error:
            return jsonify({"message": str(error)}), 403
        except OldapError as error:  # should not be reachable
            return jsonify({"message": str(error)}), 500

        return jsonify({"message": "User updated successfully"}), 200

    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400
