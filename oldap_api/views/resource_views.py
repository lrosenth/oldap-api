import json

from flask import Blueprint, request, jsonify, Response
from oldap_api.authentication import authenticated_connection, require_auth
from oldaplib.src.datamodel import DataModel
from oldaplib.src.project import Project
from oldaplib.src.objectfactory import ResourceInstanceFactory
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorNoPermission, OldapErrorAlreadyExists, \
    OldapErrorInconsistency, OldapErrorValue, OldapErrorNotFound, OldapErrorUpdateFailed, OldapErrorKey


resource_bp = Blueprint('resource', __name__, url_prefix='/admin')

@resource_bp.route('/<project>/get/<iri>', methods=['GET'])
@require_auth
def get_resource(project, iri):

    con = authenticated_connection()
    try:
        project = Project.read(con, projectIri_SName=project)
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404
    except OldapError as error:
        return jsonify({'message': str(error)}), 400

    try:
        factory = ResourceInstanceFactory(con=con, project=project)
    except (OldapErrorInconsistency, OldapErrorNotFound, OldapError) as error:
        return jsonify({'message': str(error)}), 400

    try:
        instance = factory.read(iri)
    except OldapErrorNoPermission as error:
        return jsonify({'message': str(error)}), 403
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404
    except OldapError as error:
        return jsonify({'message': str(error)}), 500
    return jsonify(instance.toJsonObject()), 200


@resource_bp.route('/<project>/<resclass>', methods=['PUT'])
@require_auth
def create_resource(project, resclass):

    con = authenticated_connection()

    try:
        project = Project.read(con=con, projectIri_SName=project)
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404
    except OldapError as error:
        return jsonify({'message': str(error)}), 500

    dm = DataModel.read(con, project, ignore_cache=True)
    pass

    try:
        factory = ResourceInstanceFactory(con=con, project=project)
        Resclass = factory.createObjectInstance(resclass)
    except OldapError as error:
        return jsonify({'message': str(error)}), 500

    data = request.get_json()

    try:
        instance = Resclass(**data)
    except (OldapErrorValue, OldapErrorKey, OldapError) as error:
        return jsonify({'message': str(error)}), 400

    try:
        instance.create()
    except OldapErrorNoPermission as error:
        return jsonify({'message': str(error)}), 403
    except OldapErrorAlreadyExists as error:
        return jsonify({'message': str(error)}), 409
    except OldapError as error:
        return jsonify({'message': str(error)}), 500

    return jsonify({'message': 'OK', 'iri': str(instance.iri)}), 200

