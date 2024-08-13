"""
This script provides a RESTful API for managing users and projects and permissionsets.
It uses Flask and oldaplib to perform CRUD operations on user, project data and permissionsets.
The API offers endpoints for creating, reading, updating, searching and deleting users, projects nad permissionsets.

Available endpoints:
- POST /admin/auth/<userid>: Logs in a user and returns a token.
- DELETE /admin/auth/<userid>: Logs out a user.
- PUT /admin/user/<userid>: Creates a new user.
- GET /admin/user/<userid>: Reads the data of a user.
- DELETE /admin/user/<userid>: Deletes a user.
- POST /admin/user/<userid>: Updates the data of a user.
- PUT /admin/project/<projectid>: Creates a new project.
- GET /admin/project/<projectid>: Reads the data of a project.
- DELETE /admin/project/<projectid>: Deletes a project.
- POST /admin/project/<projectid>: Updates the data of a project.
- PUT /admin/permissionset/<permissionsetid>: Creates a new permission set.
- GET /admin/permissionset/<permissionlabel>: Reads the data of a permission set.
- DELETE /admin/permissionset/<permissionlabel>: Deletes a permission set.
- GET /admin/permissionset/search: Searches for permission sets.

The implementation includes error handling and validation for most operations.
"""
from pprint import pprint
from typing import Dict, Set
from flask import Blueprint, request, jsonify
from oldaplib.src.connection import Connection
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.enums.language import Language
from oldaplib.src.enums.permissions import AdminPermission, DataPermission
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.observable_set import ObservableSet
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorNotFound, OldapErrorAlreadyExists, OldapErrorValue, \
    OldapErrorUpdateFailed, OldapErrorNoPermission, OldapErrorInconsistency
from oldaplib.src.in_project import InProjectClass
from oldaplib.src.permissionset import PermissionSet
from oldaplib.src.project import Project
from oldaplib.src.user import User
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_date import Xsd_date
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_string import Xsd_string
from languages import known_languages

bp = Blueprint('admin', __name__, url_prefix='/admin')


