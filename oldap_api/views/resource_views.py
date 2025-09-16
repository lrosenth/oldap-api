import json

from flask import Blueprint, request, jsonify, Response
from oldaplib.src.connection import Connection
from oldaplib.src.project import Project
from oldaplib.src.objectfactory import ResourceInstanceFactory
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorNoPermission, OldapErrorAlreadyExists, \
    OldapErrorInconsistency, OldapErrorValue, OldapErrorNotFound, OldapErrorUpdateFailed, OldapErrorKey


resource_bp = Blueprint('resource', __name__, url_prefix='/data')


@resource_bp.route('/<project>/<resclass>', methods=['PUT'])
def create_resource(project, resclass):
    out = request.headers['Authorization']
    b, token = out.split()

    try:
        con = Connection(token=token,
                         context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    try:
        project = Project.read(con=con, projectIri_SName=project)
        factory = ResourceInstanceFactory(con=con, project=project)
        Resclass = factory.createObjectInstance(resclass)

        data = request.get_json()
        instance = Resclass(**data)
        instance.create()
    except OldapError as error:
        return jsonify({'message': str(error)}), 500
    return jsonify({'message': 'Resource created'}), 200

