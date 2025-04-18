import json
from pprint import pprint
from xmlrpc.client import Boolean

from flask import Blueprint, request, jsonify, Response
from oldaplib.src.connection import Connection
from oldaplib.src.enums.language import Language
from oldaplib.src.helpers.json_encoder import SpecialEncoder
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorNoPermission, OldapErrorAlreadyExists, OldapErrorNotFound, OldapErrorValue, OldapErrorInconsistency
from oldaplib.src.oldaplist import OldapList
from oldaplib.src.oldaplist_helpers import get_nodes_from_list
from oldaplib.src.oldaplistnode import OldapListNode
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from requests import delete

from views import known_languages

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
        except OldapErrorNotFound as error:
            return jsonify({'message': str(error)}), 404
        except OldapErrorAlreadyExists as error:
            return jsonify({'message': str(error)}), 409
        except OldapError as error:
            return jsonify({'message': str(error)}), 500 # should not be reachable
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
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404
    except OldapError as error:
        return jsonify({'message': str(error)}), 500 # Should not be reachable

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
        if data["position"] not in {"root", "leftOf", "belowOf", "rightOf"}:
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
                case "rightOf":
                    node.insert_node_right_of(leftnode=refnode)
                case "belowOf":
                    node.insert_node_below_of(parentnode=refnode)
                case "leftOf":
                    node.insert_node_left_of(rightnode=refnode)
                case _:
                    return jsonify({"message": f"Position {position} is not allowed"}), 400 # Should not be reachable
        except OldapErrorNoPermission as error:
            return jsonify({'message': str(error)}), 403
        except OldapErrorAlreadyExists as error:
            return jsonify({'message': str(error)}), 409
        except OldapError as error:
            return jsonify({'message': str(error)}), 500 # should not be reachable
        return jsonify({"message": "Node successfully created"}), 200

    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400