# Function to log into a user
@bp.route('/auth/<userid>', methods=['POST'])
def login(userid):
    """
    Viewfunction to log into a user. A JSON is expected with the password. The userid is given via the URL parameter.
    The JSON that needs to be provided has the following form: json={'password': 'RioGrande'}
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


@bp.route('/auth/<userid>', methods=['DELETE'])
def logout(userid):
    """
    Viewfunction to log out of a user.
    :param userid: The userid of the logout account.
    :return:
    """
    # TODO: how to make a logout??? oldaplib does not yet have a solution! So we just return 200
    return '', 200


# Function to create a user
@bp.route('/user/<userid>', methods=['PUT'])
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


# Function to read the contents of a user
@bp.route('/user/<userid>', methods=['GET'])
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


# Function to delete a user
@bp.route('/user/<userid>', methods=['DELETE'])
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


@bp.route('/user/<userid>', methods=['POST'])
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


@bp.route('/project/<projectid>', methods=['PUT'])
def create_project(projectid):
    """
    Viewfunction to create a new project. A JSON is expectet that contains the necessary information to create a new
    project that has the following form:
    json={
        "projectIri": "http://unittest.org/project/testproject",
        "label": ["unittest@en", "unittest@de"], or "unittest@en"
        "comment": ["For testing@en", "Für Tests@de"], or "For testing@en"
        "namespaceIri": "http://unitest.org/project/unittest#",
        "projectStart": "1993-04-05",
        "projectEnd": "2000-01-10"
    }
    :param projectid: The projectid (nikname/shortname) for the new project.
    :return: A JSON to denote the success of the operation that has the following form:
    json={"message": "Project successfully created"}
    """
    known_json_fields = {"projectIri", "label", "comment", "namespaceIri", "projectStart", "projectEnd"}
    mandatory_json_fields = {"namespaceIri"}
    out = request.headers['Authorization']
    b, token = out.split()

    if request.is_json:
        data = request.get_json()
        unknown_json_field = set(data.keys()) - known_json_fields
        if unknown_json_field:
            return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to create a project. Usable are {known_json_fields}. Aborded operation"}), 400
        projectIri = data.get("projectIri", None)
        projectShortName = projectid
        label = data.get("label", None)
        comment = data.get('comment', None)
        namespaceIri = data.get('namespaceIri', None)
        projectStart = data.get('projectStart', None)
        projectEnd = data.get('projectEnd', None)

        if not mandatory_json_fields.issubset(set(data.keys())):
            return jsonify({"message": f"The Fields {mandatory_json_fields} are required to create a user. Used where {set(data.keys())}. Usablable are {known_json_fields}"}), 400
        if label == [] or comment == []:
            return jsonify({"message": f"A meaningful label and comment need to be provided and can not be empty"}), 400
        try:
            con = Connection(server='http://localhost:7200',
                             repo="oldap",
                             token=token,
                             context_name="DEFAULT")
        except OldapError as error:
            return jsonify({"message": f"Connection failed: {str(error)}"}), 403
        try:
            project = Project(con=con,
                              projectShortName=Xsd_NCName(projectShortName),
                              projectIri=Iri(projectIri),
                              label=LangString(label),
                              namespaceIri=NamespaceIRI(namespaceIri),
                              comment=LangString(comment),
                              projectStart=Xsd_date(projectStart) if projectEnd else None,
                              projectEnd=Xsd_date(projectEnd) if projectEnd else None
                              )
            project.create()
        except OldapErrorNoPermission as error:
            return jsonify({'message': str(error)}), 403
        except OldapErrorAlreadyExists as error:
            return jsonify({'message': str(error)}), 409
        except OldapErrorInconsistency as error:  # inconsistent start and enddate
            return jsonify({'message': str(error)}), 400
        except OldapErrorValue as error:
            return jsonify({'message': str(error)}), 400
        except OldapError as error:  # should not be reachable
            return jsonify({'message': str(error)}), 500

        return jsonify({"message": "Project successfully created"}), 200
    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400


@bp.route('/project/<projectid>', methods=['DELETE'])
def delete_project(projectid):
    """
    Viewfunction to delete a project.
    :param projectid: The projectid ot the project that should to be deleted.
    :return: A JSON to denote the success of the operation that has the following form:
    json={"message": "Project successfully deleted"}
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
        project = Project.read(con=con, projectIri_SName=Xsd_NCName(projectid))
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404
    try:
        project.delete()
    except OldapErrorNoPermission as error:
        return jsonify({'message': str(error)}), 403
    except OldapError as error:  # Should not be reachable!
        return jsonify({'message': str(error)}), 500

    return jsonify({"message": "Project successfully deleted"}), 200


