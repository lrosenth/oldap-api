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
from oldaplib.src.xsd.xsd_date import Xsd_date
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_string import Xsd_string

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
    known_json_fields = {"givenName", "familyName", "password", "inProjects", "hasPermissions"}
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
                        isActive=True)
            user.create()
        except OldapErrorAlreadyExists as error:
            return jsonify({"message": str(error)}), 409
        except OldapErrorValue as error:
            return jsonify({'message': str(error)}), 400
        except OldapError as error:
            return jsonify({'message': str(error)})

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
    'isActive': 'true',
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
        "isActive": str(user.isActive),
        "given_name": str(user.givenName),
        "in_projects": [],
        "has_permissions": [str(x) for x in user.hasPermissions] if user.hasPermissions else []
    }

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
        user3 = User.read(con=con, userId=userid)
        user3.delete()
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
        "in_projects": [{
            "permissions": ['oldap:ADMIN_USERS', (...)],
            "project": 'http://www.salsah.org/version/2.0/SwissBritNet'
            }, {...}],
        "has_permissions": ['oldap:GenericView', (...)]
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
        firstname = data.get("givenName", None)
        lastname = data.get("familyName", None)
        password = data.get("password", None)
        inprojects = data.get('inProjects', None)
        haspermissions = data.get('hasPermissions', None)
        isactive = data.get('isActive', None)

        in_project_dict: Dict[str | Iri, Set[AdminPermission] | ObservableSet[AdminPermission]] | None = None
        if inprojects is not None:
            in_project_dict = {}  # we need an empty dict to fill it
            for item in inprojects:
                project_name = item["project"]

                if item.get("permissions") is not None:
                    try:
                        permissions = {AdminPermission(f'oldap:{x}') for x in item["permissions"]}
                    except ValueError as error:
                        return jsonify({'message': f'The given project permission is not a valid one'}), 400
                else:
                    permissions = set()
                try:
                    in_project_dict[Iri(project_name)] = permissions
                except OldapErrorValue as error:
                    return jsonify({'message': f'The given projectname is not a valid anyIri'}), 400

        if haspermissions is not None:
            try:
                permission_set = {Iri(f'oldap:{x}') for x in haspermissions}
            except OldapErrorValue as error:
                return jsonify({'message': f'The given permission is not a QName'}), 400
        else:
            permission_set = None

        try:
            con = Connection(server='http://localhost:7200',
                             repo="oldap",
                             token=token,
                             context_name="DEFAULT")
        except OldapError as error:
            return jsonify({"message": f"Connection failed: {str(error)}"}), 403

        try:
            user2 = User.read(con=con, userId=Xsd_NCName(userid))  # read the user from the triple store
        except OldapErrorNotFound as error:
            return jsonify({"message": str(error)}), 404

        if firstname:
            user2.givenName = Xsd_string(firstname)
        if lastname:
            user2.familyName = Xsd_string(lastname)
        if password:
            user2.credentials = Xsd_string(password)
        if isactive is not None:
            if isactive.lower() == 'true':
                user2.isActive = True
            elif isactive.lower() == 'false':
                user2.isActive = False
        if in_project_dict is not None:
            user2.inProject = InProjectClass(in_project_dict)
        if permission_set:
            user2.hasPermissions = permission_set
        if permission_set == set():
            user2.hasPermissions = set()

        try:
            user2.update()
        except OldapErrorUpdateFailed as error:  # hard to test
            return jsonify({"message": str(error)}), 500
        except OldapErrorValue as error:
            return jsonify({"message": str(error)}), 404
        except OldapErrorNoPermission as error:  # prob bug in backend -- not reachable yet
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
        "label": ["unittest@en", "unittest@de"],
        "comment": ["For testing@en", "Für Tests@de"],
        "namespaceIri": "http://unitest.org/project/unittest#",
        "projectStart": "1993-04-05",
        "projectEnd": "2000-01-10"
    }
    :param projectid: The projectid (nikname/shortname) for the new project.
    :return: A JSON to denote the success of the operation that has the following form:
    json={"message": "Project successfully created"}
    """
    known_json_fields = {"projectIri", "label", "comment", "namespaceIri", "projectStart", "projectEnd"}
    mandatory_json_fields = {"label", "namespaceIri"}
    out = request.headers['Authorization']
    b, token = out.split()

    if request.is_json:
        data = request.get_json()
        unknown_json_field = set(data.keys()) - known_json_fields
        if unknown_json_field:
            return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to create a project. Usable are {known_json_fields}. Aborded operation"}), 400
        projectIri = data.get("projectIri", None)
        projectShortName = projectid  # Necessary
        label = data.get("label", None)  # Necessary
        comment = data.get('comment', None)
        namespaceIri = data.get('namespaceIri', None)  # Necessary
        projectStart = data.get('projectStart', None)
        projectEnd = data.get('projectEnd', None)

        if label is None or namespaceIri is None or projectShortName is None:
            return jsonify({
                               "message": f"To create a project, at least the projectshortname, label, comment and namespaceIri are required"}), 400
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
                              projectShortName=Xsd_NCName(projectShortName),  # NO
                              projectIri=Iri(projectIri),  # NO
                              label=LangString(label),
                              namespaceIri=NamespaceIRI(namespaceIri),  # NO
                              comment=LangString(comment),
                              projectStart=Xsd_date(projectStart) if projectEnd else None,
                              projectEnd=Xsd_date(projectEnd) if projectEnd else None
                              )
            project.create()
        except OldapErrorNoPermission as error:
            return jsonify({'message': str(error)}), 403
        except OldapErrorAlreadyExists as error:
            return jsonify({'message': str(error)}), 409
        except OldapErrorInconsistency as error:
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
    known_json_fields = {"label", "comment"}
    out = request.headers['Authorization']
    b, token = out.split()

    if request.is_json:
        data = request.get_json()
        unknown_json_field = set(data.keys()) - known_json_fields
        if unknown_json_field:
            return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to search for a project. Usable are {known_json_fields}. Aborded operation"}), 400
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
        return jsonify({"message": str(projects)}), 200

    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400


@bp.route('/project/<projectid>', methods=['POST'])
def modify_project(projectid):
    known_json_fields = {"label", "comment", "projectStart", "projectEnd"}
    out = request.headers['Authorization']
    b, token = out.split()

    if request.is_json:
        data = request.get_json()
        unknown_json_field = set(data.keys()) - known_json_fields
        if unknown_json_field:
            return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to modify a project. Usable are {known_json_fields}. Aborded operation"}), 400

        label = data.get("label", None)
        comment = data.get("comment", None)
        projectStart = data.get("projectStart", None)
        projectEnd = data.get("projectEnd", None)

        if label is None and comment is None and projectStart is None and projectEnd is None:
            return jsonify(
                {'message': 'Either the label, comment, projectStart or projectEnd needs to be modified'}), 400

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
            if label:
                project.label = LangString(label)
            if comment:
                project.comment = LangString(comment)
            if projectStart:
                project.projectStart = Xsd_date(projectStart)
            if projectEnd:
                project.projectEnd = Xsd_date(projectEnd)
        except OldapErrorValue as error:
            return jsonify({"message": str(error)}), 400
        except OldapErrorInconsistency as error:
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


@bp.route('/permissionset/<projectshortname>/<permisionsetid>', methods=['PUT'])
def create_permissionset(projectshortname, permisionsetid):
    known_json_fields = {"label", "comment", "givesPermission", "definedByProject", "id"}
    mandatory_json_fields = {"label", "givesPermission"}
    out = request.headers['Authorization']
    b, token = out.split()

    if request.is_json:

        data = request.get_json()
        unknown_json_field = set(data.keys()) - known_json_fields
        if unknown_json_field:
            return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to create a permissionset. Usable are {known_json_fields}. Aborded operation"}), 400
        label = data.get("label", None)  # Necessary
        comment = data.get("comment", None)  # Enum: Datapermission
        givesPermission = data.get("givesPermission", None)  # Necessary
        definedByProject = data.get('definedByProject', None)  # Necessary

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
                                          label=LangString(label),
                                          comment=LangString(comment),
                                          givesPermission=givesPermission,
                                          definedByProject=Iri(definedByProject))
            permissionset.create()
        except OldapErrorNoPermission as error:
            return jsonify({'message': str(error)}), 403
        except OldapErrorAlreadyExists as error:
            return jsonify({'message': str(error)}), 409
        except OldapErrorInconsistency as error:
            return jsonify({'message': str(error)}), 400
        except OldapErrorValue as error:
            return jsonify({'message': str(error)}), 400
        except OldapError as error:  # should not be reachable
            return jsonify({'message': str(error)}), 500

        return jsonify({"message": "Permissionset successfully created"}), 200
    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400


@bp.route('/permissionset/<permissionlabel>', methods=['GET'])
def read_permissionset(permissionlabel):
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
        permissionsetIri = PermissionSet.search(con=con, label=permissionlabel)[0]
    except IndexError as error:
        return jsonify({"message": "Permissionset not found"}), 404

    try:
        ps = PermissionSet.read(con=con, permissionSetIri=permissionsetIri)
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404

    return jsonify({"message": str(ps)}), 200


@bp.route('/permissionset/search', methods=['GET'])
def search_permissionset():
    known_json_fields = {"definedByProject", "givesPermission", "label"}
    out = request.headers['Authorization']
    b, token = out.split()

    if request.is_json:
        data = request.get_json()
        unknown_json_field = set(data.keys()) - known_json_fields
        if unknown_json_field:
            return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to search for a permissionset. Usable are {known_json_fields}. Aborded operation"}), 400
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
        try:
            permissionset = PermissionSet.search(con=con, label=label, givesPermission=givespermission, definedByProject=definedbyproject)
            return jsonify({"message": str(permissionset)}), 200
        except OldapErrorNotFound as error:
            return jsonify({'message': str(error)}), 404
    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400


@bp.route('/permissionset/<permissionlabel>', methods=['DELETE'])
def delete_permissionset(permissionlabel):
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
        permissionsetIri = PermissionSet.search(con=con, label=permissionlabel)[0]
    except IndexError as error:
        return jsonify({"message": "Permissionset not found"}), 404

    try:
        ps = PermissionSet.read(con=con, permissionSetIri=permissionsetIri)
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404

    try:
        ps.delete()
    except OldapErrorNoPermission as error:
        return jsonify({'message': str(error)}), 403
    except OldapError as error:  # Should not be reachable!
        return jsonify({'message': str(error)}), 500

    return jsonify({"message": "Permissionset successfully deleted"}), 200
