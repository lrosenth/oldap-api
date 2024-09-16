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
from oldaplib.src.dtypes.xsdset import XsdSet
from oldaplib.src.enums.propertyclassattr import PropClassAttr
from oldaplib.src.enums.xsd_datatypes import XsdDatatypes
from oldaplib.src.hasproperty import HasProperty
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorNotFound
from oldaplib.src.iconnection import IConnection
from oldaplib.src.project import Project
from oldaplib.src.propertyclass import PropertyClass
from oldaplib.src.resourceclass import ResourceClass
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_string import Xsd_string

from apierror import ApiError

datamodel_bp = Blueprint('datamodel', __name__, url_prefix='/admin')


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


def process_property(con: IConnection, project: Project, data: dict) -> PropertyClass:
    known_json_fields = {"iri", "subPropertyOf", "class", "datatype", "name", "description", "languageIn", "uniqueLang",
                         "in", "minLength", "maxLength", "pattern", "minExclusive", "minInclusive", "maxExclusive",
                         "maxInclusive", "lessThan", "lessThanOrEquals", }
    mandatory_json_fields = {"iri"}  # entweder class oder datatype sind mandatory. eines von beiden MUSS drinn sein! wenn property auf literal zeigt -> datatype. wenn prop auf andere ressourceinstanz zeigt -> class von instanz angeben

    unknown_json_field = set(data.keys()) - known_json_fields
    if unknown_json_field:
        raise ApiError("The Field/s {unknown_json_field} is/are not used to create a permissionset. Usable are {known_json_fields}. Aborded operation")
    if not mandatory_json_fields.issubset(set(data.keys())):
        raise ApiError("The Fields {mandatory_json_fields} are required to create a permissionset. Used where {set(data.keys())}. Usablable are {known_json_fields}")
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
        raise ApiError("At least one of the two datatype or toClass needs to be given")
    if datatype is not None and toClass is not None:
        raise ApiError("It is not allowed to give both the datatype and the class at the same time")

    prop = PropertyClass(
        con=con,
        project=project,
        property_class_iri=Iri(iri),
        subPropertyOf=subPropertyOf,
        toClass=toClass,
        datatype=XsdDatatypes(datatype),
        name=LangString(name),
        description=LangString(description),
        languageIn=languageIn,
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

    return prop


# Dieser Pfad ist für standalone Property. der andere Pfad wird für ressource sein. dies sind dann bereits alle pfade
@datamodel_bp.route('/datamodel/<project>/property', methods=['PUT'])
def add_standalone_property_to_datamodel(project):
    out = request.headers['Authorization']
    b, token = out.split()

    if request.is_json:

        try:
            con = Connection(server='http://localhost:7200',
                             repo="oldap",
                             token=token,
                             context_name="DEFAULT")
        except OldapError as error:
            return jsonify({"message": f"Connection failed: {str(error)}"}), 403

        data = request.get_json()
        try:
            prop = process_property(con=con, project=project, data=data)
        except ApiError as error:
            return jsonify({"message": str(error)}), 400

        try:
            dm = DataModel.read(con, project, ignore_cache=True)
            prop.force_external()
            dm[prop.property_class_iri] = prop
            dm.update()

        except OldapError as error:
            return jsonify({"message": str(error)}), 400
        return jsonify({"message": f"Standalone property in datamodel {project} successfully created"}), 200


@datamodel_bp.route('/datamodel/<project>/resource', methods=['PUT'])
def add_resource_to_datamodel(project):
    known_json_fields = {"iri", "superclass", "label", "comment", "closed", "hasProperty"}
    mandatory_json_fields = {"iri"}
    known_hasproperty_fields = {"property", "maxCount", "minCount", "order"}
    mandatory_hasproperty_fields = {"property"}
    out = request.headers['Authorization']
    b, token = out.split()

    if request.is_json:

        try:
            con = Connection(server='http://localhost:7200',
                             repo="oldap",
                             token=token,
                             context_name="DEFAULT")
        except OldapError as error:
            return jsonify({"message": f"Connection failed: {str(error)}"}), 403

        data = request.get_json()

        unknown_json_field = set(data.keys()) - known_json_fields
        if unknown_json_field:
            return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to create a resource. Usable are {known_json_fields}. Aborded operation"}), 400
        if not mandatory_json_fields.issubset(set(data.keys())):
            return jsonify({"message": f"The Fields {mandatory_json_fields} are required to create a resource. Used where {set(data.keys())}. Usablable are {known_json_fields}"})

        iri = data.get("iri", None)
        superclass = data.get("superclass", None)
        label = data.get("label", None)
        comment = data.get("comment", None)
        closed = data.get("closed", None)
        hasProperty = data.get("hasProperty", None)

        try:
            dm = DataModel.read(con, project, ignore_cache=True)
        except OldapError as error:
            return jsonify({"message": str(error)}), 400

        resource = ResourceClass(con=con, project=project, owlclass_iri=Iri(iri), comment=comment, closed=closed, label=label)
        if resource.superclass is not None:
            try:
                resource.superclass = superclass
            except OldapError as error:
                return jsonify({"message": str(error)}), 403
        dm[Iri(iri)] = resource
        dm.update()

        # TODO: correct oldap that this is not necessary to reread the dm
        try:
            dm = DataModel.read(con, project, ignore_cache=True)
        except OldapError as error:
            return jsonify({"message": str(error)}), 400

        if hasProperty and isinstance(hasProperty, list):
            for prop in hasProperty:
                unknown_hasproperty_field = set(prop.keys()) - known_hasproperty_fields
                if unknown_hasproperty_field:
                    return jsonify({"message": f"The Field/s {unknown_hasproperty_field} is/are not used to create a property in a resource. Usable are {known_hasproperty_fields}. Aborded operation"}), 400
                if not mandatory_hasproperty_fields.issubset(set(prop.keys())):
                    return jsonify({"message": f"The Fields {mandatory_hasproperty_fields} are required to create a resource. Used where {set(prop.keys())}. Usablable are {known_hasproperty_fields}"}), 400
                try:
                    endprop = process_property(con=con, project=project, data=prop["property"])
                    hp1 = HasProperty(con=con, prop=endprop, minCount=prop["minCount"], maxCount=prop["maxCount"], order=prop["order"])
                except ApiError as error:
                    return jsonify({"message": str(error)}), 400
                dm[Iri(iri)][endprop.property_class_iri] = hp1

        try:
            dm.update()
        except OldapError as error:
            return jsonify({"message": str(error)}), 400
        return jsonify({"message": f"Resource in datamodel {project} successfully created"}), 200


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

    try:
        dm = DataModel.read(con, project, ignore_cache=True)
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404

    propclasses = set(dm.get_propclasses())
    resclasses = set(dm.get_resclasses())

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

    for resource in resclasses:
        gaga = {
            "iri": str(resource),
            "superclass": str(dm[resource].superclass),
            "label": [f'{value}@{lang.name.lower()}' for lang, value in dm[resource].label.items()] if dm[resource].label else None,
            "comment": [f'{value}@{lang.name.lower()}' for lang, value in dm[resource].comment.items()] if dm[resource].comment else None,
            "closed": bool(dm[resource].closed),
            "hasProperty": []
        }
        for iri, hp in dm[resource].properties.items():
            hp.prop.subPropertyOf
            papa = {
                "property": {
                    "iri": str(iri),
                    "subPropertyOf": str(hp.prop.subPropertyOf),
                    "datatype": str(hp.prop.datatype),
                    "name": [f'{value}@{lang.name.lower()}' for lang, value in hp.prop.name.items()] if hp.prop.name else None,
                    "description": [f'{value}@{lang.name.lower()}' for lang, value in hp.prop.description.items()] if hp.prop.description else None,
                    "languageIn": [f'{tag}'[-2:].lower() for tag in hp.prop.languageIn] if hp.prop.languageIn else None,
                    "uniqueLang": bool(hp.prop.uniqueLang),
                    "in": str(hp.prop.inSet),
                    "minLength": str(hp.prop.minLength),
                    "maxLength": str(hp.prop.maxLength),
                    "pattern": str(hp.prop.pattern),
                    "minExclusive": str(hp.prop.minExclusive),
                    "minInclusive": str(hp.prop.minInclusive),
                    "maxExclusive": str(hp.prop.maxExclusive),
                    "maxInclusive": str(hp.prop.maxInclusive),
                    "lessThan": str(hp.prop.lessThan),
                    "lessThanOrEquals": str(hp.prop.lessThanOrEquals)
                },
                "maxCount": str(hp.maxCount),
                "minCount": str(hp.minCount),
                "order": str(hp.order)
            }
            gaga["hasProperty"].append(papa)
        res["resources"].append(gaga)
    return res, 200


# TODO
@datamodel_bp.route('/datamodel/<project>/delete', methods=['DELETE'])
def delete_whole_datamodel(project):
    pass
    # out = request.headers['Authorization']
    # b, token = out.split()
    #
    # try:
    #     con = Connection(server='http://localhost:7200',
    #                      repo="oldap",
    #                      token=token,
    #                      context_name="DEFAULT")
    # except OldapError as error:
    #     return jsonify({"message": f"Connection failed: {str(error)}"}), 403


@datamodel_bp.route('/datamodel/<project>/<standaloneprop>/del', methods=['DELETE'])
def delete_whole_standalone_property(project, standaloneprop):
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
        dm = DataModel.read(con, project, ignore_cache=True)
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404

    try:
        del dm[Iri(standaloneprop)]
        dm.update()
    except KeyError as error:
        return jsonify({'message': str(error)}), 404
    except OldapError as error:
        return jsonify({'message': str(error)}), 500
    return jsonify({'message': 'Data model successfully deleted'}), 200


@datamodel_bp.route('/datamodel/<project>/<resource>/del', methods=['DELETE'])
def delete_whole_resource(project, resource):
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
        dm = DataModel.read(con, project, ignore_cache=True)
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404

    try:
        del dm[Iri(resource)]
        dm.update()
    except KeyError as error:
        return jsonify({'message': str(error)}), 404
    except OldapError as error:
        return jsonify({'message': str(error)}), 500
    return jsonify({'message': 'Data model successfully deleted'}), 200


@datamodel_bp.route('/datamodel/<project>/<resource>/<property>/del', methods=['DELETE'])
def delete_prop_in_resource(project, resource, property):
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
        dm = DataModel.read(con, project, ignore_cache=True)
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404

    try:
        del dm[Iri(resource)][Iri(property)]
        dm.update()
    except KeyError as error:
        return jsonify({'message': str(error)}), 404
    except OldapError as error:
        return jsonify({'message': str(error)}), 500
    return jsonify({'message': 'Data model successfully deleted'}), 200


@datamodel_bp.route('/datamodel/<project>/<property>/mod', methods=['POST'])
def modify_standalone_property(project, property):

    known_json_fields = {"iri", "subPropertyOf", "toClass", "datatype", "name", "description", "languageIn", "uniqueLang", "in", "minLength", "maxLength", "pattern", "minExclusive", "minInclusive", "maxExclusive", "maxInclusive", "lessThan", "lessThanOrEquals"}
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
        dm = DataModel.read(con, project, ignore_cache=True)
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404

    if request.is_json:
        data = request.get_json()
        unknown_json_field = set(data.keys()) - known_json_fields
        if unknown_json_field:
            return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to modify a project. Usable are {known_json_fields}. Aborded operation"}), 400
        if not set(data.keys()):
            return jsonify({"message": f"At least one field must be given to modify the project. Usablable for the modify-viewfunction are {known_json_fields}"}), 400

        # TODO: inSet und languageIn muss mit Paps zusammen gemacht werden. Ausserdem: Wieder das mit [] und {add: ..., del: ...} erlaubn?
        # if data.get("in", None):
        #     indata = XsdSet({Xsd_string(x) for x in data.get("in")})
        # else:
        #     indata = None

        attributes = {
            "iri": data.get("iri", None),
            "subPropertyOf": data.get("subPropertyOf", None),
            "toClass": data.get("toClass", None),
            "datatype": data.get("datatype", None),
            "name": LangString(data.get("name", None)),
            "description": LangString(data.get("description", None)),
            # "languageIn": data.get("languageIn", None),
            "uniqueLang": data.get("uniqueLang", None),
            # "inSet": indata,
            "minLength": data.get("minLength", None),
            "maxLength": data.get("maxLength", None),
            "pattern": data.get("pattern", None),
            "minExclusive": data.get("minExclusive", None),
            "minInclusive": data.get("minInclusive", None),
            "maxExclusive": data.get("maxExclusive", None),
            "maxInclusive": data.get("maxInclusive", None),
            "lessThan": data.get("lessThan", None),
            "lessThanOrEquals": data.get("lessThanOrEquals", None)
        }

        if attributes["toClass"] and attributes["datatype"]:
            return jsonify({"message": "It is not allowed to simultaniously give a 'toClass' and a 'datatype'"})
        if dm[Iri(property)].toClass and attributes["datatype"]:
            return jsonify({"message": "A 'toClass' is still present in the property. Therefore it is not allowed to set a datatype since they are mutualy exclusive"})
        if dm[Iri(property)].datatype and attributes["toClass"]:
            return jsonify({"message": "A 'datatype' is still present in the property. Therefore it is not allowed to set a toClass since they are mutualy exclusive"})

        for attr, value in attributes.items():
            if value is not None:
                setattr(dm[Iri(property)], attr, value)

        try:
            dm.update()
        except KeyError as error:
            return jsonify({'message': str(error)}), 404
        except OldapError as error:
            return jsonify({'message': str(error)}), 500
    return jsonify({'message': 'Data model successfully modified'}), 200


@datamodel_bp.route('/datamodel/mod/<project>/<resource>', methods=['POST'])
def modify_resource(project, resource):

    # known_json_fields = {"iri", "subPropertyOf", "toClass", "datatype", "name", "description", "languageIn", "uniqueLang", "in", "minLength", "maxLength", "pattern", "minExclusive", "minInclusive", "maxExclusive", "maxInclusive", "lessThan", "lessThanOrEquals"}
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
        dm = DataModel.read(con, project, ignore_cache=True)
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404

    if request.is_json:
        data = request.get_json()

        attributes = {
            "closed": data.get("closed", None),
        }
        for attr, value in attributes.items():
            if value is not None:
                setattr(dm[Iri(resource)], attr, value)
        try:
            dm.update()
        except KeyError as error:
            return jsonify({'message': str(error)}), 404
        except OldapError as error:
            return jsonify({'message': str(error)}), 500
    return jsonify({'message': 'Data model successfully modified'}), 200
