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
from oldaplib.src.enums.xsd_datatypes import XsdDatatypes
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapError
from oldaplib.src.project import Project
from oldaplib.src.propertyclass import PropertyClass
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_string import Xsd_string

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


# Dieser Pfad ist für standalone Property. der andere Pfad wird für ressource sein. dies sind dann bereits alle pfade
@datamodel_bp.route('/datamodel/<project>/property', methods=['PUT'])
def add_standalone_property_to_datamodel(project):

    known_json_fields = {"iri", "subPropertyOf", "class", "datatype", "name", "description", "languageIn", "uniqueLang",
                         "in", "minLength", "maxLength", "pattern", "minExclusive", "minInclusive", "maxExclusive",
                         "maxInclusive", "lessThan", "lessThanOrEquals",}
    mandatory_json_fields = {"iri"} # entweder class oder datatype sind mandatory. eines von beiden MUSS drinn sein! wenn property auf literal zeigt -> datatype. wenn prop auf andere ressourceinstanz zeigt -> class von instanz angeben
    out = request.headers['Authorization']
    b, token = out.split()

    if request.is_json:

        data = request.get_json()
        unknown_json_field = set(data.keys()) - known_json_fields
        if unknown_json_field:
            return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to create a permissionset. Usable are {known_json_fields}. Aborded operation"}), 400
        if not mandatory_json_fields.issubset(set(data.keys())):
            return jsonify({"message": f"The Fields {mandatory_json_fields} are required to create a permissionset. Used where {set(data.keys())}. Usablable are {known_json_fields}"}), 400
        iri = data.get("iri", None)  # Iri, z.B. "myproj:pageOf"
        subPropertyOf = data.get("subPropertyOf", None)  # Iri() of the the Superclass, e.g. "myproj:partOf" ; partOf is generischer Fall von pageOf
        toClass = data.get("class", None)  # an Iri(). Beschreibt die Klasse der Instanz, auf die diese Property zeigen muss, Z.B. "myproj:Book" heisst, dass die Property auf ein Buch zeigen muss
        datatype = data.get("datatype", None)  # "xsd:string", oder "xsd:integer" etc. Datentyp, wenn die Property durch einen Literal repräsentiert wird
        name = data.get("name", None)  # Human readable Name, ist ein LangString (kann also in verschiedenen Sprachen vorkommen, z.B. ["Seite@de", Page@fr", "Page@en"]
        description = data.get("description", None)  # Beschreibung (Langstring), z.B. ["Eine Buchseite@de", "A page of a book@en"]
        languageIn = data.get("languageIn", None)  # ["en", "fr", "it", "de"]
        uniqueLang = data.get("uniqueLang", None)  # True | False. Jede Sprache kann nur einmal vorkommen. kommt nur vor wenn property selbst ein langstring datentyp ist
        inSet = data.get("in", None)  # ["Renault", "Opel", "BMW", "Mercedes"]  (für eine string, oder [0, 1, 2, 3]
        minLength = data.get("minLength", None)  # Bei xsd:string und rdf:langString die minimale Länge des Strings
        maxLength = data.get("maxLength", None)  # Bei xsd:String und rdf:langString die maximale Läbge des Strings
        pattern = data.get("pattern", None)  # Der String muss dem Regex-pattern entsprechen. z.B. "^[\w\.-]+@[a-zA-Z\d\.-]+\.[a-zA-Z]{2,}$"
        minExclusive = data.get("minExclusive", None)  # MinimalWert (Exclusive) für einen numerischen Datentyp der Property z.B. Datum/int/float...
        minInclusive = data.get("minInclusive", None)  # Minimaler Wert (inklusive) für einen numerischen Datentyp der Property z.B. Datum/int/float...
        maxExclusive = data.get("maxExclusive", None)  # Maximaler Wert (exklusive) für einen numerischen Datentyp der Property z.B. Datum/int/float...
        maxInclusive = data.get("maxInclusive", None)  # Maximaler Wert (inklusive) für einen numerischen Datentyp der Property z.B. Datum/int/float...
        lessThan = data.get("lessThan", None)  # Der (numerische) Wert muss kleiner sein als der durch die gegenebe IRI referenzierten Property z.B. Iri("myproj:deathDate")
        lessThanOrEquals = data.get("lessThanOrEquals", None)  # Der (numerische) Wert muss kleiner oder gleich sein als der durch die gegenebe IRI referenzierten Property z.B. Iri("myproj:deathDate")

        if datatype is None and toClass is None:
            return jsonify({"message": "Either the datatype or the class must be given"}), 400
        if datatype is not None and toClass is not None:
            return jsonify({"message": "It is not allowed to give both the datatype and the class at the same time"}), 400

        try:
            con = Connection(server='http://localhost:7200',
                             repo="oldap",
                             token=token,
                             context_name="DEFAULT")
        except OldapError as error:
            return jsonify({"message": f"Connection failed: {str(error)}"}), 403

        try:
            dm = DataModel.read(con, project, ignore_cache=True)
            prop = PropertyClass(
                con = con,
                project = project,
                property_class_iri = Iri(iri),
                subPropertyOf = subPropertyOf,
                toClass = toClass,
                datatype=XsdDatatypes(datatype),
                name=LangString(name),
                description=LangString(description),
                languageIn = languageIn,
                uniqueLang=Xsd_boolean(uniqueLang),
                inSet=inSet,
                minLength=minLength,
                maxLength=maxLength,
                pattern=pattern,
                minExclusive=minExclusive,
                minInclusive=minInclusive,
                maxExclusive=maxExclusive,
                maxInclusive=maxInclusive,
                lessThan=lessThan,
                lessThanOrEquals=lessThanOrEquals,
            )
            dm[Iri(iri)] = prop
            dm.update()

        except OldapError as error:
            return jsonify({"message": str(error)}), 400
        return jsonify({"message": f"Standalone property in datamodel {project} successfully created"}), 200


