"""
This script is part of a RESTful API for managing functionalities of oldaplib.
It uses Flask and oldaplib to perform CRUD operations on user, project data, permissionsets and more.
The API offers endpoints for creating, reading, updating, searching and deleting functions to interact with the database.

Available endpoints:
- PUT /admin/permissionset/<permissionsetid>: Creates a new permission set.
- GET /admin/permissionset/<permissionlabel>: Reads the data of a permission set.
- DELETE /admin/permissionset/<permissionlabel>: Deletes a permission set.
- POST /admin/permissionset/<definedbyproject>/<permissionsetid>: Modifies an existing permission set.
- GET /admin/permissionset/search: Searches for permission sets.

The implementation includes error handling and validation for most operations.
"""
from flask import request, jsonify, Blueprint, current_app
from oldaplib.src.connection import Connection
from oldaplib.src.enums.datapermissions import DataPermission
from oldaplib.src.enums.roleattr import RoleAttr
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorNoPermission, OldapErrorAlreadyExists, \
    OldapErrorValue, OldapErrorNotFound, OldapErrorUpdateFailed, OldapErrorKey, OldapErrorInconsistency, OldapErrorInUse
from oldaplib.src.role import Role
from oldaplib.src.xsd.xsd_qname import Xsd_QName

from oldap_api.helpers.process_langstring import process_langstring
from oldap_api.views import known_languages

from oldaplib.src.helpers.context import Context

role_bp = Blueprint('role', __name__, url_prefix='/admin')

