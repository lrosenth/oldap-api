import json
import os
import tempfile
from pathlib import Path

from flask import Blueprint, request, jsonify, Response, current_app
from oldaplib.src.connection import Connection
from oldaplib.src.enums.oldaplistattr import OldapListAttr
from oldaplib.src.enums.oldaplistnodeattr import OldapListNodeAttr
from oldaplib.src.helpers.json_encoder import SpecialEncoder
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorNoPermission, OldapErrorAlreadyExists, \
    OldapErrorNotFound, OldapErrorValue, OldapErrorInconsistency, OldapErrorKey, OldapErrorUpdateFailed, \
    OldapErrorInUse, OldapErrorNotImplemented
from oldaplib.src.oldaplist import OldapList
from oldaplib.src.oldaplist_helpers import load_list_from_yaml, dump_list_to, ListFormat
from oldaplib.src.oldaplistnode import OldapListNode
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName

from oldap_api.helpers.process_langstring import process_langstring

hierarchical_list_bp = Blueprint('hlist', __name__, url_prefix='/admin')


@hierarchical_list_bp.route('/hlist/<project>/upload', methods=['POST'])
def upload_yaml_hlist(project):
    """
    Viewfunction to upload a hierarchical list from a YAML file.
    :param project: The project where the hierarchical list should be uploaded to.
    :return: A JSON to denote the success of the operation that has the following form:
    json={"message": "File successfully uploaded"}
    """
    out = request.headers['Authorization']
    b, token = out.split()

    file = request.files.get("yamlfile")
    if file is None or file.filename == "":
        return jsonify({"message": "No file was sent"}), 400
    if not file.filename.endswith(".yaml"):
        return jsonify({"message": "Only YAML files (ending with \".yaml\" are allowed"}), 400

    try:
        con = Connection(server='http://localhost:7200',
                         repo="oldap",
                         token=token,
                         context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403
    tmpfile = tempfile.mktemp(prefix="OLDAP_", dir=current_app.config['TMP_FOLDER'])
    file.save(tmpfile)
    try:
        load_list_from_yaml(con=con, project=project, filepath=Path(tmpfile))
    except OldapErrorValue as error:
        return jsonify({"message": str(error)}), 400
    except OldapErrorNoPermission as error:
        return jsonify({"message": str(error)}), 403
    except OldapError as error:
        #file.delete()
        if os.path.exists(tmpfile):
            os.remove(tmpfile)
        return jsonify({"message": f"File could not be uploaded: {error}"}), 400
    if os.path.exists(tmpfile):
        os.remove(tmpfile)
    return jsonify({"message": "File successfully uploaded"}), 200


@hierarchical_list_bp.route('/hlist/<project>/<hlistid>', methods=['PUT'])
def create_empty_hlist(project, hlistid):
    """
    Viewfunction to create an empty hierarchical list. A JSON is expected that has the following form.
    json={
        "prefLabel": ["testlabel@en"],
        "definition": ["testdefinition@en"]
    }
    :param project: The project where the hierarchical list should be created
    :param hlistid: The id of the hierarchical list
    :return: A JSON to denote the success of the operation that has the following form:
    json={"message": "Hierarchical list successfully created"}
    """
    known_json_fields = {"prefLabel", "definition"}
    mandatory_json_fields = {"prefLabel"}

    out = request.headers['Authorization']
    b, token = out.split()

    if request.is_json:
        data = request.get_json()
        unknown_json_field = set(data.keys()) - known_json_fields
        if unknown_json_field:
            return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to create a hierarchical list. Usable are {known_json_fields}. Aborded operation"}), 400
        if not mandatory_json_fields.issubset(set(data.keys())):
            return jsonify({"message": f"The Fields {mandatory_json_fields} are required to create a hierarchical list. Used where {set(data.keys())}. Usablable are {known_json_fields}"}), 400
        prefLabel = data.get("prefLabel", None)
        definition = data.get('definition', None)

        if prefLabel == [] or definition == []:
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
                              prefLabel=LangString(prefLabel),
                              definition=LangString(definition))
            hlist.create()
        except OldapErrorValue as error:
            return jsonify({"message": str(error)}), 400
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
    """
    Viewfunction to read an existing hierarchical list.
    :param project: The project where the hierarchical list should be created
    :param hlistid: The id of the hierarchical list
    :return: A list containing the ordered node structure of the hierarchical list e.g.
    [{'contributor': 'https://orcid.org/0000-0003-1681-4036',
      'created': '2025-04-25T17:39:56.637331+02:00',
      'creator': 'https://orcid.org/0000-0003-1681-4036',
      'definition': ['testrootnodedefinition@en'],
      'modified': '2025-04-25T17:39:56.637331+02:00',
      'oldapListNodeId': 'nodeA',
      'prefLabel': ['testrootnodelabel@en']},
      {'contributor': 'https://orcid.org/0000-0003-1681-4036',
                        'created': '2025-04-25T17:39:57.974365+02:00',
                        'creator': 'https://orcid.org/0000-0003-1681-4036',
                        'definition': ['testrootnodedefinition@en'],
                        'modified': '2025-04-25T17:39:57.974365+02:00',
                        'nodes': [{'contributor': 'https://orcid.org/0000-0003-1681-4036',
                                   'created': '2025-04-25T17:39:58.331659+02:00',
                                   'creator': 'https://orcid.org/0000-0003-1681-4036',
                                   'definition': ['testrootnodedefinition@en'],
                                   'modified': '2025-04-25T17:39:58.331659+02:00',
                                   'oldapListNodeId': 'nodeBA',
                                   'prefLabel': ['testrootnodelabel@en']}],
                        'oldapListNodeId': 'nodeB',
                        'prefLabel': ['testrootnodelabel@en']},
    ]
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
        oldaplist = OldapList.read(con=con, project=project, oldapListId=hlistid)
        hlist = oldaplist.get_nodes_from_list()
        oldaplist.nodes = hlist
    except OldapErrorValue as error:
        return jsonify({"message": str(error)}), 400
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404
    except OldapError as error:
        return jsonify({'message': str(error)}), 500 # Should not be reachable

    #return json.dumps(hlist, cls=SpecialEncoder), 200
    return Response(json.dumps(oldaplist, cls=SpecialEncoder), mimetype="application/json"), 200

@hierarchical_list_bp.route('/hlist/<project>/<hlistid>', methods=['POST'])
def modify_hlist(project, hlistid):
    """

    :param project:
    :param hlistid:
    :return:
    """
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
    except OldapErrorValue as error:
        return jsonify({"message": str(error)}), 400
    except OldapErrorNotFound as error:
        return jsonify({"message": str(error)}), 404
    except OldapError as error:
        return jsonify({"message": str(error)}), 500 # Should not be reachable

    for attrname, attrval in data.items():
        if attrname == "prefLabel":
            try:
                process_langstring(hlist, OldapListAttr.PREF_LABEL, attrval, hlist.notifier)
            except (OldapErrorKey, OldapErrorValue, OldapErrorInconsistency) as error:
                return jsonify({"message": str(error)}), 400
            except OldapError as error:
                return jsonify({"message": str(error)}), 500
            continue

        if attrname == "definition":
            try:
                process_langstring(hlist, OldapListAttr.DEFINITION, attrval, hlist.notifier)
            except (OldapErrorKey, OldapErrorValue, OldapErrorInconsistency) as error:
                return jsonify({"message": str(error)}), 400
            except OldapError as error:
                return jsonify({"message": str(error)}), 500
            continue

        if attrval is None:
            delattr(property, attrname)
        continue

    try:
        hlist.update()
    except OldapErrorNoPermission as error:
        return jsonify({"message": str(error)}), 403
    except OldapError as error:
        return jsonify({"message": str(error)}), 500  # Should not be reachable

    return jsonify({"message": "Node successfully modified"}), 200


@hierarchical_list_bp.route('/hlist/<project>/<hlistid>', methods=['DELETE'])
def delete_hlist(project, hlistid):
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
        oldaplist = OldapList.read(con=con, project=project, oldapListId=hlistid)
        oldaplist.delete()
    except OldapErrorValue as error:
        return jsonify({"message": str(error)}), 400
    except OldapErrorNoPermission as error:
        return jsonify({'message': str(error)}), 403
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404
    except OldapErrorInUse as error:
        return jsonify({'message': str(error)}), 409
    except OldapError as error:  # Should not be reachable!
        return jsonify({'message': str(error)}), 500
    return jsonify({"message": "Hierarchical list successfully deleted"}), 200


@hierarchical_list_bp.route('/hlist/search', methods=['GET'])
def hlist_search():
    out = request.headers['Authorization']
    b, token = out.split()

    known_query_fields = {"project", "hlist", "prefLabel", "definition", "exactMatch"}

    if request.args:
        unknown_query_field = set(request.args.keys() - known_query_fields)
    else:
        unknown_query_field = set()
    if unknown_query_field:
        return jsonify({"message": f"The Field/s {unknown_query_field} is/are not used to search for hlists. Usable are {known_query_fields}. Aborted operation"}), 400
    project = request.args.get('project', None)
    hlist = request.args.get('hlist', None)
    prefLabel = request.args.get('prefLabel', None)
    definition = request.args.get('definition', None)
    exactMatch = request.args.get('exactMatch', False)

    try:
        con = Connection(server='http://localhost:7200',
                         repo="oldap",
                         token=token,
                         context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    try:
        hlists = OldapList.search(con=con,
                                  project=project,
                                  id=hlist,
                                  prefLabel=prefLabel,
                                  definition=definition,
                                  exactMatch=exactMatch)
    except OldapErrorValue as error:
        return jsonify({"message": str(error)}), 400
    except OldapError as error:
        return jsonify({"message": f"Search failed: {str(error)}"}), 500
    return jsonify([str(x) for x in hlists]), 200


@hierarchical_list_bp.route('/hlist/get', methods=['GET'])
def hlist_get_by_iri():
    out = request.headers['Authorization']
    b, token = out.split()
    if not request.args:
        return jsonify({"message": f"Query parameter 'iri' expected – got none"}), 400

    known_query_fields = {"iri"}
    unknown_query_field = set(request.args.keys() - known_query_fields)
    if unknown_query_field:
        return jsonify({"message": f"The Field/s {unknown_query_field} is/are not used to get a user by iri. Use {known_query_fields}. Aborted operation"}), 400
    hlistIri = request.args.get('iri', None)
    [projectId, hlistId] = hlistIri.split(":")

    try:
        con = Connection(server='http://localhost:7200',
                         repo="oldap",
                         token=token,
                         context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    try:
        hlist = OldapList.read(con=con, project=projectId, oldapListId=hlistId)
    except OldapErrorNotFound as error:
        return jsonify({"message": f'Hlist {hlistIri} not found'}), 404
    except OldapError as error:
        return jsonify({"message": f'Error reading {hlistIri}'}), 400

    # Building the response json
    answer = {
        "oldapListId": str(hlist.oldapListId),
        "iri": str(hlist.iri),
        "creator": str(hlist.creator),
        "created": str(hlist.created),
        "contributor": str(hlist.contributor),
        "modified": str(hlist.modified),
        "nodeNamespaceIri": str(hlist.node_namespaceIri),
        "nodeClassIri": str(hlist.node_classIri),
    }
    if hlist.prefLabel:
        answer['prefLabel'] = [f'{value}@{lang.name.lower()}' for lang, value in hlist.prefLabel.items()]
    if hlist.definition:
        answer['definition'] = [f'{value}@{lang.name.lower()}' for lang, value in hlist.definition.items()]

    return jsonify(answer), 200

@hierarchical_list_bp.route('/hlist/<project>/<hlistid>/download', methods=['GET'])
def hlist_download(project, hlistid):
    out = request.headers['Authorization']
    b, token = out.split()

    format = ListFormat.YAML
    mimetype = "application/x-yaml"
    extension = "yaml"
    if request.args:
        formatstr = request.args.get('format', None)
        if formatstr.upper() == "YAML":
            pass
        elif formatstr.upper() == "JSON":
            format = ListFormat.JSON
            mimetype = "application/json"
            extension = "json"
        else:
            raise OldapErrorNotImplemented(f"Format {formatstr} not implemented! Must be YAML or JSON.")
    try:
        con = Connection(server='http://localhost:7200',
                         repo="oldap",
                         token=token,
                         context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403
    try:
        hlist = OldapList.read(con=con, project=project, oldapListId=hlistid)
        hlist_str = dump_list_to(con=con, project=project,oldapListId=hlistid,listformat=ListFormat.YAML)
    except OldapErrorValue as error:
        return jsonify({"message": str(error)}), 400
    except OldapErrorNoPermission as error:
        return jsonify({'message': str(error)}), 403
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404
    except OldapError as error:  # Should not be reachable!
        return jsonify({'message': str(error)}), 500
    except Exception as error:
        return jsonify({'message': str(error)}), 500
    return Response(
        hlist_str,
        mimetype='application/x-yaml',
        headers={ 'Content-Disposition': f'attachment; filename="{hlist.oldapListId}.{extension}"' })


@hierarchical_list_bp.route('/hlist/<project>/<hlistid>/in_use', methods=['GET'])
def hlist_is_in_use(project, hlistid):
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
    except OldapErrorValue as error:
        return jsonify({"message": str(error)}), 400
    except OldapErrorNoPermission as error:
        return jsonify({'message': str(error)}), 403
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404
    except OldapError as error:  # Should not be reachable!
        return jsonify({'message': str(error)}), 500
    try:
        in_use = oldaplist.in_use()
    except OldapError as error:
        return jsonify({'message': str(error)}), 500
    return jsonify({"in_use": in_use}), 200

@hierarchical_list_bp.route('/hlist/<project>/<hlistid>/<nodeid>', methods=['GET'])
def get_node(project, hlistid, nodeid):
    """
    Get a node with a given node ID
    :param project: Shortname of the project where the list is attched to
    :param hlistid: Name of the hierarchical list
    :param nodeid: ID of the node
    :return: A JSON of the form
      {
        'nodeid': "nodeA",
        'created': '2025-04-25T17:39:56.637331+02:00',
        'creator': 'https://orcid.org/0000-0003-1681-4036',
        'definition': ['testrootnodedefinition@en'],
        'modified': '2025-04-25T17:39:56.637331+02:00',
        'prefLabel': ['testrootnodelabel@en', ...],
        'definition': ['testrootnodedefinition@en', ...]
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
        hlist = OldapList.read(con=con, project=project, oldapListId=hlistid)
        node = OldapListNode.read(con=con,
                                  **hlist.info,
                                  oldapListNodeId=nodeid)
    except OldapErrorValue as error:
        return jsonify({"message": str(error)}), 400
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404
    except OldapError as error:
        return jsonify({'message': str(error)}), 403
    res = {
        'nodeid': str(node.oldapListNodeId),
        'creator': str(node.creator),
        'created': str(node.created),
        'contributor': str(node.contributor),
        'modified': str(node.modified),
        **({'prefLabel': [f'{value}@{lang.name.lower()}' for lang, value in node.prefLabel.items()]} if node.prefLabel else {}),
        **({'definition': [f'{value}@{lang.name.lower()}' for lang, value in node.definition.items()]} if node.definition else {}),
    }
    return res, 200


@hierarchical_list_bp.route('/hlist/<project>/<hlistid>/<nodeid>', methods=['PUT'])
def add_node(project, hlistid, nodeid):
    """
    Viewfunction to add a new node to an existing hierarchical list. A JSON is expected that has the following form.
    Note: if the position is "root", then "refnode" must be omitted. Allowed positions are root, leftOf, rightOf, belowOf.
    json= {
      "prefLabel": ["testrootnodelabel@en"],
      "definition": ["testrootnodedefinition@en"],
      "position": "leftOf",
      "refnode": "nodeA"
    }
    :param project: The project where the hierarchical list is located to add the node to.
    :param hlistid: The id of the hierarchical list
    :param nodeid: the id of the node to add
    :return: A JSON to denote the success of the operation that has the following form:
    json={"message": "Node successfully created"}
    """
    known_json_fields = {"prefLabel", "definition", "position", "refnode"}
    mandatory_json_fields = {"prefLabel", "position"}

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
        prefLabel = data.get("prefLabel", None)
        definition = data.get('definition', None)
        position = data.get("position", None)
        refnodeId = data.get("refnode", None)


        if prefLabel == [] or definition == []:
            return jsonify({"message": f"A meaningful prefLabel and definition need to be provided and can not be empty"}), 400

        try:
            con = Connection(server='http://localhost:7200',
                             repo="oldap",
                             token=token,
                             context_name="DEFAULT")
        except OldapError as error:
            return jsonify({"message": f"Connection failed: {str(error)}"}), 403

        try:
            oldaplist = OldapList.read(con=con, project=project, oldapListId=hlistid)

            refnode: OldapListNode | None = None
            if refnodeId:
                refnode = OldapListNode.read(con=con, **oldaplist.info, oldapListNodeId=refnodeId)
        except OldapErrorValue as error:
            return jsonify({"message": str(error)}), 400
        except OldapErrorNotFound as error:
            return jsonify({"message": str(error)}), 404
        except OldapError as error:  # should not be reachable
            return jsonify({"message": str(error)}), 500

        try:
            node = OldapListNode(con=con,
                                 **oldaplist.info,
                                 oldapListNodeId=Xsd_NCName(nodeid),
                                 prefLabel=LangString(prefLabel),
                                 definition=LangString(definition),
                                 validate=True)
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
        except OldapErrorValue as error:
            return jsonify({"message": str(error)}), 400
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
    """
    Viewfunction that deletes a node from the hierarchical list
    :param project: The project where the node should be deleted
    :param hlistid: The id of the hierarchical list
    :param nodeid: the id of the node to delete
    :return: A JSON to denote the success of the operation that has the following form:
    json={"message": "Node successfully deleted"}
    """
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
            node = OldapListNode.read(con=con, **hlist.info, oldapListNodeId=nodeid)
            node.delete_node()
        except OldapErrorValue as error:
            return jsonify({"message": str(error)}), 400
        except OldapErrorNoPermission as error:
            return jsonify({"message": str(error)}), 403
        except OldapErrorNotFound as error:
            return jsonify({"message": str(error)}), 404
        except OldapErrorInUse as error:
            return jsonify({"message": str(error)}), 409
        except OldapErrorInconsistency as error:
            return jsonify({"message": str(error)}), 409
        except OldapError as error:  # should not be reachable
            return jsonify({"message": str(error)}), 500
    elif recursive is True:
        try:
            hlist = OldapList.read(con=con, project=project,  oldapListId=hlistid)
            nodetodel = OldapListNode.read(con=con, **hlist.info, oldapListNodeId=nodeid)
            nodetodel.delete_node_recursively()
        except OldapErrorValue as error:
            return jsonify({"message": str(error)}), 400
        except OldapErrorNoPermission as error:
            return jsonify({"message": str(error)}), 403
        except OldapErrorNotFound as error:
            return jsonify({"message": str(error)}), 404
        except OldapErrorInUse as error:
            return jsonify({"message": str(error)}), 409
        except OldapErrorInconsistency as error:
            return jsonify({"message": str(error)}), 409
        except OldapError as error:  # should not be reachable
            return jsonify({"message": str(error)}), 500

    return jsonify({"message": "Node successfully deleted"}), 200


@hierarchical_list_bp.route('/hlist/<project>/<hlistid>/<nodeid>/move', methods=['POST'])
def move_node(project, hlistid, nodeid):
    """
    Viewfunction that moves a node inside the hierarchical list from one place to another.
    When there are any number of nodes below the node one wish to move, they get moved automatically alongside the other node. Allowed directions are belowOf, leftOf and rightOf.
    A JSON is expected that has the following form:
    json={
    "direction": "targetnode"
    }
    :param project: The project where the node should be moved
    :param hlistid: The id of the hierarchical list
    :param nodeid: the id of the node to move
    :return: A JSON to denote the success of the operation that has the following form:
    json={"message": "Node successfully moved"}
    """
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
        nodetomove = OldapListNode.read(con=con, **hlist.info, oldapListNodeId=nodeid)
        targetnode = OldapListNode.read(con=con, **hlist.info, oldapListNodeId=targetnodeid)
    except OldapErrorValue as error:
            return jsonify({"message": str(error)}), 400
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
            return jsonify({"message": f"Something that should not have went wrong! No valid field given to move a node. Should not be reachable!!"}), 400 # Should not be reachable
    except OldapErrorValue as error:
        return jsonify({"message": str(error)}), 400
    except OldapErrorNoPermission as error:
        return jsonify({"message": str(error)}), 403
    except OldapErrorInconsistency as error:
        return jsonify({"message": str(error)}), 409
    except OldapError as error:
        return jsonify({"message": str(error)}), 500 # should not be reachable
    return jsonify({"message": "Node successfully moved"}), 200


@hierarchical_list_bp.route('/hlist/<project>/<hlistid>/<nodeid>', methods=['POST'])
def modify_node(project, hlistid, nodeid):
    """

    :param project:
    :param hlistid:
    :param nodeid:
    :return:
    """
    known_json_fields = {"prefLabel", "definition"}
    out = request.headers['Authorization']
    b, token = out.split()

    if request.is_json:
        data = request.get_json()
        unknown_json_field = set(data.keys()) - known_json_fields
        if unknown_json_field:
            return jsonify({"message": f"The Field/s {unknown_json_field} is/are allowed for modifying a node. Usable are {known_json_fields}. Aborded operation"}), 400
        if not set(data.keys()):
            return jsonify({"message": f"At least one field must be given to modify a node. Usable for the modify-viewfunction are {known_json_fields}"}), 400

        prefLabel = data.get("prefLabel", "NotSent")
        definition = data.get("definition", "NotSent")
        try:
            con = Connection(server='http://localhost:7200',
                             repo="oldap",
                             token=token,
                             context_name="DEFAULT")
        except OldapError as error:
            return jsonify({"message": f"Connection failed: {str(error)}"}), 403

        try:
            hlist = OldapList.read(con=con, project=project, oldapListId=hlistid)
            nodetochange = OldapListNode.read(con=con, **hlist.info, oldapListNodeId=nodeid)
        except OldapErrorValue as error:
            return jsonify({"message": str(error)}), 400
        except OldapErrorNotFound as error:
            return jsonify({"message": str(error)}), 404
        except OldapError as error:
            return jsonify({"message": str(error)}), 500 # Should not be reachable

        try:
            process_langstring(nodetochange, OldapListNodeAttr.PREF_LABEL, prefLabel, nodetochange.notifier)
            process_langstring(nodetochange, OldapListNodeAttr.DEFINITION, definition, nodetochange.notifier)
        except OldapErrorKey as error:
            return jsonify({"message": str(error)}), 400
        except OldapErrorValue as error:
            return jsonify({"message": str(error)}), 400
        except OldapErrorInconsistency as error:  # inconsistent start and end
            return jsonify({'message': str(error)}), 400
        except OldapError as error:
            return jsonify({"message": str(error)}), 500

        try:
            nodetochange.update()
        except OldapErrorValue as error:
            return jsonify({"message": str(error)}), 400
        except OldapErrorNoPermission as error:
            return jsonify({"message": str(error)}), 403
        except OldapErrorUpdateFailed as error:  # hard to test
            return jsonify({"message": str(error)}), 500
        except OldapError as error:  # should not be reachable
            return jsonify({"message": str(error)}), 500

        return jsonify({"message": "Node successfully modified"}), 200
    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400





