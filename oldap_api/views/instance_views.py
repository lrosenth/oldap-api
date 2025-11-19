from flask import request, jsonify, Blueprint
from oldaplib.src.connection import Connection
from oldaplib.src.datamodel import DataModel
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorValue, OldapErrorKey, OldapErrorNoPermission, \
    OldapErrorAlreadyExists, OldapErrorNotFound, OldapErrorInUse
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.objectfactory import ResourceInstance, ResourceInstanceFactory, SortBy
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.helpers.context import Context
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName

instance_bp = Blueprint('instance', __name__, url_prefix='/data')

@instance_bp.route('/textsearch/<project>', methods=['GET'])
def textsearch_instance(project):
    known_json_fields = {"searchString", "countOnly", "resclass", "sortBy", "limit", "offset"}
    out = request.headers['Authorization']
    b, token = out.split()

    if request.args:
        unknown_json_field = set(request.args.keys()) - known_json_fields
    else:
        unknown_json_field = set()
    if unknown_json_field:
        return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to search for a permissionset. Usable are {known_json_fields}. Aborded operation"}), 400

    searchString = getattr(request, "args", {}).get("searchString", None)
    countOnly = getattr(request, "args", {}).get("countOnly", None)
    resClass = getattr(request, "args", {}).get("resClass", None)
    sortBy = getattr(request, "args", {}).get("sortBy", None)
    limit = getattr(request, "args", {}).get("limit", None)
    offset = getattr(request, "args", {}).get("offset", None)

    if not searchString:
        return jsonify({"message": "No search string provided"}), 400
    try:
        params: dict[str, Any] = {
            's': str(searchString),
        }
        if countOnly:
            params['countOnly'] = True
        if sortBy:
            if sortBy == "PROPVAL":
                params['sortBy'] = SortBy.PROPVAL
            elif sortBy == "CREATED":
                params['sortBy'] = SortBy.CREATED
            elif sortBy == "LASTMOD":
                params['sortBy'] = SortBy.LASTMOD
            else:
                return jsonify({"message": f'The Field/s {sortBy} is invalid. Usable are "PROPVAL", "CREATED", "LASTMOD". Aborded operation'}), 400
        if resClass:
            params['resClass'] = Xsd_QName(resClass, validate=True)
        if limit:
            params['limit'] = int(limit)
        if offset:
            params['offset'] = int(offset)
    except (OldapErrorValue, OldapError) as error:
        return jsonify({"message": str(error)}), 400

    try:
        con = Connection(token=token,
                         context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    try:
        res = ResourceInstance.search_fulltext(con=con,
                                               projectShortName=Xsd_NCName(project, validate=True),
                                               **params)
    except OldapError as error:
        return jsonify({"message": f"Search failed: {str(error)}"}), 400

    if countOnly:
        return jsonify({"count": res.value}), 200
    else:
        tmp = {str(key): {str(x): str(y) for x, y in value.items()} for key, value in res.items()}
        return jsonify(tmp), 200


@instance_bp.route('/ofclass/<project>', methods=['GET'])
def allofclass_instance(project):
    known_json_fields = {"resClass", "includeProperties", "countOnly", "sortBy", "limit", "offset"}
    out = request.headers['Authorization']
    b, token = out.split()

    if request.args:
        unknown_json_field = set(request.args.keys()) - known_json_fields
    else:
        unknown_json_field = set()
    if unknown_json_field:
        return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to search for a permissionset. Usable are {known_json_fields}. Aborded operation"}), 400

    resClass = getattr(request, "args", {}).get("resClass", None)
    includeProperties = getattr(request, "args", {}).get("includeProperties", None)
    countOnly = getattr(request, "args", {}).get("countOnly", None)
    sortBy = getattr(request, "args", {}).get("sortBy", None)
    limit = getattr(request, "args", {}).get("limit", None)
    offset = getattr(request, "args", {}).get("offset", None)

    if not resClass:
        return jsonify({"message": "No resource class provided"}), 400
    try:
        params: dict[str, Any] = {
            'resClass': Xsd_QName(resClass),
        }
        if includeProperties:
            params['includeProperties'] = [Xsd_QName(x, validate=true) for x in includeProperties] if isinstance(includeProperties,
                                                                                            list) else [
                Xsd_QName(includeProperties, validate=True)]
        if countOnly:
            params['countOnly'] = True
        if sortBy:
            if sortBy == "PROPVAL":
                params['sortBy'] = SortBy.PROPVAL
            elif sortBy == "CREATED":
                params['sortBy'] = SortBy.CREATED
            elif sortBy == "LASTMOD":
                params['sortBy'] = SortBy.LASTMOD
        if limit:
            params['limit'] = int(limit)
        if offset:
            params['offset'] = int(offset)
    except (OldapErrorValue, OldapError) as error:
        return jsonify({"message": str(error)}), 400
    try:
        con = Connection(token=token,
                         context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    try:
        res = ResourceInstance.all_resources(con=con,
                                             projectShortName=Xsd_NCName(project, validate=True),
                                             **params)
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 400

    if countOnly:
        return jsonify({"count": res.value}), 200
    else:
        tmp = {str(key): {str(x): str(y) for x, y in value.items()} for key, value in res.items()}
        return jsonify(tmp), 200




@instance_bp.route('/<project>/<resource>', methods=['PUT'])
def add_instance(project, resource):
    out = request.headers['Authorization']
    b, token = out.split()

    if not request.is_json:
        return jsonify({"message": "Invalid request format, JSON required"}), 400

    try:
        con = Connection(token=token, context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    factory = ResourceInstanceFactory(con=con, project=project)
    instclass = factory.createObjectInstance(resource)

    data = request.get_json()
    if not data:
        return jsonify({"message": "No data provided"}), 400
    try:
        instance = instclass(**data)
    except (OldapErrorValue, OldapErrorKey, OldapError) as error:
        return jsonify({"message": str(error)}), 400
    try:
        instance.create()
    except OldapErrorNoPermission as error:
        return jsonify({"message": str(error)}), 403
    except OldapErrorValue as error:
        return jsonify({"message": str(error)}), 409
    except OldapErrorAlreadyExists as error:
        return jsonify({"message": str(error)}), 409
    except OldapError as error:
        return jsonify({"message": str(error)}), 500
    return jsonify({"message": "Instance successfully created", "iri": str(instance.iri)}), 200

@instance_bp.route('/<project>/<resiri>', methods=['GET'])
def read_instance(project, resiri):
    out = request.headers['Authorization']
    b, token = out.split()

    try:
        con = Connection(token=token, context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    try:
        iri = Iri(resiri, validate=True)
    except OldapErrorValue as error:
        return jsonify({"message": str(error)}), 400
    context = Context(name=con.context_name)
    if not context.get(project):
        return jsonify({"message": f'Project "{project}" not found'}), 404

    query = context.sparql_context
    query += f"SELECT ?resclass FROM {project}:data WHERE {{ {iri.toRdf} a ?resclass }}"
    try:
        jsonres = con.query(query)
    except OldapError as error:
        return jsonify({"message": str(error)}), 500
    res = QueryProcessor(context, jsonres)
    for r in res:
        resource = r['resclass']

    try:
        data = ResourceInstanceFactory.read_data(con=con,
                                                 iri=Iri(resiri, validate=True),
                                                 projectShortName=Xsd_NCName(project, validate=True))
    except OldapErrorValue as error:
        return jsonify({"message": str(error)}), 400
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404
    except OldapError as error:
        return jsonify({'message': str(error)}), 500
    data = {str(x): y for x, y in data.items()}
    return jsonify(data), 200

@instance_bp.route('/<project>/<resiri>', methods=['POST'])
def update_instance(project, resiri):
    """
    Update instance information for a specified project and resource identifier (resiri).

    This route handles the logic for updating instances within the provided
    project and resource identifier. It validates the request format, handles
    authentication via a token, verifies the provided resource identifier, and
    checks the existence of the specified project in the context. Appropriate
    responses are returned based on the success or failure of these operations.
    The JSON passed in the body has the following structure:
    {
        property_qname: null,  // deletes this property
        property_qname: value,  // replaces the existing value with this new value, or creates the property
        property_qname: [value1, value2, ...],  // replaces the existing value with the new values
        property_qname: {"add": "[value1, value2, ...], "del": "[value1, value2, ...]"},  // adds and deletes values},
    }

    :param project: The name of the project to which the instance belongs
    :type project: str
    :param resiri: The resource identifier for the instance to be updated
    :type resiri: str
    :return: JSON response containing a success or error message, along with
        appropriate HTTP status codes
    :rtype: flask.Response
    """
    out = request.headers['Authorization']
    b, token = out.split()

    if not request.is_json:
        return jsonify({"message": "Invalid request format, JSON required"}), 400
    data = request.get_json()
    if not data:
        return jsonify({"message": "No data provided"}), 400

    try:
        con = Connection(token=token, context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    try:
        iri = Iri(resiri, validate=True)
    except OldapErrorValue as error:
        return jsonify({"message": str(error)}), 400
    context = Context(name=con.context_name)
    if not context.get(project):
        return jsonify({"message": f'Project "{project}" not found'}), 404
    try:
        factory = ResourceInstanceFactory(con=con, project=project)
        instance = factory.read(iri)
        for attrname, attrval in data.items():
            attr = Xsd_QName(attrname)
            if attrval is None:
                instance[attr].discard()
            elif isinstance(attrval, list):
                instance[attr].replace(attrval)
            elif isinstance(attrval, dict):
                if "add" in attrval:
                    adding = attrval.get("add", [])
                    if adding and not isinstance(adding, list):
                        instance[attr].add(adding)
                    else:
                        for x in adding:
                            instance[attr].add(x)
                if "del" in attrval:
                    deleting = attrval.get("del", [])
                    if deleting and not isinstance(deleting, list):
                        instance[attr].discard(deleting)
                    else:
                        for x in deleting:
                            instance[attr].discard(x)
            else:
                instance[attr].replace([attrval])
        instance.update()
        return jsonify({"message": "Instance successfully updated"}), 200
    except OldapError as error:
        return jsonify({"message": str(error)}), 500

@instance_bp.route('/<project>/<resiri>', methods=['DELETE'])
def delete_instance(project, resiri):
    out = request.headers['Authorization']
    b, token = out.split()

    try:
        con = Connection(token=token, context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    try:
        iri = Iri(resiri, validate=True)
    except OldapErrorValue as error:
        return jsonify({"message": str(error)}), 400
    context = Context(name=con.context_name)
    if not context.get(project):
        return jsonify({"message": f'Project "{project}" not found'}), 404

    try:
        factory = ResourceInstanceFactory(con=con, project=project)
        instance = factory.read(iri)
        instance.delete()
        return jsonify({"message": "Instance successfully deleted"}), 200
    except OldapErrorInUse as error:
        return jsonify({"message": str(error)}), 409
    except OldapErrorNoPermission as error:
        return jsonify({"message": str(error)}), 403
    except OldapErrorNotFound as error:
        return jsonify({"message": str(error)}), 404
    except OldapErrorValue as error:
        return jsonify({"message": str(error)}), 400
    except OldapError as error:
        return jsonify({"message": str(error)}), 500
    return jsonify({"message": "Instance successfully deleted"}), 200

