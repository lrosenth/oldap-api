"""
This script is part of a RESTful API for managing functionalities of oldaplib.
It uses Flask and oldaplib to perform CRUD operations on user, project data, permissionsets and more.
The API offers endpoints for creating, reading, updating, searching and deleting functions to interact with the database.

Available endpoints:
- PUT /admin/project/<projectid>: Creates a new project.
- GET /admin/project/<projectid>: Reads the data of a project.
- DELETE /admin/project/<projectid>: Deletes a project.
- POST /admin/project/<projectid>: Modify the data of a project.
- GET /admin/project/search: Searches for permission sets.

The implementation includes error handling and validation for most operations.
"""

from flask import request, jsonify, Blueprint
from oldaplib.src.connection import Connection
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.enums.projectattr import ProjectAttr
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorNoPermission, OldapErrorAlreadyExists, \
    OldapErrorInconsistency, OldapErrorValue, OldapErrorNotFound, OldapErrorUpdateFailed, OldapErrorKey
from oldaplib.src.project import Project
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_date import Xsd_date
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName

from helpers.process_langstring import process_langstring

project_bp = Blueprint('project', __name__, url_prefix='/admin')


@project_bp.route('/project/<projectid>', methods=['PUT'])
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


@project_bp.route('/project/<projectid>', methods=['DELETE'])
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


@project_bp.route('/project/<projectid>', methods=['GET'])
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
        'projectShortName': str(project.projectShortName),
        'namespaceIri': str(project.namespaceIri),
        'projectStart': str(project.projectStart) if project.projectStart else None,
        'projectEnd': str(project.projectEnd) if project.projectEnd else None
    }
    if project.label:
        res['label'] = [f'{value}@{lang.name.lower()}' for lang, value in project.label.items()]
    if project.comment:
        res['comment'] = [f'{value}@{lang.name.lower()}' for lang, value in project.comment.items()]
    return res, 200

@project_bp.route('/project/get', methods=['GET'])
def get_project_by_iri():
    out = request.headers['Authorization']
    b, token = out.split()
    if not request.args:
        return jsonify({"message": f"Query parameter 'iri' expected – got none"}), 400

    known_query_fields = {"iri"}
    unknown_query_field = set(request.args.keys() - known_query_fields)
    if unknown_query_field:
        return jsonify({"message": f"The Field/s {unknown_query_field} is/are not used to get a user by iri. Use {known_query_fields}. Aborted operation"}), 400
    projectIri = request.args.get('iri', None)

    try:
        con = Connection(server='http://localhost:7200',
                         repo="oldap",
                         token=token,
                         context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    try:
        project = Project.read(con=con, projectIri_SName=Iri(projectIri))
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404
    res = {
        'projectIri': str(project.projectIri),
        'creator': str(project.creator),
        'created': str(project.created),
        'contributor': str(project.contributor),
        'modified': str(project.modified),
        #'label': [f'{value}@{lang.name.lower()}' for lang, value in project.label.items()] if project.label else None,
        #'comment': [f'{value}@{lang.name.lower()}' for lang, value in project.comment.items()] if project.comment else None,
        'projectShortName': str(project.projectShortName),
        'namespaceIri': str(project.namespaceIri),
        'projectStart': str(project.projectStart) if project.projectStart else None,
        'projectEnd': str(project.projectEnd) if project.projectEnd else None
    }
    if project.label:
        res['label'] = [f'{value}@{lang.name.lower()}' for lang, value in project.label.items()]
    if project.comment:
        res['comment'] = [f'{value}@{lang.name.lower()}' for lang, value in project.comment.items()]
    return res, 200


@project_bp.route('/project/search', methods=['GET'])
def search_project():
    """
    Viewfunction to search for a project. It is possible to search for label and comment.
    The query parameters the following form:
    query_string={
        "label": examplelabel,
        "comment": examplecomment
    }
    if no query parameters are provided, a list of all projects is being returned.
    :return: A JSON containing the Iri's about the found projects. It has the following form:
    json={[Iri("http://unittest.org/project/testproject")]}
    """
    out = request.headers['Authorization']
    b, token = out.split()

    known_query_fields = {"label", "comment"}
    if request.args:
        unknown_query_field = set(request.args.keys() - known_query_fields)
        if unknown_query_field:
            return jsonify({"message": f"The Field/s {unknown_query_field} is/are not used to search for a project. Usable are {known_query_fields}. Aborted operation"}), 400
        label = request.args.get('label', None)
        comment = request.args.get('comment', None)
    else:
        label = None
        comment = None

    try:
        con = Connection(server='http://localhost:7200',
                         repo="oldap",
                         token=token,
                         context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    projects = Project.search(con=con, label=label, comment=comment)
    return jsonify([{'projectIri': str(x.projectIri), 'projectShortName': str(x.projectShortName)} for x in projects]), 200


@project_bp.route('/project/<projectid>', methods=['POST'])
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
        projectStart = data.get("projectStart", "NotSent")
        projectEnd = data.get("projectEnd", "NotSent")

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
            process_langstring(project, ProjectAttr.LABEL, label, project.notifier)
            process_langstring(project, ProjectAttr.COMMENT, comment, project.notifier)

            if projectStart != "NotSent":
                if projectStart is None:
                    del project.projectStart
                else:
                    project.projectStart = Xsd_date(projectStart)
            if projectEnd != "NotSent":
                if projectEnd is None:
                    del project.projectEnd
                else:
                    project.projectEnd = Xsd_date(projectEnd)
        except OldapErrorKey as error:
            return jsonify({"message": str(error)}), 400
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


@project_bp.route('/project/getid', methods=['GET'])
def get_projectid():
    """
    Veiwfunction to get the project id from the submitted project iri.
    query_param = {iri:<projectiri>}
    :return: A JSON containing the project id that has the following form:
    json={"id": str(proj_id)}
    """
    out = request.headers['Authorization']
    b, token = out.split()

    if request.args:
        iri = request.args.get('iri')
    else:
        return jsonify({"message": "Please provide a project iri in the arguments"}), 400

    if iri:
        try:
            con = Connection(server='http://localhost:7200',
                             repo="oldap",
                             token=token,
                             context_name="DEFAULT")
        except OldapError as error:
            return jsonify({"message": f"Connection failed: {str(error)}"}), 403

        try:
            proj_id = Project.get_shortname_from_iri(con=con, iri=Iri(iri))
        except OldapErrorValue as error:
            return jsonify({"message": f"OldapErrorValue: {error}"}), 400
        except OldapErrorNotFound as error:
            return jsonify({"message": f"OldapErrorNotFound: {error}"}), 404
        except OldapError as error:
            return jsonify({"message": f"OldapError: {error}"}), 500
        except Exception as error:
            return jsonify({"message": f"Generic exception: {error}"}), 500
        return jsonify({"id": str(proj_id)}), 200

    else:
        return jsonify({"message": f"iri query parameter expected"}), 400

