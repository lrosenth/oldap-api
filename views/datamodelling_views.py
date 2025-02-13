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
from flask import Blueprint, request, jsonify, Response
from oldaplib.src.connection import Connection
from oldaplib.src.datamodel import DataModel
from oldaplib.src.dtypes.languagein import LanguageIn
from oldaplib.src.dtypes.xsdset import XsdSet
from oldaplib.src.enums.language import Language
from oldaplib.src.enums.propertyclassattr import PropClassAttr
from oldaplib.src.enums.xsd_datatypes import XsdDatatypes
from oldaplib.src.hasproperty import HasProperty
from oldaplib.src.helpers.convert2datatype import convert2datatype
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorNotFound, OldapErrorValue, OldapErrorNoPermission
from oldaplib.src.iconnection import IConnection
from oldaplib.src.project import Project
from oldaplib.src.propertyclass import PropertyClass
from oldaplib.src.resourceclass import ResourceClass
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_string import Xsd_string

from apierror import ApiError
from views import known_languages

datamodel_bp = Blueprint('datamodel', __name__, url_prefix='/admin')


@datamodel_bp.route('/datamodel/<project>', methods=['PUT'])
def create_empty_datamodel(project):
    """
    Viewfunction to create a new and empty datamodel. If a new datamodel is to be created, first it needs
    to be created in this empty state. In a second step the newly created datamodel is then filled with its content.
    :param project: The Name of the project where the new datamodel should be located
    :return: A JSON to denote the success of the operation that has the following form:
    json={"message": "Empty datamodel successfully created"}
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

    dm = DataModel(con=con,
                   project=project,
                   )

    try:
        dm.create()
    except OldapError as error:  # Should not be reachable
        return jsonify({"message": str(error)}), 400

    return jsonify({"message": "Empty datamodel successfully created"}), 200


def process_property(con: IConnection, project: Project, property_iri: str, data: dict) -> PropertyClass:
    """
    A local helper function that processes a given property. Used in:
    1. add_standalone_property_to_datamodel,
    2. add_resource_to_datamodel
    3. add_property_to_resource
    :param con: The connection that was established by the calling function
    :param project: The project where the property that is to be processed is located
    :param property_iri: The Iri of the property that is to be processed
    :param data: The data of the property
    :return: The processed PropertyClass
    """
    known_json_fields = {"iri", "subPropertyOf", "class", "datatype", "name", "description", "languageIn", "uniqueLang",
                         "inSet", "minLength", "maxLength", "pattern", "minExclusive", "minInclusive", "maxExclusive",
                         "maxInclusive", "lessThan", "lessThanOrEquals", "toClass"}

    unknown_json_field = set(data.keys()) - known_json_fields
    if unknown_json_field:
        raise ApiError(f"The Field/s {unknown_json_field} is/are not used to create a permissionset. Usable are {known_json_fields}. Aborded operation")
    iri = property_iri  # Iri, z.B. "myproj:pageOf"
    subPropertyOf = data.get("subPropertyOf", None)  # Iri() of the the Superclass, e.g. "myproj:partOf" ; partOf is generischer Fall von pageOf
    toClass = data.get("class", None)  # an Iri(). Beschreibt die Klasse der Instanz, auf die diese Property zeigen muss, Z.B. "myproj:Book" heisst, dass die Property auf ein Buch zeigen muss
    datatype = data.get("datatype", None)  # "xsd:string", oder "xsd:integer" etc. Datentyp, wenn die Property durch einen Literal repräsentiert wird
    name = data.get("name", None)  # Human readable Name, ist ein LangString (kann also in verschiedenen Sprachen vorkommen, z.B. ["Seite@de", Page@fr", "Page@en"]
    description = data.get("description", None)  # Beschreibung (Langstring), z.B. ["Eine Buchseite@de", "A page of a book@en"]
    languageIn = data.get("languageIn", None)  # ["en", "fr", "it", "de"]
    uniqueLang = data.get("uniqueLang", None)  # True | False. Jede Sprache kann nur einmal vorkommen. kommt nur vor wenn property selbst ein langstring datentyp ist
    inSet = data.get("inSet", None)  # ["Renault", "Opel", "BMW", "Mercedes"]  (für eine string, oder [0, 1, 2, 3]
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
        raise ApiError("At least one of the two -- datatype or class -- needs to be given")
    if datatype is not None and toClass is not None:
        raise ApiError("It is not allowed to give both the datatype and the class at the same time")

    prop = PropertyClass(
        con=con,
        project=project,
        property_class_iri=Iri(iri),
        subPropertyOf=subPropertyOf,
        toClass= None if toClass is None else Iri(toClass),
        datatype = None if datatype is None else XsdDatatypes(datatype),
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


@datamodel_bp.route('/datamodel/<project>/property/<property>', methods=['PUT'])
def add_standalone_property_to_datamodel(project, property):
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
            prop = process_property(con=con, project=project, property_iri=property, data=data)
        except ApiError as error:
            return jsonify({"message": str(error)}), 400
        except AttributeError as error:
            return jsonify({"message": str(error)}), 400  # Should not be reachable
        except TypeError as error:
            return jsonify({"message": str(error)}), 400  # Should not be reachable
        except ValueError as error:
            return jsonify({"message": str(error)}), 400  # Should not be reachable
        except OldapErrorValue as error:
            return jsonify({"message": str(error)}), 400
        except OldapError as error:
            return jsonify({'message': str(error)}), 500  # Should not be reachable

        try:
            dm = DataModel.read(con, project, ignore_cache=True)
            prop.force_external()
            dm[prop.property_class_iri] = prop
            dm.update()

        except OldapError as error:  # Should not be reachable
            return jsonify({"message": str(error)}), 500
        return jsonify({"message": f"Standalone property in datamodel {project} successfully created"}), 200
    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400

@datamodel_bp.route('/datamodel/<project>/<resource>', methods=['PUT'])
def add_resource_to_datamodel(project, resource):
    known_json_fields = {"superclass", "label", "comment", "closed", "hasProperty"}
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
        iri = resource
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

        if hasProperty and isinstance(hasProperty, list):
            for prop in hasProperty:
                unknown_hasproperty_field = set(prop.keys()) - known_hasproperty_fields
                if unknown_hasproperty_field:
                    return jsonify({"message": f"The Field/s {unknown_hasproperty_field} is/are not used to create a property in a resource. Usable are {known_hasproperty_fields}. Aborded operation"}), 400
                if not mandatory_hasproperty_fields.issubset(set(prop.keys())):
                    return jsonify({"message": f"The Fields {mandatory_hasproperty_fields} are required to create a resource. Used where {set(prop.keys())}. Usable are {known_hasproperty_fields}"}), 400
                if prop["property"].get("iri", None) is None:
                    return jsonify({"message": f"Property IRI is missing in HasProperty"}), 400
                try:
                    property_iri = prop["property"]["iri"]
                    endprop = process_property(con=con, project=project, property_iri=property_iri, data=prop["property"])
                    hp1 = HasProperty(con=con, prop=endprop, minCount=prop["minCount"], maxCount=prop["maxCount"], order=prop["order"])
                except ApiError as error:
                    return jsonify({"message": str(error)}), 400
                dm[Iri(iri)][endprop.property_class_iri] = hp1

        try:
            dm.update()
        except OldapError as error:  # Should not be reachable
            return jsonify({"message": str(error)}), 500
        return jsonify({"message": f"Resource in datamodel {project} successfully created"}), 200
    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400


@datamodel_bp.route('/datamodel/<project>/<resource>/<property>', methods=['PUT'])
def add_property_to_resource(project, resource, property):
    known_json_fields = {"subPropertyOf", "datatype", "name", "description", "languageIn", "uniqueLang", "inSet", "minLength", "maxLength", "pattern", "minExclusive", "minInclusive", "maxExclusive", "maxInclusive", "lessThan", "lessThanOrEquals", "minCount", "maxCount", "order"}
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
        if not set(data.keys()):
            return jsonify({"message": f"At least one field must be given to add to the resource. Usable for the add-viewfunction are {known_json_fields}"}), 400

        maxcount = data.get("maxCount", None)
        mincount = data.get("minCount", None)
        order = data.get("order", None)

        if maxcount:
            del data["maxCount"]
        if mincount:
            del data["minCount"]
        if order:
            del data["order"]

        try:
            prop = process_property(con=con, project=project, property_iri=property, data=data)
        except ApiError as error:  # should not be reachable
            return jsonify({"message": str(error)}), 400
        hasprop = HasProperty(con=con, prop=prop, minCount=mincount, maxCount=maxcount, order=order)
        try:
            dm = DataModel.read(con, project, ignore_cache=True)
        except OldapErrorNotFound as error:
            return jsonify({'message': str(error)}), 404
        dm[Iri(resource)][Iri(property)] = hasprop

        try:
            dm.update()
        except OldapError as error:  # Should not be reachable
            return jsonify({"message": str(error)}), 500
        return jsonify({"message": f"Property in resource {resource} in datamodel {project} successfully created"}), 200
    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400


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
            "iri": str(prop) if prop is not None else None,
            **({"subPropertyOf": str(dm[prop].subPropertyOf)} if dm[prop].subPropertyOf is not None else {}),
            **({"toClass": str(dm[prop].toClass)} if dm[prop].toClass is not None else {}),
            **({"datatype": str(dm[prop].datatype)} if dm[prop].datatype is not None else {}),
            **({"name": [f'{value}@{lang.name.lower()}' for lang, value in dm[prop].name.items()]} if dm[prop].name else {}),
            **({"description": [f'{value}@{lang.name.lower()}' for lang, value in dm[prop].description.items()]} if dm[prop].description else {}),
            **({"languageIn": [f'{tag}'[-2:].lower() for tag in dm[prop].languageIn]} if dm[prop].languageIn else {}),
            **({"uniqueLang": bool(dm[prop].uniqueLang)} if dm[prop].uniqueLang is not None else {}),
            **({"inSet": list({str(x) for x in dm[prop].inSet})} if dm[prop].inSet is not None else {}),
            **({"minLength": str(dm[prop].minLength)} if dm[prop].minLength is not None else {}),
            **({"maxLength": str(dm[prop].maxLength)} if dm[prop].maxLength is not None else {}),
            **({"pattern": str(dm[prop].pattern)} if dm[prop].pattern is not None else {}),
            **({"minExclusive": str(dm[prop].minExclusive)} if dm[prop].minExclusive is not None else {}),
            **({"minInclusive": str(dm[prop].minInclusive)} if dm[prop].minInclusive is not None else {}),
            **({"maxExclusive": str(dm[prop].maxExclusive)} if dm[prop].maxExclusive is not None else {}),
            **({"maxInclusive": str(dm[prop].maxInclusive)} if dm[prop].maxInclusive is not None else {}),
            **({"lessThan": str(dm[prop].lessThan)} if dm[prop].lessThan is not None else {}),
            **({"lessThanOrEquals": str(dm[prop].lessThanOrEquals)} if dm[prop].lessThanOrEquals is not None else {}),
        }
        res["standaloneProperties"].append(kappa)

    for resource in resclasses:
        gaga = {
            "iri": str(resource),
            # **({"superclass": str(dm[resource].superclass)} if dm[resource].superclass is not None else {})
            # does not add a "superclass": None if dm[resource].superclass is None. That's better...
            "superclass": str(dm[resource].superclass) if dm[resource].superclass is not None else None,
            "label": [f'{value}@{lang.name.lower()}' for lang, value in dm[resource].label.items()] if dm[resource].label else None,
            "comment": [f'{value}@{lang.name.lower()}' for lang, value in dm[resource].comment.items()] if dm[resource].comment else None,
            "closed": bool(dm[resource].closed) if dm[resource].closed is not None else None,
            "hasProperty": []
        }
        for iri, hp in dm[resource].properties.items():
            hp.prop.subPropertyOf
            papa = {
                "property": {
                    "iri": str(iri),
                    "subPropertyOf": str(hp.prop.subPropertyOf) if hp.prop.subPropertyOf is not None else None,
                    "datatype": str(hp.prop.datatype) if hp.prop.datatype is not None else None,
                    "name": [f'{value}@{lang.name.lower()}' for lang, value in hp.prop.name.items()] if hp.prop.name else None,
                    "description": [f'{value}@{lang.name.lower()}' for lang, value in hp.prop.description.items()] if hp.prop.description else None,
                    "languageIn": [f'{tag}'[-2:].lower() for tag in hp.prop.languageIn] if hp.prop.languageIn else None,
                    "uniqueLang": bool(hp.prop.uniqueLang) if hp.prop.uniqueLang is not None else None,
                    "inSet": list({str(x) for x in hp.prop.inSet}) if hp.prop.inSet is not None else None,
                    "minLength": str(hp.prop.minLength) if hp.prop.minLength is not None else None,
                    "maxLength": str(hp.prop.maxLength) if hp.prop.maxLength is not None else None,
                    "pattern": str(hp.prop.pattern) if hp.prop.pattern is not None else None,
                    "minExclusive": str(hp.prop.minExclusive) if hp.prop.minExclusive is not None else None,
                    "minInclusive": str(hp.prop.minInclusive) if hp.prop.minInclusive is not None else None,
                    "maxExclusive": str(hp.prop.maxExclusive) if hp.prop.maxExclusive is not None else None,
                    "maxInclusive": str(hp.prop.maxInclusive) if hp.prop.maxInclusive is not None else None,
                    "lessThan": str(hp.prop.lessThan) if hp.prop.lessThan is not None else None,
                    "lessThanOrEquals": str(hp.prop.lessThanOrEquals) if hp.prop.lessThanOrEquals is not None else None,
                },
                "maxCount": str(hp.maxCount) if hp.maxCount is not None else None,
                "minCount": str(hp.minCount) if hp.minCount is not None else None,
                "order": str(hp.order) if hp.order is not None else None,
            }
            gaga["hasProperty"].append(papa)
        res["resources"].append(gaga)
    return res, 200


@datamodel_bp.route('/datamodel/<project>', methods=['DELETE'])
def delete_whole_datamodel(project):
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
        dm.delete()
    except OldapError as error:  # Should not be reachable
        return jsonify({'message': str(error)}), 500
    return jsonify({'message': 'Data model successfully deleted'}), 200


@datamodel_bp.route('/datamodel/<project>/property/<standaloneprop>', methods=['DELETE'])
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
    except OldapErrorValue as error:
        return jsonify({'message': str(error)}), 404
    except OldapError as error:  # Should not be reachable
        return jsonify({'message': str(error)}), 500
    return jsonify({'message': 'Data model successfully deleted'}), 200


@datamodel_bp.route('/datamodel/<project>/<resource>', methods=['DELETE'])
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
    except OldapErrorValue as error:
        return jsonify({'message': str(error)}), 404
    except OldapError as error:
        return jsonify({'message': str(error)}), 500  # Should not be reachable
    return jsonify({'message': 'Data model successfully deleted'}), 200


@datamodel_bp.route('/datamodel/<project>/<resource>/<property>', methods=['DELETE'])
def delete_hasprop_in_resource(project, resource, property):
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
    except OldapErrorValue as error:
        return jsonify({'message': str(error)}), 404
    except OldapError as error:
        return jsonify({'message': str(error)}), 500  # Should not be reachable
    return jsonify({'message': 'Data model successfully deleted'}), 200


def property_modifier(data: dict, property: PropertyClass) -> tuple[Response, int]:
    known_json_fields = {"iri", "subPropertyOf", "toClass", "datatype", "name", "description", "languageIn", "uniqueLang", "inSet", "minLength", "maxLength", "pattern", "minExclusive", "minInclusive", "maxExclusive", "maxInclusive", "lessThan", "lessThanOrEquals"}
    unknown_json_field = set(data.keys()) - known_json_fields
    if unknown_json_field:
        return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to modify a project. Usable are {known_json_fields}. Aborded operation"}), 400
    if not set(data.keys()):
        return jsonify({"message": f"At least one field must be given to modify the project. Usable for the modify-viewfunction are {known_json_fields}"}), 400
    for attrname, attrval in data.items():
        if attrname == "languageIn":
            if isinstance(attrval, list):
                if not attrval:
                    return jsonify({"message": f"Using an empty list is not allowed in the modify"}), 400
                for item in attrval:
                    if item is None:
                        return jsonify({"message": f"Using a None in a modifylist is not allowed"}), 400
                tmpval = [Language[x.upper()] for x in attrval]
                setattr(property, attrname, LanguageIn(tmpval))
            elif isinstance(attrval, dict):
                if not set(attrval.keys()).issubset({"add", "del"}):
                    return jsonify({"message": f"The sended command (keyword in dict) is not known"}), 400
                if "add" in attrval:
                    adding = attrval.get("add", [])
                    if not isinstance(adding, list):
                        return jsonify({"message": "The given attributes in add and del must be in a list"}), 400
                    if not adding:
                        return jsonify({"message": f"Using an empty list is not allowed in the modify"}), 400
                    for item in adding:
                        if item is None:
                            return jsonify({"message": f"Using a None in a modifylist is not allowed"}), 400
                        property.languageIn.add(Language[item.upper()])
                if "del" in attrval:
                    deleting = attrval.get("del", [])
                    if not isinstance(deleting, list):
                        return jsonify({"message": "The given attributes in add and del must be in a list"}), 400
                    if not deleting:
                        return jsonify({"message": f"Using an empty list is not allowed in the modify"}), 400
                    for item in deleting:
                        if item is None:
                            return jsonify({"message": f"Using a None in a modifylist is not allowed"}), 400
                        property.languageIn.discard(Language[item.upper()])
            if attrval is None:
                delattr(property, attrname)
            continue
        if attrname == "inSet":
            datatype = property.datatype
            if isinstance(attrval, list):
                if not attrval:
                    return jsonify({"message": f"Using an empty list is not allowed in the modify"}), 400
                for item in attrval:
                    if item is None:
                        return jsonify({"message": f"Using a None in a modifylist is not allowed"}), 400
                tmpval = [convert2datatype(x, datatype) for x in attrval]
                setattr(property, attrname, XsdSet(tmpval))
            elif isinstance(attrval, dict):
                if not set(attrval.keys()).issubset({"add", "del"}):
                    return jsonify({"message": f"The sended command (keyword in dict) is not known"}), 400
                if "add" in attrval:
                    adding = attrval.get("add", [])
                    if not isinstance(adding, list):
                        return jsonify({"message": "The given attributes in add and del must be in a list"}), 400
                    if not adding:
                        return jsonify({"message": f"Using an empty list is not allowed in the modify"}), 400
                    for item in adding:
                        if item is None:
                            return jsonify({"message": f"Using a None in a modifylist is not allowed"}), 400
                        property.inSet.add(convert2datatype(item, datatype))
                if "del" in attrval:
                    deleting = attrval.get("del", [])
                    if not isinstance(deleting, list):
                        return jsonify({"message": "The given attributes in add and del must be in a list"}), 400
                    if not deleting:
                        return jsonify({"message": f"Using an empty list is not allowed in the modify"}), 400
                    for item in deleting:
                        if item is None:
                            return jsonify({"message": f"Using a None in a modifylist is not allowed"}), 400
                        property.inSet.discard(convert2datatype(item, datatype))
            if attrval is None:
                delattr(property, attrname)
            continue
        if attrname == "name" or attrname == "description":
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
                setattr(property, attrname, LangString(attrval))
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
                    for item in adding:
                        if item is None:
                            return jsonify({"message": f"Using a None in a modifylist is not allowed"}), 400
                        try:
                            if item[-3] != '@':
                                return jsonify({"message": f"Please add a correct language tags e.g. @de"}), 400
                        except IndexError as error:
                            return jsonify({"message": f"Please add a correct language tags e.g. @de"}), 400
                        lang = item[-2:].upper()
                        try:
                            property[PropClassAttr.from_name(str(attrname))][Language[lang]] = item[:-3]
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
            elif attrval is None:
                delattr(property, attrname)
            else:
                return jsonify({"message": f"To modify {attrname} accepted is either a list, dict or None. Received {type(attrname).__name__} instead."}), 400
            continue
        if attrval is None:
            delattr(property, attrname)
        else:
            setattr(property, attrname, attrval)
        continue
    return jsonify({"message": "Property in resource successfully updated"}), 200

@datamodel_bp.route('/datamodel/<project>/property/<property>', methods=['POST'])
def modify_standalone_property(project, property):

    known_json_fields = {"iri", "subPropertyOf", "toClass", "datatype", "name", "description", "languageIn", "uniqueLang", "inSet", "minLength", "maxLength", "pattern", "minExclusive", "minInclusive", "maxExclusive", "maxInclusive", "lessThan", "lessThanOrEquals"}
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
            return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to modify a standalone property. Usable are {known_json_fields}. Aborded operation"}), 400
        if not set(data.keys()):
            return jsonify({"message": f"At least one field must be given to modify the standalone property. Usable for the modify-viewfunction are {known_json_fields}"}), 400

        jsonmsg, statuscode = property_modifier(data, dm[Iri(property)])
        if statuscode != 200:
            return jsonmsg, statuscode
        try:
            dm.update()
        except OldapErrorNoPermission as error:
            return jsonify({'message': str(error)}), 404
        except OldapError as error:
            return jsonify({'message': str(error)}), 500  # Should not be reachable
        return jsonify({'message': 'Data model successfully modified'}), 200
    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400


@datamodel_bp.route('/datamodel/<project>/<resource>', methods=['POST'])
def modify_resource(project, resource):

    known_json_fields = {"label", "comment", "closed", "hasProperty"}
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
            return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to modify a standalone property. Usable are {known_json_fields}. Aborded operation"}), 400
        if not set(data.keys()):
            return jsonify({"message": f"At least one field must be given to modify the standalone property. Usable for the modify-viewfunction are {known_json_fields}"}), 400

        for attrname, attrval in data.items():
            if attrname == "label" or attrname == "comment":
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

                        setattr(dm[Iri(resource)], attrname, LangString(attrval))
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
                        for item in adding:
                            if item is None:
                                return jsonify({"message": f"Using a None in a modifylist is not allowed"}), 400
                            try:
                                if item[-3] != '@':
                                    return jsonify({"message": f"Please add a correct language tags e.g. @de"}), 400
                            except IndexError as error:
                                return jsonify({"message": f"Please add a correct language tags e.g. @de"}), 400
                            lang = item[-2:].upper()
                            try:
                                tmp = getattr(dm[Iri(resource)], attrname)
                                tmp[Language[lang]] = item[:-3]
                                #dm[Iri(resource)]['rdfs:'+ attrname][Language[lang]] = item[:-3]
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
                                tmp = getattr(dm[Iri(resource)], attrname)
                                del tmp[Language[lang]]
                            except KeyError as error:
                                return jsonify({"message": f"{lang} is not a valid language. Supportet are {known_languages}"}), 400
                elif attrval is None:
                    delattr(dm[Iri(resource)], attrname)
                    # del dm[Iri(resource)][attrname]
                else:
                    return jsonify({"message": f"To modify {attrname} accepted is either a list, dict or None. Received {type(attrname).__name__} instead."}), 400
                continue

            if attrval is not None:
                setattr(dm[Iri(resource)], attrname, attrval)
        try:
            dm.update()
        except OldapErrorNoPermission as error:
            return jsonify({'message': str(error)}), 404
        except OldapError as error:
            return jsonify({'message': str(error)}), 500  # Should not be reachable
        return jsonify({'message': 'Data model successfully modified'}), 200
    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400


@datamodel_bp.route('/datamodel/<project>/<resiri>/<propiri>', methods=['POST'])
def modify_attribute_in_has_prop(project, resiri, propiri):
    known_json_fields = {"maxCount", "minCount", "order", "property"}
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
    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400
    unknown_json_field = set(data.keys()) - known_json_fields
    if unknown_json_field:
        return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to modify an attribute of a property in a resource. Usable are {known_json_fields}. Aborded operation"}), 400
    if not set(data.keys()):
        return jsonify({"message": f"At least one field must be given to modify an attribute of a property in a resource. Usable for the modify-viewfunction are {known_json_fields}"}), 400

    if "minCount" in data:
        dm[Iri(resiri)][Iri(propiri)].minCount = data["minCount"]
    if "maxCount" in data:
        dm[Iri(resiri)][Iri(propiri)].maxCount = data["maxCount"]
    if "order" in data:
        dm[Iri(resiri)][Iri(propiri)].order = data["order"]

    property_data = data.get("property", None)
    if property_data or property_data == {}:
        jsonmsg, statuscode = property_modifier(property_data, dm[Iri(resiri)][Iri(propiri)].prop)
        if statuscode != 200:
            return jsonmsg, statuscode

    try:
        dm.update()
    except OldapErrorNoPermission as error:
        return jsonify({'message': str(error)}), 404
    except OldapError as error:
        return jsonify({'message': str(error)}), 500  # Should not be reachable
    return jsonify({'message': 'Data model successfully modified'}), 200











