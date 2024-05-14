from typing import Dict, Set

from flask import Blueprint, request, jsonify
from omaslib.src.connection import Connection
from omaslib.src.dtypes.namespaceiri import NamespaceIRI
from omaslib.src.enums.permissions import AdminPermission, DataPermission
from omaslib.src.helpers.langstring import LangString
from omaslib.src.helpers.observable_set import ObservableSet
from omaslib.src.helpers.omaserror import OmasError, OmasErrorNotFound, OmasErrorAlreadyExists, OmasErrorValue, \
    OmasErrorUpdateFailed, OmasErrorNoPermission, OmasErrorInconsistency
from omaslib.src.in_project import InProjectClass
from omaslib.src.permissionset import PermissionSet
from omaslib.src.project import Project
from omaslib.src.user import User
from omaslib.src.xsd.iri import Iri
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
            resp = jsonify({'message': 'Login succeeded', 'token': con.token}), 200
            return resp
        except OmasErrorNotFound as err:
            return jsonify({'message': str(err)}), 404
        except OmasError as error:
            return jsonify({"message": f"Connection failed: {str(error)}"}), 403
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
        except OmasError as error:
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
        except OmasErrorAlreadyExists as error:
            return jsonify({"message": str(error)}), 409
        except OmasErrorValue as error:
            return jsonify({'message': str(error)}), 400
        except OmasError as error:
            return jsonify({'message': str(error)})

    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400
    return jsonify({"message": f"User {userid} created", "userIri": f"{userid}"}), 200


# Function to read the contents of a user
@bp.route('/user/<userid>', methods=['GET'])
def read_users(userid):
    out = request.headers['Authorization']
    b, token = out.split()

    try:
        con = Connection(server='http://localhost:7200',
                         repo="omas",
                         token=token,
                         context_name="DEFAULT")
    except OmasError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    try:
        user = User.read(con=con, userId=userid)
    except OmasErrorNotFound as error:
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
    out = request.headers['Authorization']
    b, token = out.split()

    try:
        con = Connection(server='http://localhost:7200',
                         repo="omas",
                         token=token,
                         context_name="DEFAULT")
    except OmasError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    try:
        user3 = User.read(con=con, userId=userid)
        user3.delete()
    except OmasErrorNotFound as error:
        return jsonify({"message": str(error)}), 404
    except OmasErrorNoPermission as error:
        return jsonify({"message": str(error)}), 403

    return jsonify({"message": f"User {userid} deleted"}), 200


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
        isactive = data.get('isActive', None)

        if firstname is None and lastname is None and password is None and inprojects is None and haspermissions is None and isactive is None:
            return jsonify({
                               "message": "Either the firstname, lastname, password, isactive, inProjects or hasPermissions needs to be modified"}), 400

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
            return jsonify({"message": f"Connection failed: {str(error)}"}), 403

        try:
            user2 = User.read(con=con, userId=Xsd_NCName(userid))  # read the user from the triple store
        except OmasErrorNotFound as error:
            return jsonify({"message": str(error)}), 404

        if firstname:
            user2.givenName = Xsd_string(firstname)
        if lastname:
            user2.familyName = Xsd_string(lastname)
        if password:
            user2.credentials = Xsd_string(password)
        if isactive is not None and isactive.lower() == 'true':
            user2.isActive = True
        else:
            user2.isActive = False
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
        except OmasErrorUpdateFailed as error:  # hard to test
            return jsonify({"message": str(error)}), 500
        except OmasErrorValue as error:
            return jsonify({"message": str(error)}), 404
        except OmasErrorNoPermission as error:  # prob bug in backend -- not reachable yet
            return jsonify({"message": str(error)}), 403
        except OmasError as error:  # should not be reachable
            return jsonify({"message": str(error)}), 500

        return jsonify({"message": "User updated successfully"}), 200

    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400


@bp.route('/project/<projectid>', methods=['PUT'])
def create_project(projectid):
    out = request.headers['Authorization']
    b, token = out.split()

    if request.is_json:
        data = request.get_json()
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
                             repo="omas",
                             token=token,
                             context_name="DEFAULT")
        except OmasError as error:
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
        except OmasErrorNoPermission as error:
            return jsonify({'message': str(error)}), 403
        except OmasErrorAlreadyExists as error:
            return jsonify({'message': str(error)}), 409
        except OmasErrorInconsistency as error:
            return jsonify({'message': str(error)}), 400
        except OmasErrorValue as error:
            return jsonify({'message': str(error)}), 400
        except OmasError as error:  # should not be reachable
            return jsonify({'message': str(error)}), 500

        return jsonify({"message": "Project successfully created"}), 200
    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400


@bp.route('/project/<projectid>', methods=['DELETE'])
def delete_project(projectid):
    out = request.headers['Authorization']
    b, token = out.split()

    try:
        con = Connection(server='http://localhost:7200',
                         repo="omas",
                         token=token,
                         context_name="DEFAULT")
    except OmasError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403
    try:
        project = Project.read(con=con, projectIri_SName=Xsd_NCName(projectid))
    except OmasErrorNotFound as error:
        return jsonify({'message': str(error)}), 404
    try:
        project.delete()
    except OmasErrorNoPermission as error:
        return jsonify({'message': str(error)}), 403
    except OmasError as error:  # Should not be reachable!
        return jsonify({'message': str(error)}), 500

    return jsonify({"message": "Project successfully deleted"}), 200