@hierarchical_list_bp.route('/hlist/<project>/<hlistid>/<nodeid>', methods=['DELETE'])
def del_node(project, hlistid, nodeid):
    known_querry_fields = {"recursive"}
    out = request.headers['Authorization']
    b, token = out.split()

    if request.args:
        unknown_json_field = set(request.args.keys()) - known_querry_fields
    else:
        unknown_json_field = set()
    if unknown_json_field:
        return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to delete a node in a hlist. Usable are {known_querry_fields}. Aborded operation"}), 400

    # recursive = getattr(request, "args", {}).get("recursive", None)
    truthvalues = {"true", "1", "yes", "on"}
    recursive = getattr(request, "args", {}).get("recursive", "false").lower() in truthvalues

    try:
        con = Connection(server='http://localhost:7200',
                         repo="oldap",
                         token=token,
                         context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    if recursive is False:
        try:
            hlist = OldapList.read(con=con, project=project,  oldapListId=hlistid)
            node = OldapListNode.read(con=con, oldapList=hlist, oldapListNodeId=nodeid)
            node.delete_node()
        except OldapErrorNoPermission as error:
            return jsonify({"message": str(error)}), 403
        except OldapErrorNotFound as error:
            return jsonify({"message": str(error)}), 404
        except OldapErrorInconsistency as error:
            return jsonify({"message": str(error)}), 409
        except OldapError as error:  # should not be reachable
            return jsonify({"message": str(error)}), 500
    elif recursive is True:
        try:
            hlist = OldapList.read(con=con, project=project,  oldapListId=hlistid)
            nodetodel = OldapListNode.read(con=con, oldapList=hlist, oldapListNodeId=nodeid)
            nodetodel.delete_node_recursively()
        except OldapErrorNoPermission as error:
            return jsonify({"message": str(error)}), 403
        except OldapErrorNotFound as error:
            return jsonify({"message": str(error)}), 404
        except OldapErrorInconsistency as error:
            return jsonify({"message": str(error)}), 409 # should not be reachable
        except OldapError as error:  # should not be reachable
            return jsonify({"message": str(error)}), 500

    return jsonify({"message": "Node successfully deleted"}), 200


@hierarchical_list_bp.route('/hlist/<project>/<hlistid>/<nodeid>/move', methods=['POST'])
def move_node(project, hlistid, nodeid):
    known_json_fields = {"leftOf", "belowOf", "rightOf"}
    out = request.headers['Authorization']
    b, token = out.split()

    if request.is_json:
        data = request.get_json()
        unknown_json_field = set(data.keys()) - known_json_fields
        if unknown_json_field:
            return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to create a root node. Usable are {known_json_fields}. Aborded operation"}), 400
        if not set(data.keys()):
            return jsonify({"message": f"At least one field must be given to move a node. Usable for the move-viewfunction are {known_json_fields}"}), 400
        if len(data.keys()) > 1:
            return jsonify({"message": f"Only one field can be given to move a node. Used where {set(data.keys())}. Usablable for the move-viewfunction is only one of {known_json_fields}"}), 400

    try:
        con = Connection(server='http://localhost:7200',
                         repo="oldap",
                         token=token,
                         context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    leftOf = data.get("leftOf", None)
    belowOf = data.get("belowOf", None)
    rightOf = data.get("rightOf", None)
    targetnodeid = data[next(iter(data))]

    try:
        hlist = OldapList.read(con=con, project=project, oldapListId=hlistid)
        nodetomove = OldapListNode.read(con=con, oldapList=hlist, oldapListNodeId=nodeid)
        targetnode = OldapListNode.read(con=con, oldapList=hlist, oldapListNodeId=targetnodeid)
    except OldapErrorNotFound as error:
        return jsonify({"message": str(error)}), 404
    except OldapError as error:
        return jsonify({"message": str(error)}), 500 # Should not be reachable

    try:
        if leftOf:
            nodetomove.move_node_left_of(con=con, rightnode=targetnode)
        elif belowOf:
            nodetomove.move_node_below(con=con, target=targetnode)
        elif rightOf:
            nodetomove.move_node_right_of(con=con, leftnode=targetnode)
        else:
            return jsonify({"message": f"Something that should not have went wrong!No valid field given to move a node. Should not be reachable!!"}), 400 # Should not be reachable
    except OldapErrorNoPermission as error:
        return jsonify({"message": str(error)}), 403
    except OldapErrorInconsistency as error:
        return jsonify({"message": str(error)}), 409
    except OldapError as error:
        return jsonify({"message": str(error)}), 500 # should not be reachable
    return jsonify({"message": "Node successfully moved"}), 200


@hierarchical_list_bp.route('/hlist/<project>/<hlistid>/<nodeid>', methods=['POST'])
def modify_node(project, hlistid, nodeid):
    known_json_fields = {"prefLabel", "definition"}
    out = request.headers['Authorization']
    b, token = out.split()

    if request.is_json:
        data = request.get_json()
        unknown_json_field = set(data.keys()) - known_json_fields
        if unknown_json_field:
            return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to create a root node. Usable are {known_json_fields}. Aborded operation"}), 400
        if not set(data.keys()):
            return jsonify({"message": f"At least one field must be given to move a node. Usable for the move-viewfunction are {known_json_fields}"}), 400

    try:
        con = Connection(server='http://localhost:7200',
                         repo="oldap",
                         token=token,
                         context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    try:
        hlist = OldapList.read(con=con, project=project, oldapListId=hlistid)
        nodetochange = OldapListNode.read(con=con, oldapList=hlist, oldapListNodeId=nodeid)
    except OldapErrorNotFound as error:
        return jsonify({"message": str(error)}), 404
    except OldapError as error:
        return jsonify({"message": str(error)}), 500 # Should not be reachable


    for attrname, attrval in data.items():
        if attrname == "prefLabel" or attrname == "definition":
            if isinstance(attrval, list):
                if not attrval:
                    return jsonify({"message": f"Using an empty list is not allowed in the modify"}), 400
                for item in attrval:
                    if item is None:
                        return jsonify({"message": f"Using a None in a modifylist is not allowed"}), 400
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
                try:
                    setattr(nodetochange, attrname, LangString(attrval))
                except OldapErrorValue as error:
                    return jsonify({"message": str(error)}), 404
            elif isinstance(attrval, dict):
                if not attrval:
                    return jsonify({"message": f"Using an empty dict is not allowed in the modify"}), 400
                if not set(attrval.keys()).issubset({"add", "del"}):
                    return jsonify({"message": f"The sended command (keyword in dict) is not known"}), 400
                if "add" in attrval:
                    adding = attrval.get("add", [])
                    if not isinstance(adding, list):
                        return jsonify({"message": "The given attributes in add and del must be in a list"}), 400
                    if not adding:
                        return jsonify({"message": f"Using an empty list is not allowed in the modify"}), 400
                    languagecounter = []
                    for item in adding:
                        if item is None:
                            return jsonify({"message": f"Using a None in a modifylist is not allowed"}), 400
                        try:
                            if item[-3] != '@':
                                return jsonify({"message": f"Please add a correct language tags e.g. @de"}), 400
                        except IndexError as error:
                            return jsonify({"message": f"Please add a correct language tags e.g. @de"}), 400
                        lang = item[-2:].upper()
                        if lang in languagecounter:
                            return jsonify({"message": "It is only allowed to have one entry per language"}), 404
                        else:
                            languagecounter.append(lang)
                        try:
                            getattr(nodetochange, attrname)[Language[lang]] = item[:-3]
                        except KeyError as error:
                            return jsonify({"message": f"{lang} is not a valid language. Supportet are {known_languages}"}), 400
                if "del" in attrval:
                    deleting = attrval.get("del", [])
                    if not isinstance(deleting, list):
                        return jsonify({"message": "The given attributes in add and del must be in a list"}), 400
                    if not deleting:
                        return jsonify({"message": f"Using an empty list is not allowed in the modify"}), 400
                    for item in deleting:
                        if item is None:
                            return jsonify({"message": f"Using a None in a modifylist is not allowed"}), 400
                        try:
                            if item[-3] != '@':
                                return jsonify({"message": f"Please add a correct language tags e.g. @de"}), 400
                        except IndexError as error:
                            return jsonify({"message": f"Please add a correct language tags e.g. @de"}), 400
                        lang = item[-2:].upper()
                        try:
                            del property[PropClassAttr.from_name(str(attrname))][Language[lang]]
                        except KeyError as error:
                            return jsonify({"message": f"{lang} is not a valid language. Supportet are {known_languages}"}), 400
                        except TypeError as error:
                            return jsonify({"message": f"The entry {attrval} is not in the datamodel and thus could not be deleted"}), 404
            elif attrval is None:
                delattr(property, attrname)
            else:
                return jsonify({"message": f"To modify {attrname} accepted is either a list, dict or None. Received {type(attrname).__name__} instead."}), 400
            continue
        if attrval is None:
            delattr(property, attrname)
        continue

    # if prefLabel:
    #     try:
    #         nodetochange.prefLabel = LangString(prefLabel)
    #     except OldapErrorValue as error:
    #         return jsonify({"message": str(error)}), 404
    #     except OldapError as error:
    #         return jsonify({"message": str(error)}), 500 # Should not be reachable
    #
    # if definition:
    #     try:
    #         nodetochange.definition = LangString(definition)
    #     except OldapErrorValue as error:
    #         return jsonify({"message": str(error)}), 404
    #     except OldapError as error:
    #         return jsonify({"message": str(error)}), 500  # Should not be reachable

    try:
        nodetochange.update()
    except OldapErrorNoPermission as error:
        return jsonify({"message": str(error)}), 403
    except OldapError as error:
        return jsonify({"message": str(error)}), 500  # Should not be reachable

    return jsonify({"message": "Node successfully modified"}), 200