@bp.route('/project/<projectid>', methods=['GET'])
def read_project(projectid):
    """
    Viewfunction to retrieve information about the project given by the projectid.
    :param projectid: The projectid of the project for that the information should be retrieved.
    :return: A JSON containing the information about the given project. It has the following form:
    json={
    'Project': 'http://unittest.org/project/testproject',
    'Creation': '2024-05-27T18:32:43.120691 by https://orcid.org/0000-0003-1681-4036',
    Modified: 2024-05-27T18:32:43.120691 by https://orcid.org/0000-0003-1681-4036,
    Label: "unittest@en", "unittest@de",
    Comment: "For testing@en", "Für Tests@de",
    ShortName: testproject,
    Namespace IRI: http://unitest.org/project/unittest#,
    Project start: 1993-04-05,
    Project end: 2000-01-10
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
        project = Project.read(con=con, projectIri_SName=projectid)
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404
    res = {
        'projectIri': str(project.projectIri),
        'creator': str(project.creator),
        'created': str(project.created),
        'contributor': str(project.contributor),
        'modified': str(project.modified),
        'label': [f'{value}@{lang.name.lower()}' for lang, value in project.label.items()] if project.label else None,
        'comment': [f'{value}@{lang.name.lower()}' for lang, value in project.comment.items()] if project.comment else None,
        'projectShortname': str(project.projectShortName),
        'namespaceIri': str(project.namespaceIri),
        'projectStart': str(project.projectStart) if project.projectStart else None,
        'projectEnd': str(project.projectEnd) if project.projectEnd else None
    }
    return res, 200


@bp.route('/project/search', methods=['GET'])
def search_project():
    """
    Viewfunction to search for a project. It is possible to search for label and comment.
    A JSON is expected that has the following form:
    json={
    "label": examplelabel,
    "comment": examplecomment
    }
    :return: A JSON containing the Iri's about the found projects. It has the following form:
    json={'message': '[Iri("http://unittest.org/project/testproject")]'}
    """
    known_json_fields = {"label", "comment"}
    out = request.headers['Authorization']
    b, token = out.split()

    if request.is_json:
        data = request.get_json()
        unknown_json_field = set(data.keys()) - known_json_fields
        if unknown_json_field:
            return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to search for a project. Usable are {known_json_fields}. Aborded operation"}), 400
        if not set(data.keys()):
            return jsonify({"message": f"At least one field must be given to search for a project. Usablable for the search-viewfunction are {known_json_fields}"}), 400
        label = data.get("label", None)
        comment = data.get('comment', None)

        try:
            con = Connection(server='http://localhost:7200',
                             repo="oldap",
                             token=token,
                             context_name="DEFAULT")
        except OldapError as error:
            return jsonify({"message": f"Connection failed: {str(error)}"}), 403

        projects = Project.search(con=con, label=label, comment=comment)
        return jsonify(str(projects)), 200

    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400


@bp.route('/project/<projectid>', methods=['POST'])
def modify_project(projectid):
    """
    Veiwfunction to modify a project given its projectid. The label, comment, projectstart and projectend can be modified this way.
    A JSON is expectet that has the following form - all the fields are optionals, a list exchanges the
    whole field, a dict adds/removes entries:
    json={
    "label": "["unittest@en", "..."]" or "{"add": ["tobeadded@it", ...], "del": ["tobedeleted@en"]},
    "comment": ["For testing@en", "..."] or "{"add": ["tobeadded@it", ...], "del": ["tobedeleted@en"]},
    "projectstart": "1995-05-28",
    "projectend": "2001-09-18"
    }
    :param projectid: The projectid of the project that should be modified.
    :return: A JSON informing about the success of the operation that has the following form:
    json={"message": "Project updated successfully"}
    """
    known_json_fields = {"label", "comment", "projectStart", "projectEnd"}
    out = request.headers['Authorization']
    b, token = out.split()

    if request.is_json:
        data = request.get_json()
        unknown_json_field = set(data.keys()) - known_json_fields
        if unknown_json_field:
            return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to modify a project. Usable are {known_json_fields}. Aborded operation"}), 400
        if not set(data.keys()):
            return jsonify({"message": f"At least one field must be given to modify the project. Usablable for the modify-viewfunction are {known_json_fields}"}), 400
        label = data.get("label", "NotSent")
        comment = data.get("comment", "NotSent")
        projectStart = data.get("projectStart", None)
        projectEnd = data.get("projectEnd", None)

        try:
            con = Connection(server='http://localhost:7200',
                             repo="oldap",
                             token=token,
                             context_name="DEFAULT")
        except OldapError as error:
            return jsonify({"message": f"Connection failed: {str(error)}"}), 403
        try:
            project = Project.read(con=con, projectIri_SName=projectid)
        except OldapErrorNotFound as error:
            return jsonify({"message": str(error)}), 404

        try:
            if label != "NotSent":
                if isinstance(label, str):
                    return jsonify({"message": f"For the label either a list or a dict is expected, not a string"}), 400
                if isinstance(label, list):
                    for item in label:
                        try:
                            if item[-3] != '@':
                                return jsonify({"message": f"Please add a correct language tags e.g. @de"}), 400
                        except IndexError as error:
                            return jsonify({"message": f"Please add a correct language tags e.g. @de"}), 400
                    project.label = LangString(label)
                elif isinstance(label, dict):
                    if "add" in label:
                        if not isinstance(label["add"], list):
                            return jsonify({"message": f"The add entry needs to be a list, not a string."}), 400
                        for item in label["add"]:
                            try:
                                if item[-3] != '@':
                                    return jsonify({"message": f"Please add a correct language tags e.g. @de"}), 400
                            except IndexError as error:
                                return jsonify({"message": f"Please add a correct language tags e.g. @de"}), 400
                            lang = item[-2:].upper()
                            try:
                                project.label[Language[lang]] = item[:-3]
                            except KeyError as error:
                                return jsonify({"message": f"{lang} is not a valid language. Supportet are {known_languages}"}), 400
                    if "del" in label:
                        if not isinstance(label["del"], list):
                            return jsonify({"message": f"The delete entry needs to be a list, not a string."}), 400
                        for item in label["del"]:
                            try:
                                if item[-3] != '@':
                                    return jsonify({"message": f"Please add a correct language tags e.g. @de"}), 400
                            except IndexError as error:
                                return jsonify({"message": f"Please add a correct language tags e.g. @de"}), 400
                            lang = item[-2:].upper()
                            try:
                                del project.label[Language[lang]]
                            except KeyError as error:
                                return jsonify({"message": f"{lang} is not a valid language. Supportet are {known_languages}"}), 400
                    if "add" not in label and "del" not in label:
                        return jsonify({"message": f"The sended command (keyword in dict) is not known"}), 400
                elif label is None:
                    del project.label
                else:
                    return jsonify({"message": f"Either a List or a dict is required."}), 400

            if comment != "NotSent":
                if isinstance(comment, str):
                    return jsonify({"message": f"For the comment either a list or a dict is expected, not a string"}), 400
                if isinstance(comment, list):
                    for item in comment:
                        try:
                            if item[-3] != '@':
                                return jsonify({"message": f"Please add a correct language tags e.g. @de"}), 400
                        except IndexError as error:
                            return jsonify({"message": f"Please add a correct language tags e.g. @de"}), 400
                    project.comment = LangString(comment)
                elif isinstance(comment, dict):
                    if "add" in comment:
                        if not isinstance(comment["add"], list):
                            return jsonify({"message": f"The add entry needs to be a list, not a string."}), 400
                        for item in comment["add"]:
                            try:
                                if item[-3] != '@':
                                    return jsonify({"message": f"Please add a correct language tag e.g. @de"}), 400
                            except IndexError as error:
                                return jsonify({"message": f"Please add a correct language tags e.g. @de"}), 400
                            lang = item[-2:].upper()
                            try:
                                project.comment[Language[lang]] = item[:-3]
                            except KeyError as error:
                                return jsonify({"message": f"{lang} is not a valid language. Supportet are {known_languages}"}), 400
                    if "del" in comment:
                        if not isinstance(comment["del"], list):
                            return jsonify({"message": f"The delete entry needs to be a list, not a string."}), 400
                        for item in comment["del"]:
                            try:
                                if item[-3] != '@':
                                    return jsonify({"message": f"Please add a correct language tags e.g. @de"}), 400
                            except IndexError as error:
                                return jsonify({"message": f"Please add a correct language tags e.g. @de"}), 400
                            lang = item[-2:].upper()
                            try:
                                del project.comment[Language[lang]]
                            except KeyError as error:
                                return jsonify({"message": f"{lang} is not a valid language. Supportet are {known_languages}"}), 400
                    if "add" not in comment and "del" not in comment:
                        return jsonify({"message": f"The sended command (keyword in dict) is not known"}), 400
                elif comment is None:
                    del project.comment
                else:
                    return jsonify({"message": f"Either a List or a dict is required."}), 400
            if projectStart:
                project.projectStart = Xsd_date(projectStart)
            if projectEnd:
                project.projectEnd = Xsd_date(projectEnd)
        except OldapErrorValue as error:
            return jsonify({"message": str(error)}), 400
        except OldapErrorInconsistency as error:  # inconsistent start and enddate
            return jsonify({'message': str(error)}), 400
        except OldapError as error:
            return jsonify({"message": str(error)}), 500

        try:
            project.update()
        except OldapErrorNoPermission as error:
            return jsonify({"message": str(error)}), 403
        except OldapErrorUpdateFailed as error:  # hard to test
            return jsonify({"message": str(error)}), 500
        except OldapError as error:  # should not be reachable
            return jsonify({"message": str(error)}), 500

        return jsonify({"message": "Project updated successfully"}), 200
    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400


@bp.route('/permissionset/<definedByProject>/<permissionsetid>', methods=['PUT'])
def create_permissionset(definedByProject, permissionsetid):
    '''
    Viewfunction to create a new permissionset. A JSON is expectet that contains the necessary information to create a new
    permissionset that has the following form:
    json={
        "label": ["testPerm@en", "test@Perm@de"],
        "comment": ["For testing@en", "Für Tests@de"],
        "givesPermission": "DATA_UPDATE",
    }
    :param definedByProject: The project that defines this permission set (either the IRI or the shortname)
    :param permissionsetid: A unique identifier for the permission set (unique within the project as given by :definedByProject)
    :return: A JSON informing about the success of the operation that has the following form:
    json={"message": "Project updated successfully"}
    '''
    known_json_fields = {"label", "comment", "givesPermission"}
    mandatory_json_fields = {"givesPermission"}
    out = request.headers['Authorization']
    b, token = out.split()

    if request.is_json:

        data = request.get_json()
        unknown_json_field = set(data.keys()) - known_json_fields
        if unknown_json_field:
            return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to create a permissionset. Usable are {known_json_fields}. Aborded operation"}), 400
        if not mandatory_json_fields.issubset(set(data.keys())):
            return jsonify({"message": f"The Fields {mandatory_json_fields} are required to create a permissionset. Used where {set(data.keys())}. Usablable are {known_json_fields}"}), 400
        label = data.get("label", None)
        comment = data.get("comment", None)  # Enum: Datapermission
        givesPermission = data.get("givesPermission", None)  # Necessary

        if label == [] or comment == []:
            return jsonify({"message": f"A meaningful label and comment need to be provided and can not be empty"}), 400

        if isinstance(givesPermission, list):
            return jsonify({"message": "Only one permission can be provided and it must not be a List"}), 400

        try:
            givesPermission = DataPermission.from_string(f'oldap:{givesPermission}')
        except ValueError as error:
            return jsonify({"message": str(error)}), 400

        try:
            con = Connection(server='http://localhost:7200',
                             repo="oldap",
                             token=token,
                             context_name="DEFAULT")
        except OldapError as error:
            return jsonify({"message": f"Connection failed: {str(error)}"}), 403
        try:
            permissionset = PermissionSet(con=con,
                                          permissionSetId=permissionsetid,
                                          label=LangString(label),
                                          comment=LangString(comment),
                                          givesPermission=givesPermission,
                                          definedByProject=definedByProject)
            permissionset.create()
        except OldapErrorNoPermission as error:
            return jsonify({'message': str(error)}), 403
        except OldapErrorAlreadyExists as error:
            return jsonify({'message': str(error)}), 409
        except OldapErrorValue as error:
            return jsonify({'message': str(error)}), 400
        except OldapError as error:  # should not be reachable
            return jsonify({'message': str(error)}), 500

        return jsonify({"message": "Permissionset successfully created"}), 200
    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400


@bp.route('/permissionset/<definedbyproject>/<permissionsetid>', methods=['GET'])
def read_permissionset(definedbyproject, permissionsetid):
    '''
    Viewfunction to retrieve information about the project given by the projectid.
    :param definedbyproject: The project that defines this permission set (either the IRI or the shortname)
    :param permissionsetid: A unique identifier for the permission set (unique within the project as given by :definedByProject)
    :return: A JSON containing the information about the given project. It has the following form:
    json={
        'permisionsetid': 'testpermissionset',
        'creation': '2024-07-31T16:27:22.918232',
        'contributor': 'https://orcid.org/0000-0003-1681-4036',
        'modified': '2024-07-31T16:27:22.918232',
        'label': ['testPerm@en', 'test@de'],
        'comment': ['For testing@en', 'Für Tests@de'],
        'givesPermission': 'DataPermission.DATA_UPDATE',
        'definedByProject': 'oldap:SystemProject'
    }
    '''
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
        ps = PermissionSet.read(con=con, permissionSetId=permissionsetid, definedByProject=definedbyproject)
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404

    res = {
        'permisionsetid': str(ps.permissionSetId),
        'creation': str(ps.created),
        'contributor': str(ps.contributor),
        'modified': str(ps.modified),
        'label': [f'{value}@{lang.name.lower()}' for lang, value in ps.label.items()] if ps.label else None,
        'comment': [f'{value}@{lang.name.lower()}' for lang, value in ps.comment.items()] if ps.comment else None,
        'givesPermission': str(ps.givesPermission),
        'definedByProject': str(ps.definedByProject),
    }

    return res, 200


@bp.route('/permissionset/search', methods=['GET'])
def search_permissionset():
    '''
    Viewfunction to search for a permissionset. It is possible to search for definedByProject, givesPermission and label.
    A JSON is expected that has the following form (at least one keyword is needed):
    json={
    "label": examplelabel,
    "definedByProject": exampledefinedByProject,
    "givesPermission": examplegivesPermission
    }
    :return: A JSON containing the Iri's about the found projects. It has the following form:
    json={'message': '[Iri("http://unittest.org/project/testproject")]'}
    '''
    known_json_fields = {"definedByProject", "givesPermission", "label"}
    out = request.headers['Authorization']
    b, token = out.split()

    if request.is_json:
        data = request.get_json()
        unknown_json_field = set(data.keys()) - known_json_fields
        if unknown_json_field:
            return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to search for a permissionset. Usable are {known_json_fields}. Aborded operation"}), 400
        if not set(data.keys()):
            return jsonify({"message": f"At least one field must be given to search for a permissionset. Usable for the search-viewfunction are {known_json_fields}"}), 400
        label = data.get("label", None)
        givespermission = data.get('givesPermission', None)
        definedbyproject = data.get("definedByProject", None)

        try:
            con = Connection(server='http://localhost:7200',
                             repo="oldap",
                             token=token,
                             context_name="DEFAULT")
        except OldapError as error:
            return jsonify({"message": f"Connection failed: {str(error)}"}), 403

        permissionset = PermissionSet.search(con=con, label=label, givesPermission=givespermission, definedByProject=definedbyproject)
        return jsonify(str(permissionset)), 200

    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400


@bp.route('/permissionset/<definedbyproject>/<permissionsetid>', methods=['DELETE'])
def delete_permissionset(definedbyproject, permissionsetid):
    '''
    Viewfunction to delete a project.
    :param definedbyproject: The project that defines this permission set (either the IRI or the shortname)
    :param permissionsetid: A unique identifier for the permission set (unique within the project as given by :definedByProject)
    :return: A JSON to denote the success of the operation that has the following form:
    json={"message": "Project successfully deleted"}
    '''
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
        ps = PermissionSet.read(con=con, permissionSetId=permissionsetid, definedByProject=definedbyproject)
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404

    try:
        ps.delete()
    except OldapErrorNoPermission as error:
        return jsonify({'message': str(error)}), 403
    except OldapError as error:  # Should not be reachable!
        return jsonify({'message': str(error)}), 500

    return jsonify({"message": "Permissionset successfully deleted"}), 200


@bp.route('/permissionset/<definedbyproject>/<permissionsetid>', methods=['POST'])
def modify_permissionset(definedbyproject, permissionsetid):
    '''
    Veiwfunction to modify a permissionset given its permissionsetid and its definedbyproject. The label, comment and
    givesPermission can be modified this way. A JSON is expectet that has the following form - all the fields are
    optionals, a list exchanges the whole field, a dict adds/removes entries:
    json={
    "label": "["unittest@en", "..."]" or "{"add": ["tobeadded@it", ...], "del": ["tobedeleted@en"]},
    "comment": ["For testing@en", "..."] or "{"add": ["tobeadded@it", ...], "del": ["tobedeleted@en"]},
    "givesPermission": ["DATA_VIEW", "..."] or "{"add": ["DATA_VIEW", ...], "del": ["DATA_EXTEND"]}
    }
    :param definedbyproject: The project that defines this permission set (either the IRI or the shortname)
    :param permissionsetid: A unique identifier for the permission set (unique within the project as given by :definedByProject)
    :return: A JSON informing about the success of the operation that has the following form:
    json={"message": "Project updated successfully"}
    '''
    known_json_fields = {"label", "comment", "givesPermission"}
    known_permissions = {"DATA_RESTRICTED", "DATA_VIEW", "DATA_EXTEND", "DATA_UPDATE", "DATA_DELETE", "DATA_PERMISSIONS"}
    out = request.headers['Authorization']
    b, token = out.split()

    if request.is_json:
        data = request.get_json()
        unknown_json_field = set(data.keys()) - known_json_fields
        if unknown_json_field:
            return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to modify a project. Usable are {known_json_fields}. Aborded operation"}), 400
        if not set(data.keys()):
            return jsonify({"message": f"At least one field must be given to modify the project. Usablable for the modify-viewfunction are {known_json_fields}"}), 400
        label = data.get("label", "NotSent")
        comment = data.get("comment", "NotSent")
        givesPermission = data.get("givesPermission", "NotSent")

        try:
            con = Connection(server='http://localhost:7200',
                             repo="oldap",
                             token=token,
                             context_name="DEFAULT")
        except OldapError as error:
            return jsonify({"message": f"Connection failed: {str(error)}"}), 403
        try:
            ps = PermissionSet.read(con=con, permissionSetId=permissionsetid, definedByProject=definedbyproject)
        except OldapErrorNotFound as error:
            return jsonify({"message": str(error)}), 404

        try:
            if label != "NotSent":
                if isinstance(label, str):
                    return jsonify({"message": f"For the label either a list or a dict is expected, not a string"}), 400
                if isinstance(label, list):
                    for item in label:
                        try:
                            if item[-3] != '@':
                                return jsonify({"message": f"Please add a correct language tags e.g. @de"}), 400
                        except IndexError as error:
                            return jsonify({"message": f"Please add a correct language tags e.g. @de"}), 400
                    ps.label = LangString(label)
                elif isinstance(label, dict):
                    if "add" in label:
                        if not isinstance(label["add"], list):
                            return jsonify({"message": f"The add entry needs to be a list, not a string."}), 400
                        for item in label["add"]:
                            try:
                                if item[-3] != '@':
                                    return jsonify({"message": f"Please add a correct language tags e.g. @de"}), 400
                            except IndexError as error:
                                return jsonify({"message": f"Please add a correct language tags e.g. @de"}), 400
                            lang = item[-2:].upper()
                            try:
                                ps.label[Language[lang]] = item[:-3]
                            except KeyError as error:
                                return jsonify({"message": f"{lang} is not a valid language. Supportet are {known_languages}"}), 400
                    if "del" in label:
                        if not isinstance(label["del"], list):
                            return jsonify({"message": f"The delete entry needs to be a list, not a string."}), 400
                        for item in label["del"]:
                            try:
                                if item[-3] != '@':
                                    return jsonify({"message": f"Please add a correct language tags e.g. @de"}), 400
                            except IndexError as error:
                                return jsonify({"message": f"Please add a correct language tags e.g. @de"}), 400
                            lang = item[-2:].upper()
                            try:
                                del ps.label[Language[lang]]
                            except KeyError as error:
                                return jsonify({"message": f"{lang} is not a valid language. Supportet are {known_languages}"}), 400
                    if "add" not in label and "del" not in label:
                        return jsonify({"message": f"The sended command (keyword in dict) is not known"}), 400
                elif label is None:
                    del ps.label
                else:
                    return jsonify({"message": f"Either a List or a dict is required."}), 400

            if comment != "NotSent":
                if isinstance(comment, str):
                    return jsonify({"message": f"For the comment either a list or a dict is expected, not a string"}), 400
                if isinstance(comment, list):
                    for item in comment:
                        try:
                            if item[-3] != '@':
                                return jsonify({"message": f"Please add a correct language tags e.g. @de"}), 400
                        except IndexError as error:
                            return jsonify({"message": f"Please add a correct language tags e.g. @de"}), 400
                    ps.comment = LangString(comment)
                elif isinstance(comment, dict):
                    if "add" in comment:
                        if not isinstance(comment["add"], list):
                            return jsonify({"message": f"The add entry needs to be a list, not a string."}), 400
                        for item in comment["add"]:
                            try:
                                if item[-3] != '@':
                                    return jsonify({"message": f"Please add a correct language tag e.g. @de"}), 400
                            except IndexError as error:
                                return jsonify({"message": f"Please add a correct language tags e.g. @de"}), 400
                            lang = item[-2:].upper()
                            try:
                                ps.comment[Language[lang]] = item[:-3]
                            except KeyError as error:
                                return jsonify({"message": f"{lang} is not a valid language. Supportet are {known_languages}"}), 400
                    if "del" in comment:
                        if not isinstance(comment["del"], list):
                            return jsonify({"message": f"The delete entry needs to be a list, not a string."}), 400
                        for item in comment["del"]:
                            try:
                                if item[-3] != '@':
                                    return jsonify({"message": f"Please add a correct language tags e.g. @de"}), 400
                            except IndexError as error:
                                return jsonify({"message": f"Please add a correct language tags e.g. @de"}), 400
                            lang = item[-2:].upper()
                            try:
                                del ps.comment[Language[lang]]
                            except KeyError as error:
                                return jsonify({"message": f"{lang} is not a valid language. Supportet are {known_languages}"}), 400
                    if "add" not in comment and "del" not in comment:
                        return jsonify({"message": f"The sended command (keyword in dict) is not known"}), 400
                elif comment is None:
                    del ps.comment
                else:
                    return jsonify({"message": f"Either a List or a dict is required."}), 400

            if givesPermission != "NotSent":
                ps.givesPermission = DataPermission[givesPermission]
        except KeyError as error:
            return jsonify({"message": f"{givesPermission} is not a valid permission. Supportet are {known_permissions}"}), 400
        except OldapError as error:
            return jsonify({"message": f'{str(error)}, Could not delete the given entry'}), 500

        try:
            ps.update()
        except OldapErrorNoPermission as error:
            return jsonify({"message": str(error)}), 403
        except OldapErrorUpdateFailed as error:  # hard to test
            return jsonify({"message": str(error)}), 500
        except OldapError as error:  # should not be reachable
            return jsonify({"message": str(error)}), 500

        return jsonify({"message": "Permissionset updated successfully"}), 200
    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400