@bp.route('/project/<projectid>', methods=['GET'])
def read_project(projectid):
    out = request.headers['Authorization']
    b, token = out.split()

    try:
        con = Connection(server='http://localhost:7200',
                         repo="omas",
                         token=token,
                         context_name="DEFAULT")
    except OmasError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403
    try:
        project = Project.read(con=con, projectIri_SName=projectid)
    except OmasErrorNotFound as error:
        return jsonify({'message': str(error)}), 404

    return jsonify({"message": str(project)}), 200


@bp.route('/project/search', methods=['GET'])
def search_project():
    out = request.headers['Authorization']
    b, token = out.split()

    if request.is_json:
        data = request.get_json()
        label = data.get("label", None)
        comment = data.get('comment', None)

        if label is None and comment is None:
            return jsonify({'message': 'Either label or comment needs to be provided'}), 400
        try:
            con = Connection(server='http://localhost:7200',
                             repo="omas",
                             token=token,
                             context_name="DEFAULT")
        except OmasError as error:
            return jsonify({"message": f"Connection failed: {str(error)}"}), 403
        try:
            projects = Project.search(con=con, label=label, comment=comment)
            return jsonify({"message": str(projects)}), 200
        except OmasErrorNotFound as error:
            return jsonify({'message': str(error)}), 404
    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400


@bp.route('/project/<projectid>', methods=['POST'])
def modify_project(projectid):
    out = request.headers['Authorization']
    b, token = out.split()

    if request.is_json:
        data = request.get_json()
        if (data.get("projectShortName", None) is not None or data.get("projectIri", None) is not None
                or data.get("namespaceIri", None) is not None):
            return jsonify({"message": f"projectShortName, projectIri and namespaceIri must not be modified"}), 403

        label = data.get("label", None)
        comment = data.get("comment", None)
        projectStart = data.get("projectStart", None)
        projectEnd = data.get("projectEnd", None)

        if label is None and comment is None and projectStart is None and projectEnd is None:
            return jsonify(
                {'message': 'Either the label, comment, projectStart or projectEnd needs to be modified'}), 400

        try:
            con = Connection(server='http://localhost:7200',
                             repo="omas",
                             token=token,
                             context_name="DEFAULT")
        except OmasError as error:
            return jsonify({"message": f"Connection failed: {str(error)}"}), 403
        try:
            project = Project.read(con=con, projectIri_SName=projectid)
        except OmasErrorNotFound as error:
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
        except OmasErrorValue as error:
            return jsonify({"message": str(error)}), 400
        except OmasErrorInconsistency as error:
            return jsonify({'message': str(error)}), 400
        except OmasError as error:
            return jsonify({"message": str(error)}), 500

        try:
            project.update()
        except OmasErrorNoPermission as error:
            return jsonify({"message": str(error)}), 403
        except OmasErrorUpdateFailed as error:  # hard to test
            return jsonify({"message": str(error)}), 500
        except OmasError as error:  # should not be reachable
            return jsonify({"message": str(error)}), 500

        return jsonify({"message": "Project updated successfully"}), 200
    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400


@bp.route('/permissionset/<permisionsetid>', methods=['PUT'])
def create_permissionset(permisionsetid):
    out = request.headers['Authorization']
    b, token = out.split()

    if request.is_json:

        data = request.get_json()
        label = data.get("label", None)  # Necessary
        comment = data.get("comment", None)  # Enum: Datapermission
        givesPermission = data.get("givesPermission", None)  # Necessary
        definedByProject = data.get('definedByProject', None)  # Necessary

        if label is None or givesPermission is None or definedByProject is None:
            return jsonify({
                               "message": f"To create a permissionset, at least the label, givesPermission and definedByProject are required"}), 400
        if label == [] or comment == []:
            return jsonify({"message": f"A meaningful label and comment need to be provided and can not be empty"}), 400

        if isinstance(givesPermission, list):
            return jsonify({"message": "Only one permission can be provided and it must not be a List"}), 400

        try:
            givesPermission = DataPermission.from_string(givesPermission)
        except ValueError as error:
            return jsonify({"message": str(error)}), 400

        try:
            con = Connection(server='http://localhost:7200',
                             repo="omas",
                             token=token,
                             context_name="DEFAULT")
        except OmasError as error:
            return jsonify({"message": f"Connection failed: {str(error)}"}), 403
        try:
            permissionset = PermissionSet(con=con,
                                          label=LangString(label),
                                          comment=LangString(comment),
                                          givesPermission=givesPermission,
                                          definedByProject=Iri(definedByProject))
            permissionset.create()
        except OmasErrorNoPermission as error:
            return jsonify({'message': str(error)}), 403
        except OmasErrorAlreadyExists as error:
            return jsonify({'message': str(error)}), 409
        except OmasErrorInconsistency as error:
            return jsonify({'message': str(error)}), 400
        except OmasErrorValue as error:
            return jsonify({'message': str(error)}), 400
        except OmasError as error:  # should not be reachable
            return jsonify({'message': str(error)}), 500

        return jsonify({"message": "Project successfully created"}), 200
    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400
