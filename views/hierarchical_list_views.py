from flask import Blueprint, request, jsonify
from oldaplib.src.connection import Connection
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorNoPermission, OldapErrorAlreadyExists, OldapErrorNotFound, OldapErrorValue
from oldaplib.src.oldaplist import OldapList
from oldaplib.src.oldaplist_helpers import get_list
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName

hierarchical_list_bp = Blueprint('hlist', __name__, url_prefix='/admin')


@hierarchical_list_bp.route('/hlist/<project>/<hlistid>', methods=['PUT'])
def create_empty_hlist(project, hlistid):
    known_json_fields = {"label", "definition"}
    mandatory_json_fields = {"label"}

    out = request.headers['Authorization']
    b, token = out.split()

    if request.is_json:
        data = request.get_json()
        unknown_json_field = set(data.keys()) - known_json_fields
        if unknown_json_field:
            return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to create a project. Usable are {known_json_fields}. Aborded operation"}), 400
        if not mandatory_json_fields.issubset(set(data.keys())):
            return jsonify({"message": f"The Fields {mandatory_json_fields} are required to create a user. Used where {set(data.keys())}. Usablable are {known_json_fields}"}), 400
        label = data.get("label", None)
        definition = data.get('definition', None)

        if label == []:
            return jsonify({"message": f"A meaningful label and comment need to be provided and can not be empty"}), 400

        try:
            con = Connection(server='http://localhost:7200',
                             repo="oldap",
                             token=token,
                             context_name="DEFAULT")
        except OldapError as error:
            return jsonify({"message": f"Connection failed: {str(error)}"}), 403

        try:
            hlist = OldapList(con=con,
                              project=project,
                              oldapListId=Xsd_NCName(hlistid),
                              prefLabel=LangString(label),
                              definition=LangString(definition))
            hlist.create()

        except OldapErrorNoPermission as error:
            return jsonify({'message': str(error)}), 403
        except OldapErrorAlreadyExists as error:
            return jsonify({'message': str(error)}), 409
        except OldapErrorValue as error:
            return jsonify({'message': str(error)}), 404
        except OldapError as error:
            return jsonify({'message': str(error)}), 500
        return jsonify({"message": "Hierarchical list successfully created"}), 200
    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400

@hierarchical_list_bp.route('/hlist/<project>/<hlistid>', methods=['GET'])
def read_hlist(project, hlistid):
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
        hlist = get_list(con=con, project=project, oldapListId=Xsd_NCName(hlistid))
    except OldapErrorValue as error:
        return jsonify({'message': str(error)}), 404
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404

    return jsonify(hlist), 200



