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
from flask import request, jsonify, Blueprint
from oldaplib.src.connection import Connection
from oldaplib.src.enums.datapermissions import DataPermission
from oldaplib.src.enums.language import Language
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorNoPermission, OldapErrorAlreadyExists, \
    OldapErrorValue, OldapErrorNotFound, OldapErrorUpdateFailed
from oldaplib.src.permissionset import PermissionSet

from views import known_languages

permset_bp = Blueprint('permissionset', __name__, url_prefix='/admin')



@permset_bp.route('/permissionset/<definedByProject>/<permissionsetid>', methods=['PUT'])
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


@permset_bp.route('/permissionset/<definedbyproject>/<permissionsetid>', methods=['GET'])
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


@permset_bp.route('/permissionset/search', methods=['GET'])
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


@permset_bp.route('/permissionset/<definedbyproject>/<permissionsetid>', methods=['DELETE'])
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


@permset_bp.route('/permissionset/<definedbyproject>/<permissionsetid>', methods=['POST'])
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
                        lang = item[-2:].upper()
                        try:
                            Language[lang]
                        except KeyError as error:
                            return jsonify({"message": f"{lang} is not a valid language. Supportet are {known_languages}"}), 400

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
                        lang = item[-2:].upper()
                        try:
                            Language[lang]
                        except KeyError as error:
                            return jsonify({"message": f"{lang} is not a valid language. Supportet are {known_languages}"}), 400
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