@role_bp.route('/role/get', methods=['GET'])
def role_get_by_iri():
    """
    Retrieve a role by its Internationalized Resource Identifier (IRI) via an HTTP GET request.

    This function handles an API route that allows retrieving detailed information about a role
    based on its IRI. It validates the request, parses query parameters, establishes a connection
    to the backend, and attempts to retrieve the role's information. If successful, it returns
    the role's metadata in JSON format; otherwise, it provides appropriate error messages.

    :param methods: The HTTP methods allowed for this endpoint. Should be set to a list with 'GET'.
    :type methods: list

    :return: A tuple containing the role metadata as a JSON object and the HTTP status code.
    :rtype: tuple
    :raises KeyError: If the `Authorization` header is missing in the request.
    :raises ValueError: If the `Authorization` token is malformed or improperly split.
    :raises OldapError: If there is an issue establishing a connection to the backend.
    :raises OldapErrorValue: If an issue occurs while reading the role by its IRI.
    :raises OldapErrorNotFound: If the specified role IRI cannot be found.
    :raises Exception: If the conversion of IRI to QName fails.
    """
    out = request.headers['Authorization']
    b, token = out.split()
    if not request.args:
        return jsonify({"message": f"Query parameter 'iri' expected – got none"}), 400

    known_query_fields = {"iri"}
    unknown_query_field = set(request.args.keys() - known_query_fields)
    if unknown_query_field:
        return jsonify({"message": f"The Field/s {unknown_query_field} is/are not used to get a permission set by iri. Use {known_query_fields}. Aborted operation"}), 400
    roleIri = request.args.get('iri', None)

    try:
        con = Connection(token=token,
                         context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    try:
        roleQname = Xsd_QName(roleIri, validate=True)
    except:
        context = Context(name=con.context_name)
        roleQname = context.iri2qname(roleIri)
        if roleQname is None:
            return jsonify({"message": f'Role Iri "{roleIri}" is not valid.'}), 400
    try:
        role = Role.read(con=con, qname=roleQname)
    except OldapErrorValue as error:
        current_app.logger.error(f'Error while reading role by iri "{roleIri}": {str(error)}.')
        return jsonify({"message": str(error)}), 400
    except OldapErrorNotFound as error:
        current_app.logger.error(f'Role by Iri "{roleIri}" not found: {str(error)}.')
        return jsonify({'message': str(error)}), 404

    res = {
        'roleIri': str(role.iri),
        'creator': str(role.creator),
        'created': str(role.created),
        'contributor': str(role.contributor),
        'modified': str(role.modified),
        'roleId': str(role.roleId),
        **({'label': [f'{value}@{lang.name.lower()}' for lang, value in role.label.items()]} if role.label else {}),
        **({'comment': [f'{value}@{lang.name.lower()}' for lang, value in role.comment.items()]} if role.comment else {}),
        'definedByProject': str(role.definedByProject),
    }

    return res, 200


@role_bp.route('/role/<path:definedByProject>/<roleId>', methods=['PUT'])
def create_role(definedByProject, roleId):
    """
    Creates a new role within a specified project. The role is defined based on the provided
    path parameter, `definedByProject`, and a unique identifier, `roleId`. The input data
    must be a valid JSON payload that includes the required fields.

    :param definedByProject: The project in which the role is to be defined.
    :type definedByProject: str
    :param roleId: The unique identifier for the role to be created.
    :type roleId: str
    :raises ConnectionError: Raised when the connection to the directory service fails.
    :raises ValueError: Raised when any validation on the input data or role creation process fails.
    :raises PermissionError: Raised when the user does not have sufficient permissions to create a role.
    :raises ConflictError: Raised when a role with the specified roleId already exists.
    :raises InternalError: Raised when an unexpected error occurs during role creation.
    :return: A JSON response indicating success or failure of the role creation process.
    :rtype: tuple
    """
    known_json_fields = {"label", "comment"}
    mandatory_json_fields = set()
    out = request.headers['Authorization']
    b, token = out.split()

    if request.is_json:

        data = request.get_json()
        unknown_json_field = set(data.keys()) - known_json_fields
        if unknown_json_field:
            return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to create a role. Usable are {known_json_fields}. Aborded operation"}), 400
        if not mandatory_json_fields.issubset(set(data.keys())):
            return jsonify({"message": f"The Fields {mandatory_json_fields} are required to create a role. Used where {set(data.keys())}. Usablable are {known_json_fields}"}), 400
        label = data.get("label", None)
        comment = data.get("comment", None)

        if label == [] or comment == []:
            return jsonify({"message": f"A meaningful label and comment need to be provided and can not be empty"}), 400

        try:
            con = Connection(token=token,
                             context_name="DEFAULT")
        except OldapError as error:
            return jsonify({"message": f"Connection failed: {str(error)}"}), 403
        try:
            role = Role(con=con,
                        roleId=roleId,
                        label=LangString(label),
                        comment=LangString(comment),
                        definedByProject=definedByProject,
                        validate=True)
            role.create()
        except OldapErrorValue as error:
            return jsonify({'message': str(error)}), 400
        except OldapErrorNoPermission as error:
            return jsonify({'message': str(error)}), 403
        except OldapErrorAlreadyExists as error:
            return jsonify({'message': str(error)}), 409
        except OldapError as error:  # should not be reachable
            return jsonify({'message': str(error)}), 500

        return jsonify({"message": "Role successfully created"}), 200
    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400


@role_bp.route('/role/<path:definedByProject>/<roleId>', methods=['GET'])
def read_role(definedByProject, roleId):
    """
    Handles the retrieval of a role from the system using the specified project
    identifier and role ID. This endpoint requires authentication and ensures
    that the role is properly fetched and returned in a structured response
    format.

    :param definedByProject: Identifier of the project defining the role
        (used to uniquely identify the scope of the role).
    :type definedByProject: str
    :param roleId: Unique identifier for the role that needs to be retrieved.
    :type roleId: str
    :return: JSON object containing the role's details, including its metadata
        and associated labels/comments, if available. The response status code
        is 200 upon success.
    :rtype: Tuple[dict, int]

    :raises OldapError: When a connection to the directory service fails.
    :raises OldapErrorValue: When the input parameters are incorrect or invalid.
    :raises OldapErrorNotFound: When the specified role does not exist in the
        system.
    """
    out = request.headers['Authorization']
    b, token = out.split()

    try:
        con = Connection(token=token,
                         context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    try:
        role = Role.read(con=con, roleId=roleId, definedByProject=definedByProject)
    except OldapErrorValue as error:
        return jsonify({'message': str(error)}), 400
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404

    res = {
        'roleIri': str(role.iri),
        'creator': str(role.creator),
        'created': str(role.created),
        'contributor': str(role.contributor),
        'modified': str(role.modified),
        'roleId': str(role.roleId),
        **({'label': [f'{value}@{lang.name.lower()}' for lang, value in role.label.items()]} if role.label else {}),
        **({'comment': [f'{value}@{lang.name.lower()}' for lang, value in role.comment.items()]} if role.comment else {}),
        'definedByProject': str(role.definedByProject),
    }

    return res, 200


@role_bp.route('/role/search', methods=['GET'])
def search_role():
    """
    Handles the role search functionality in the permission set blueprint. This endpoint
    allows searching for roles based on specified criteria provided as query parameters.
    Only the allowed fields are considered in the query parameters, and any unsupported
    fields will result in a 400 Bad Request response.

    :param methods: The HTTP methods allowed for this endpoint.
    :type methods: list
    :return: If successful, returns a JSON response containing the list of role iris
        matching the search criteria with an HTTP 200 status. If an error occurs,
        returns a JSON error message with the appropriate HTTP status code.

    :raises OldapError:
        Raised when there is a connection failure to the LDAP server.
    :raises OldapErrorValue:
        Raised when an invalid value is used in the search query parameters.
    """
    known_json_fields = {"definedByProject", "roledId", "label"}
    out = request.headers['Authorization']
    b, token = out.split()

    if request.args:
        unknown_json_field = set(request.args.keys()) - known_json_fields
    else:
        unknown_json_field = set()
    if unknown_json_field:
        return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to search for a role. Usable are {known_json_fields}. Aborded operation"}), 400

    label = getattr(request, "args", {}).get("label", None)
    roleId = getattr(request, "args", {}).get("roleId", None)
    definedbyproject = getattr(request, "args", {}).get("definedByProject", None)

    try:
        con = Connection(token=token,
                         context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    try:
        roles = Role.search(con=con, label=label, roleId=roleId, definedByProject=definedbyproject)
    except OldapErrorValue as error:
        return jsonify({'message': str(error)}), 400
    return jsonify([str(x) for x in roles]), 200


@role_bp.route('/role/<path:definedByProject>/<roleId>', methods=['DELETE'])
def delete_role(definedByProject, roleId):
    """
    Deletes a role identified by `roleId` and `definedByProject`.

    This endpoint processes DELETE requests to remove a specific role from the system.
    It utilizes the provided authorization token for establishing a connection,
    locating the role, and deleting it. The operation includes multiple error
    handling mechanisms for scenarios such as failed connection, role not found,
    insufficient permissions, and role being in use.

    :param definedByProject: The project identifier under which the role is defined.
    :type definedByProject: str
    :param roleId: The unique identifier of the role to be deleted.
    :type roleId: str
    :return: A JSON response indicating the success or failure of the operation, along with
             appropriate HTTP status codes.
    :rtype: tuple
    """
    out = request.headers['Authorization']
    b, token = out.split()

    try:
        con = Connection(token=token,
                         context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    try:
        role = Role.read(con=con, roleId=roleId, definedByProject=definedByProject)
    except OldapErrorValue as error:
        return jsonify({'message': str(error)}), 400
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404

    try:
        role.delete()
    except OldapErrorNoPermission as error:
        return jsonify({'message': str(error)}), 403
    except OldapErrorInUse as error:  # PermissionSet is still in use (assigned to user or resource)
        return jsonify({'message': str(error)}), 409
    except OldapError as error:  # Should not be reachable!
        return jsonify({'message': str(error)}), 500

    return jsonify({"message": "Role successfully deleted"}), 200


@role_bp.route('/role/<path:definedByProject>/<roleId>', methods=['POST'])
def modify_permissionset(definedByProject, roleId):
    """
    Handles modification of a role's permissionset based on the provided parameters.

    Checks for JSON compliance, validates input fields, and verifies the presence
    of required parameters before processing the role update. Communicates with
    the backend to retrieve, validate, and update the role attributes using the
    received authorization token and role details.

    :param definedByProject: Project namespace the role is defined in
    :type definedByProject: str
    :param roleId: Unique identifier for the role to be modified
    :type roleId: str
    :return: JSON response indicating success or failure of the operation
    :rtype: tuple
    :raises JsonValidationError: If the request body is not in proper JSON format
    :raises FieldValidationError: If unrecognized or missing fields are provided
    :raises AuthorizationError: If connection fails due to an invalid token
    :raises RoleNotFoundError: If the specified role is not found
    :raises PermissionError: If permission to modify the role is denied
    :raises UpdateFailureError: If the update operation fails in unexpected ways
    """
    known_json_fields = {"label", "comment"}
    out = request.headers['Authorization']
    b, token = out.split()

    if request.is_json:
        data = request.get_json()
        unknown_json_field = set(data.keys()) - known_json_fields
        if unknown_json_field:
            return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to modify a role. Usable are {known_json_fields}. Aborded operation"}), 400
        if not set(data.keys()):
            return jsonify({"message": f"At least one field must be given to modify the role. Usablable for the modify-viewfunction are {known_json_fields}"}), 400
        label = data.get("label", "NotSent")
        comment = data.get("comment", "NotSent")

        try:
            con = Connection(token=token,
                             context_name="DEFAULT")
        except OldapError as error:
            return jsonify({"message": f"Connection failed: {str(error)}"}), 403
        try:
            role = Role.read(con=con, roleId=roleId, definedByProject=definedByProject)
        except OldapErrorValue as error:
            return jsonify({'message': str(error)}), 400
        except OldapErrorNotFound as error:
            return jsonify({"message": str(error)}), 404

        try:
            process_langstring(role, RoleAttr.LABEL, label)
            process_langstring(role, RoleAttr.COMMENT, comment)
        except OldapErrorKey as error:
            return jsonify({"message": str(error)}), 400
        except OldapErrorValue as error:
            return jsonify({"message": str(error)}), 400
        except OldapError as error:
            return jsonify({"message": str(error)}), 500

        try:
            role.update()
        except OldapErrorNoPermission as error:
            return jsonify({"message": str(error)}), 403
        except OldapErrorUpdateFailed as error:  # hard to test
            return jsonify({"message": str(error)}), 500
        except OldapError as error:  # should not be reachable
            return jsonify({"message": str(error)}), 500

        return jsonify({"message": "Role updated successfully"}), 200
    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400

@role_bp.route('/role/<path:definedByProject>/<roleId>/in_use', methods=['GET'])
def role_in_use(definedByProject, roleId):
    """
    Provides a REST endpoint to check if a specific role identified by
    `roleId` and scoped under `definedByProject` is currently in use.

    :param str definedByProject: The project scope identifier for the role.
    :param str roleId: The identifier of the role being checked.
    :return: A JSON object indicating whether the role is in use and an HTTP status code.
    :rtype: Tuple[Response, int]

    :raises 403: If connection to the remote server fails.
    :raises 400: If there is a value-related inconsistency in input or operation.
    :raises 404: If the specified role is not found.
    :raises 500: If there is a general connection or operational failure.
    """
    out = request.headers['Authorization']
    b, token = out.split()

    try:
        con = Connection(token=token,
                         context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    try:
        role = Role.read(con=con, roleId=roleId, definedByProject=definedByProject)
    except OldapErrorValue as error:
        return jsonify({'message': str(error)}), 400
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404
    except OldapErrorInconsistency as error:
        return jsonify({'message': str(error)}), 400
    except OldapError as error:
        return jsonify({'message': str(error)}), 500
    try:
        in_use = role.in_use()
    except OldapError as error:
        return jsonify({'message': str(error)}), 500
    return jsonify({"in_use": in_use}), 200
