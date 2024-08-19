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
from flask import Blueprint, request, jsonify
from oldaplib.src.connection import Connection
from oldaplib.src.datamodel import DataModel
from oldaplib.src.helpers.oldaperror import OldapError

datamodel_bp = Blueprint('datamodel', __name__, url_prefix='/admin')


# name von datamodel == name projekt
# project == project-shortname
# /datamodel/mydatamodelname -- create empty datamodel
# /datamodel/mydatamodelname/myressourcename -- create ressource for that datamodel
# Schritt 1: leeres datamodel erzeugen
@datamodel_bp.route('/datamodel/<project>', methods=['PUT'])
def create_empty_datamodel(project):
    # known_json_fields = {"label", "comment", "givesPermission"}
    # mandatory_json_fields = {"givesPermission"}
    out = request.headers['Authorization']
    b, token = out.split()

    try:
        con = Connection(server='http://localhost:7200',
                         repo="oldap",
                         token=token,
                         context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    dm = DataModel(con=con,
                   project=project,
                   )

    try:
        dm.create()
    except OldapError as error:
        return jsonify({"message": str(error)}), 400

    return jsonify({"message": "Empty datamodel successfully created"}), 200


@datamodel_bp.route('/datamodel/<project>/property', methods=['PUT'])
def create_datamodel(project):

    pass