@datamodel_bp.route('/datamodel/<project>/resource', methods=['PUT'])
def add_resource_to_datamodel(project):

    pass

# Read datamodell
# Datamodel:
# {
#  „project“: „proj-iri“,
#  „properties“: [<PropertyDef>, <PropertyDef>,…]
#  „resources: [<ResDef>, <ResDef>, …]
# }
#
# <PropDef>:
# {
#  …
# }
#
# <ResDef>:
# {
#  ...,
#  „hasProperty“:[ {
#   „minCount“: num,
#   „maxCount“: num,
#   „order“: decimal
#   „property“: <PropDef> oder „an_iri“
#  }, {…},…]
# }
@datamodel_bp.route('/datamodel/<project>', methods=['GET'])
def read_datamodel(project):
    out = request.headers['Authorization']
    b, token = out.split()

    try:
        con = Connection(server='http://localhost:7200',
                         repo="oldap",
                         token=token,
                         context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    #zuerst alle properties holen mit dm.get_propclasses() dann alle properties zusammenbauen mit ressourcen wie im yaml
    dm = DataModel.read(con, project, ignore_cache=True)
    propclasses = set(dm.get_propclasses())
    resclasses = set(dm.get_resclasses())
    # testprop = dm[Iri("hyha:testProp")]
    # maxlength = testprop.maxLength

    # Setting all property entries to None to fill the available entries afterwards.
    # (property_class_iri, subPropertyOf, toClass, datatype, name, description, languageIn, uniqueLang,
    #  inSet, minLength, maxLength, pattern, minExclusive, minInclusive, maxExclusive, maxInclusive, lessThan,
    #  lessThanOrEquals) = (None,) * 18



    res = {
        "project": project,
        "standaloneProperties": [],
        "resources": []
    }

    for prop in propclasses:

        kappa = {
            "iri": str(prop),
            "subpropertyOf": str(dm[prop].subPropertyOf),
            "toClass": str(dm[prop].toClass),
            "datatype": str(dm[prop].datatype),
            "name": [f'{value}@{lang.name.lower()}' for lang, value in dm[prop].name.items()] if dm[prop].name else None,
            "description": [f'{value}@{lang.name.lower()}' for lang, value in dm[prop].description.items()] if dm[prop].description else None,
            "languageIn": [f'{tag}'[-2:].lower() for tag in dm[prop].languageIn] if dm[prop].languageIn else None,
            "uniqueLang": bool(dm[prop].uniqueLang),
            "in": str(dm[prop].inSet),
            "minLength": str(dm[prop].minLength),
            "maxLength": str(dm[prop].maxLength),
            "pattern": str(dm[prop].pattern),
            "minExclusive": str(dm[prop].minExclusive),
            "minInclusive": str(dm[prop].minInclusive),
            "maxExclusive": str(dm[prop].maxExclusive),
            "maxInclusive": str(dm[prop].maxInclusive),
            "lessThan": str(dm[prop].lessThan),
            "lessThanOrEquals": str(dm[prop].lessThanOrEquals),
        }

        res["standaloneProperties"].append(kappa)

    return res, 200

