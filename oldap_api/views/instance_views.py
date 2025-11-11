from flask import request, jsonify, Blueprint
from oldaplib.src.connection import Connection
from oldaplib.src.datamodel import DataModel
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorValue, OldapErrorKey, OldapErrorNoPermission, \
    OldapErrorAlreadyExists
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.objectfactory import ResourceInstanceFactory
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.helpers.context import Context
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName

instance_bp = Blueprint('instance', __name__, url_prefix='/data')

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

    iri = Iri(resiri)
    context = Context(name=con.context_name)
    query = context.sparql_context
    query += f"SELECT ?resclass FROM {project}:data WHERE {{ {iri.toRdf} a ?resclass }}"
    jsonres = con.query(query)
    res = QueryProcessor(context, jsonres)
    for r in res:
        resource = r['resclass']

    data = ResourceInstanceFactory.read_data(con=con,
                                             iri=Iri(resiri, validate=True),
                                             projectShortName=Xsd_NCName(project, validate=True))
    data = {str(x): y for x, y in data.items()}
    return jsonify(data), 200

