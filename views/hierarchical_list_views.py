import json

from flask import Blueprint, request, jsonify, Response
from oldaplib.src.connection import Connection
from oldaplib.src.helpers.json_encoder import SpecialEncoder
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorNoPermission, OldapErrorAlreadyExists, OldapErrorNotFound, OldapErrorValue
from oldaplib.src.oldaplist import OldapList
from oldaplib.src.oldaplist_helpers import get_nodes_from_list
from oldaplib.src.oldaplistnode import OldapListNode
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from requests import delete

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
            return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to create a hierarchical list. Usable are {known_json_fields}. Aborded operation"}), 400
        if not mandatory_json_fields.issubset(set(data.keys())):
            return jsonify({"message": f"The Fields {mandatory_json_fields} are required to create a hierarchical list. Used where {set(data.keys())}. Usablable are {known_json_fields}"}), 400
        label = data.get("label", None)
        definition = data.get('definition', None)

        if label == [] or definition == []:
            return jsonify({"message": f"A meaningful label and definition need to be provided and can not be empty"}), 400

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
        oldaplist = OldapList.read(con=con, project=project, oldapListId=Xsd_NCName(hlistid))
        hlist = get_nodes_from_list(con=con, oldapList=oldaplist)
    except OldapErrorValue as error:
        return jsonify({'message': str(error)}), 404
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404

    #return json.dumps(hlist, cls=SpecialEncoder), 200
    return Response(json.dumps(hlist, cls=SpecialEncoder), mimetype="application/json"), 200

@hierarchical_list_bp.route('/hlist/<project>/<hlistid>/<nodeid>', methods=['PUT'])
def add_node(project, hlistid, nodeid):
    known_json_fields = {"label", "definition", "position", "refnode"}
    mandatory_json_fields = {"label", "position"}

    out = request.headers['Authorization']
    b, token = out.split()

    if request.is_json:
        data = request.get_json()
        unknown_json_field = set(data.keys()) - known_json_fields
        if unknown_json_field:
            return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to create a root node. Usable are {known_json_fields}. Aborded operation"}), 400
        if not mandatory_json_fields.issubset(set(data.keys())):
            return jsonify({"message": f"The Fields {mandatory_json_fields} are required to create a root node. Used where {set(data.keys())}. Usablable are {known_json_fields}"}), 400
        if data["position"] not in {"root", "left", "below", "right"}:
            return jsonify({"message": f"Position {data["position"]} is not allowed. Must be either root, left, below or right"}), 400
        if data["position"] != "root":
            if data.get("refnode", None) is None:
                return jsonify({"message": f"Position {data["position"]} requires a refnode -- which is missing"}), 400
        label = data.get("label", None)
        definition = data.get('definition', None)
        position = data.get("position", None)
        refnodeId = data.get("refnode", None)


        if label == [] or definition == []:
            return jsonify({"message": f"A meaningful label and definition need to be provided and can not be empty"}), 400

        try:
            con = Connection(server='http://localhost:7200',
                             repo="oldap",
                             token=token,
                             context_name="DEFAULT")
        except OldapError as error:
            return jsonify({"message": f"Connection failed: {str(error)}"}), 403


        try:
            oldaplist = OldapList.read(con=con, project=project, oldapListId=Xsd_NCName(hlistid))

            refnode: OldapListNode | None = None
            if refnodeId:
                refnode = OldapListNode.read(con=con, oldapList=oldaplist, oldapListNodeId=refnodeId)

        except OldapErrorNotFound as error:
            return jsonify({"message": str(error)}), 404
        except OldapError as error:  # should not be reachable
            return jsonify({"message": str(error)}), 500

        try:
            node = OldapListNode(con=con,
                              oldapList=oldaplist,
                              oldapListNodeId=Xsd_NCName(nodeid),
                              prefLabel=LangString(label),
                              definition=LangString(definition))
            match position:
                case "root":
                    node.create_root_node()
                case "right":
                    node.insert_node_right_of(leftnode=refnode)
                case "below":
                    node.insert_node_below_of(parentnode=refnode)
                case "left":
                    node.insert_node_left_of(rightnode=refnode)
                case _:
                    return jsonify({"message": f"Position {position} is not allowed"}), 400
        except OldapErrorNoPermission as error:
            return jsonify({'message': str(error)}), 403
        except OldapErrorAlreadyExists as error:
            return jsonify({'message': str(error)}), 409
        except OldapErrorValue as error:
            return jsonify({'message': str(error)}), 404
        except OldapError as error:
            return jsonify({'message': str(error)}), 500
        return jsonify({"message": "Root node successfully created"}), 200

    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400


@hierarchical_list_bp.route('/hlist/<project>/<hlistid>/<nodeid>', methods=['DELETE'])
def del_node(project, hlistid, nodeid):
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
        hlist = OldapList.read(con=con, project=project,  oldapListId=hlistid)
        node = OldapListNode.read(con=con, oldapList=hlist, oldapListNodeId=nodeid)
        node.delete_node()
    except OldapErrorNoPermission as error:
        return jsonify({"message": str(error)}), 403
    except OldapErrorNotFound as error:
        return jsonify({"message": str(error)}), 404
    except OldapError as error:  # should not be reachable
        return jsonify({"message": str(error)}), 500

    return jsonify({"message": "Node successfully deleted"}), 200

