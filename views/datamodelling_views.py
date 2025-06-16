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
from oldaplib.src.enums.resourceclassattr import ResClassAttribute
from oldaplib.src.enums.xsd_datatypes import XsdDatatypes
from oldaplib.src.hasproperty import HasProperty
from oldaplib.src.helpers.convert2datatype import convert2datatype
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorNotFound, OldapErrorValue, OldapErrorNoPermission, \
    OldapErrorInconsistency, OldapErrorAlreadyExists, OldapErrorKey, OldapErrorType
from oldaplib.src.iconnection import IConnection
from oldaplib.src.project import Project
from oldaplib.src.propertyclass import PropertyClass
from oldaplib.src.resourceclass import ResourceClass
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_string import Xsd_string

from apierror import ApiError
from helpers.process_langstring import process_langstring
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
        return jsonify({"message": str(error)}), 500

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
    """
    Viewfunction to add a standalone property to an existing datamodel. A JSON is expectet that has the following form.
    Either the class or the datatype must be given but not both at the same time.
    If the datatype is given, then all fields are optional. If the class is given, only subPropertyOf, name and desctiption are allowed.
    json={
        "subPropertyOf": "hyha:testProp",
        "datatype": "rdf:langString",
        "class": "hyha:kappa",
        "name": ["Test Property@en", "Test Feld@de"],
        "description": ["Test Feld Beschreibung@de"],
        "languageIn": ["en", "fr", "it", "de"],
        "uniqueLang": True,
        "inSet": ["Kappa", "Gaga", "gugus"],
        "minLength": 1,
        "maxLength": 50,
        "pattern": r"^[\w\.-]+@[a-zA-Z\d-]+(\.[a-zA-Z\d-]+)*\.[a-zA-Z]{2,}$",
        "minExclusive": 5.5,
        "minInclusive": 5.5,
        "maxExclusive": 5.5,
        "maxInclusive": 5.5,
        "lessThan": "hyha:testProp",
        "lessThanOrEquals": "hyha:testProp"
    }
    For a detailed overview what the fields mean look at def process_property
    :param project: The project where the datamodel is located
    :param property: The name (Iri) of the property one wish to add
    :return: A JSON informing about the success of the operation that has the following form:
    json={"message": f"Standalone property in datamodel {project} successfully created"}
    """
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
            prop.force_external()
        except (ApiError, AttributeError, TypeError, ValueError,OldapErrorValue, OldapErrorInconsistency) as error:
            return jsonify({"message": str(error)}), 400
        except OldapErrorNotFound as error:
            return jsonify({'message': str(error)}), 404
        except OldapError as error:
            return jsonify({'message': str(error)}), 500  # Should not be reachable

        try:
            dm = DataModel.read(con, project, ignore_cache=True)
            dm[prop.property_class_iri] = prop
            dm.update()

        except OldapErrorAlreadyExists as error:
            return jsonify({"message": str(error)}), 409
        except OldapError as error:  # Should not be reachable
            return jsonify({"message": str(error)}), 500
        return jsonify({"message": f"Standalone property in datamodel {project} successfully created"}), 200
    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400

@datamodel_bp.route('/datamodel/<project>/<resource>', methods=['PUT'])
def add_resource_to_datamodel(project, resource):
    """
    Viewfunction to add a standalone property to an existing datamodel. A JSON is expectet that has the following form.
    If a non-empty hasProperty is given then property a mandatory field. The others are all optional.
    json={
        "label": [
        "Eine Buchseite@de",
        "A page of a book@en"
        ],
        "comment": [
            "Eine Buchseite@de",
            "A page of a book@en"
        ],
        "closed": True,
        "hasProperty": [
            {
                "property": {...},
                "maxCount": 3,
                "minCount": 1,
                "order": 1
            },
            {
                "property": {...},
                "maxCount": 4,
                "minCount": 2,
                "order": 2
            }
        ]
    }
    Note: in property_1 and property_2 are the same fields as in add_standalone_property_to_datamodel
    :param project: The project where the datamodel is located
    :param resource: The name (Iri) of the resource one wish to add
    :return: A JSON informing about the success of the operation that has the following form:
    json={"message": f"Resource in datamodel {project} successfully created"}
    """
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
            return jsonify({"message": str(error)}), 404

        resource = ResourceClass(con=con, project=project, owlclass_iri=Iri(iri), comment=comment, closed=closed, label=label)
        if resource.superclass is not None:
            try:
                resource.superclass = superclass
            except OldapError as error:
                return jsonify({"message": str(error)}), 403
            try:
                dm[Iri(iri)] = resource
            except OldapErrorAlreadyExists as error:
                return jsonify({"message": str(error)}), 409

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
        except OldapErrorAlreadyExists as error:
            return jsonify({"message": str(error)}), 409
        except OldapError as error:  # Should not be reachable
            return jsonify({"message": str(error)}), 500
        return jsonify({"message": f"Resource in datamodel {project} successfully created"}), 200
    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400


@datamodel_bp.route('/datamodel/<project>/<resource>/<property>', methods=['PUT'])
def add_property_to_resource(project, resource, property):
    """
    Viewfunction to add a property to a resource. A JSON is expected that has the following form. Note that the same fields
    are used when a standalone property is created. However, three additional fields are used -- minCount, maxCount and order.
    json={
        "subPropertyOf": "hyha:testProp",
        "datatype": "rdf:langString",
        "name": ["New Test Property@en", "New Test Feld@de"],
        "description": ["New Test Feld Beschreibung@de"],
        "languageIn": ["en", "fr", "it", "de"],
        "uniqueLang": True,
        "inSet": ["Kappa", "Gaga", "gugus"],
        "minLength": 1,
        "maxLength": 50,
        "pattern": r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$",
        "minExclusive": 5.5,
        "minInclusive": 5.5,
        "maxExclusive": 5.5,
        "maxInclusive": 5.5,
        "lessThan": "hyha:testProp",
        "lessThanOrEquals": "hyha:testProp",
        "minCount": 1,
        "maxCount": 2,
        "order": 2
    }
    :param project: The project where the datamodel is located
    :param resource: The name (Iri) of the resource where the property should be added
    :param property: The name (Iri) of the new property
    :return: A JSON informing about the success of the operation that has the following form:
    json={"message": f"Property in resource {resource} in datamodel {project} successfully created"}
    """
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
            dm[Iri(resource)][Iri(property)] = hasprop
        except OldapErrorNotFound as error:
            return jsonify({'message': str(error)}), 404
        except OldapErrorAlreadyExists as error:
            return jsonify({'message': str(error)}), 409
        except OldapError as error:
            return jsonify({'message': str(error)}), 500

        try:
            dm.update()
        except OldapErrorAlreadyExists as error:
            return jsonify({'message': str(error)}), 409
        except OldapError as error:  # Should not be reachable
            return jsonify({"message": str(error)}), 500
        return jsonify({"message": f"Property in resource {resource} in datamodel {project} successfully created"}), 200
    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400


@datamodel_bp.route('/datamodel/<project>', methods=['GET'])
def read_datamodel(project):
    """
    Viewfunction to read a specific datamodel.
    :param project: The project from whom the datamodel should be shown
    :return: A JSON containing all the information about the datamodel of the given project. It has the following form
    json={
        "project": project-name,
        "standaloneProperties": [{...}, {...}, ...],
        "resources": [{...}, {...}, ...]
    }
    For a more detailed fiew look into the .yaml file.
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
        dm = DataModel.read(con, project, ignore_cache=True)
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404
    except OldapError as error:
        return jsonify({'message': str(error)}), 500

    propclasses = set(dm.get_propclasses())
    resclasses = set(dm.get_resclasses())

    res = {
        "project": project,
        "standaloneProperties": [],
        "resources": []
    }

    for prop in propclasses:
        if prop in {'dcterms:created', 'dcterms:creator', 'dcterms:modified', 'dcterms:contributor'}:
            continue;
        kappa = {
            "iri": str(prop) if prop is not None else None,
            **({"created": str(dm[prop].created)} if dm[prop].created is not None else {}),
            **({"creator": str(dm[prop].creator)} if dm[prop].creator is not None else {}),
            **({"modified": str(dm[prop].modified)} if dm[prop].modified is not None else {}),
            **({"contributor": str(dm[prop].contributor)} if dm[prop].contributor is not None else {}),
            **({"subPropertyOf": str(dm[prop].subPropertyOf)} if dm[prop].subPropertyOf is not None else {}),
            **({"toClass": str(dm[prop].toClass)} if dm[prop].toClass is not None else {}),
            **({"datatype": str(dm[prop].datatype)} if dm[prop].datatype is not None else {}),
            **({"name": [f'{value}@{lang.name.lower()}' for lang, value in dm[prop].name.items()]} if dm[prop].name else {}),
            **({"description": [f'{value}@{lang.name.lower()}' for lang, value in dm[prop].description.items()]} if dm[prop].description else {}),
            **({"languageIn": [f'{tag}'[-2:].lower() for tag in dm[prop].languageIn]} if dm[prop].languageIn else {}),
            **({"uniqueLang": bool(dm[prop].uniqueLang)} if dm[prop].uniqueLang is not None else {}),
            **({"inSet": list({str(x) for x in dm[prop].inSet})} if dm[prop].inSet is not None else {}),
            **({"minLength": dm[prop].minLength.value} if dm[prop].minLength is not None else {}),
            **({"maxLength": dm[prop].maxLength.value} if dm[prop].maxLength is not None else {}),
            **({"pattern": str(dm[prop].pattern)} if dm[prop].pattern is not None else {}),
            **({"minExclusive": dm[prop].minExclusive.value} if dm[prop].minExclusive is not None else {}),
            **({"minInclusive": dm[prop].minInclusive.value} if dm[prop].minInclusive is not None else {}),
            **({"maxExclusive": dm[prop].maxExclusive.value} if dm[prop].maxExclusive is not None else {}),
            **({"maxInclusive": dm[prop].maxInclusive.value} if dm[prop].maxInclusive is not None else {}),
            **({"lessThan": str(dm[prop].lessThan)} if dm[prop].lessThan is not None else {}),
            **({"lessThanOrEquals": str(dm[prop].lessThanOrEquals)} if dm[prop].lessThanOrEquals is not None else {}),
        }
        res["standaloneProperties"].append(kappa)

    for resource in resclasses:
        gaga = {
            "iri": str(resource),
            **({"created": str(dm[prop].created)} if dm[prop].created is not None else {}),
            **({"creator": str(dm[prop].creator)} if dm[prop].creator is not None else {}),
            **({"modified": str(dm[prop].modified)} if dm[prop].modified is not None else {}),
            **({"contributor": str(dm[prop].contributor)} if dm[prop].contributor is not None else {}),
            **({"superclass": str(dm[resource].superclass)} if dm[resource].superclass is not None else {}),
            **({"label": [f'{value}@{lang.name.lower()}' for lang, value in dm[resource].label.items()]} if dm[resource].label else {}),
            **({"comment": [f'{value}@{lang.name.lower()}' for lang, value in dm[resource].comment.items()]} if dm[resource].comment else {}),
            **({"closed": bool(dm[resource].closed)} if dm[resource].closed is not None else {}),
            "hasProperty": []
        }
        for iri, hp in dm[resource].properties.items():
            hp.prop.subPropertyOf
            papa = {
                "property": {
                    "iri": str(iri),
                    **({"created": str(dm[prop].created)} if dm[prop].created is not None else {}),
                    **({"creator": str(dm[prop].creator)} if dm[prop].creator is not None else {}),
                    **({"modified": str(dm[prop].modified)} if dm[prop].modified is not None else {}),
                    **({"contributor": str(dm[prop].contributor)} if dm[prop].contributor is not None else {}),
                    **({"subPropertyOf": str(hp.prop.subPropertyOf)} if hp.prop.subPropertyOf is not None else {}),
                    **({"datatype": str(hp.prop.datatype)} if hp.prop.datatype is not None else {}),
                    **({"name": [f'{value}@{lang.name.lower()}' for lang, value in hp.prop.name.items()]} if hp.prop.name else {}),
                    **({"description": [f'{value}@{lang.name.lower()}' for lang, value in hp.prop.description.items()]} if hp.prop.description else {}),
                    **({"languageIn": [f'{tag}'[-2:].lower() for tag in hp.prop.languageIn]} if hp.prop.languageIn else {}),
                    **({"uniqueLang": bool(hp.prop.uniqueLang)} if hp.prop.uniqueLang is not None else {}),
                    **({"inSet": list({str(x) for x in hp.prop.inSet})} if hp.prop.inSet is not None else {}),
                    **({"minLength": hp.prop.minLength.value} if hp.prop.minLength is not None else {}),
                    **({"maxLength": hp.prop.maxLength.value} if hp.prop.maxLength is not None else {}),
                    **({"pattern": str(hp.prop.pattern)} if hp.prop.pattern is not None else {}),
                    **({"minExclusive": hp.prop.minExclusive.value} if hp.prop.minExclusive is not None else {}),
                    **({"minInclusive": hp.prop.minInclusive.value} if hp.prop.minInclusive is not None else {}),
                    **({"maxExclusive": hp.prop.maxExclusive.value} if hp.prop.maxExclusive is not None else {}),
                    **({"maxInclusive": hp.prop.maxInclusive.value} if hp.prop.maxInclusive is not None else {}),
                    **({"lessThan": str(hp.prop.lessThan)} if hp.prop.lessThan is not None else {}),
                    **({"lessThanOrEquals": str(hp.prop.lessThanOrEquals)} if hp.prop.lessThanOrEquals is not None else {}),
                },
                **({"maxCount": hp.maxCount.value} if hp.maxCount is not None else {}),
                **({"minCount": hp.minCount.value} if hp.minCount is not None else {}),
                **({"order": hp.order.value} if hp.order is not None else {}),
            }
            gaga["hasProperty"].append(papa)
        res["resources"].append(gaga)
    return res, 200


@datamodel_bp.route('/datamodel/<project>', methods=['DELETE'])
def delete_whole_datamodel(project):
    """
    Viewfunction that deletes an entire datamodel
    :param project: The project, where its datamodel should be deleted
    :return: A JSON to denote the success of the operation that has the following form:
    json={'message': 'Data model successfully deleted'}
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
    """
    Viewfunction that deletes an entire standalone property inside the projects datamodel
    :param project: The project, where the standalone property should be deleted
    :param standaloneprop: the Iri of the standalone property to be deleted
    :return: A JSON to denote the success of the operation that has the following form:
    json={'message': 'Data model successfully deleted'}
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
    return jsonify({'message': f'Standalone property in datamodel {project} successfully deleted'}), 200


@datamodel_bp.route('/datamodel/<project>/<resource>', methods=['DELETE'])
def delete_whole_resource(project, resource):
    """
    Viewfunction that deletes an entire resource inside the projects datamodel
    :param project: The project, where the resource should be deleted
    :param resource: The Iri of the resource to be deleted
    :return: A JSON to denote the success of the operation that has the following form:
    json={'message': 'Data model successfully deleted'}
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
    return jsonify({'message': f'Resource in datamodel {project} successfully deleted'}), 200


@datamodel_bp.route('/datamodel/<project>/<resource>/<property>', methods=['DELETE'])
def delete_hasprop_in_resource(project, resource, property):
    """
    Viewfunction that deletes an entire property inside a resource that is located in the projects datamodel
    :param project: The project, where the property is located
    :param resource: The Iri of the resource where the property should be deleted
    :param property: The Iri of the property to be deleted
    :return: A JSON to denote the success of the operation that has the following form:
    json={'message': 'Property successfully deleted'}
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
    return jsonify({'message': f'Property in resource {resource} in datamodel {project} successfully deleted'}), 200


def property_modifier(data: dict, property: PropertyClass) -> tuple[Response, int]:
    """
    A local helper function that modifies a given property. Used in:
    1. modify_standalone_property
    2. modify_attribute_in_has_prop
    :param data: The data of the property
    :param property: The property to be modified
    :return: A JSON to denote the success of the operation that has the following form:
    json={"message": "Property in resource successfully updated"}
    """
    known_json_fields = {"subPropertyOf", "toClass", "datatype", "name", "description", "languageIn", "uniqueLang", "inSet", "minLength", "maxLength", "pattern", "minExclusive", "minInclusive", "maxExclusive", "maxInclusive", "lessThan", "lessThanOrEquals"}
    unknown_json_field = set(data.keys()) - known_json_fields
    if unknown_json_field:
        return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to modify a project. Usable are {known_json_fields}. Aborded operation"}), 400
    if not set(data.keys()):
        return jsonify({"message": f"At least one field must be given to modify the project. Usable for the modify-viewfunction are {known_json_fields}"}), 400
    for attrname, attrval in data.items():
        if attrname == "languageIn":  # is a set of Language items
            if isinstance(attrval, list):
                if not attrval:
                    return jsonify({"message": f"Using an empty list is not allowed in the modify"}), 400
                for item in attrval:
                    if item is None:
                        return jsonify({"message": f"Using a None in a modifylist is not allowed"}), 400
                try:
                    tmpval = [Language[x.upper()] for x in attrval]
                    setattr(property, attrname, LanguageIn(tmpval))
                except (OldapErrorKey, OldapErrorType, KeyError) as error:
                    return jsonify({"message": str(error)}), 400
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
                        try:
                            Language[item.upper()]
                        except KeyError:
                            return jsonify({"message": f"The given languagetag '{item}' is not known. Available are {known_languages}"}), 400
                        try:
                            if property.languageIn is None:
                                property.languageIn = LanguageIn(Language[item.upper()])
                            else:
                                property.languageIn.add(Language[item.upper()])
                        except (OldapErrorKey, OldapErrorType, KeyError) as error:
                            return jsonify({"message": str(error)}), 400
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
                            property.languageIn.discard(Language[item.upper()])
                        except AttributeError:
                            return jsonify({"message": f"The entry '{item}' is not in the property and thus could not be deleted"}), 404
            elif attrval is None:
                delattr(property, attrname)
            else:
                return jsonify({"message": f"To modify {attrname} accepted is either a list, dict or None. Received {type(attrname).__name__} instead."}), 400
            continue
        if attrname == "inSet":  # a set of items of the required datatype
            datatype = property.datatype
            if isinstance(attrval, list):
                if not attrval:
                    return jsonify({"message": f"Using an empty list is not allowed in the modify"}), 400
                for item in attrval:
                    if item is None:
                        return jsonify({"message": f"Using a None in a modifylist is not allowed"}), 400
                try:
                    tmpval = [convert2datatype(x, datatype) for x in attrval]
                    setattr(property, attrname, XsdSet(tmpval))
                except (OldapErrorValue, OldapErrorType) as error:
                    return jsonify({"message": str(error)}), 400
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
                        try:
                            if property.inSet is None:
                                property.inSet = XsdSet(convert2datatype(item, datatype))
                            else:
                                property.inSet.add(convert2datatype(item, datatype))
                        except (OldapErrorValue, OldapErrorType) as error:
                            return jsonify({"message": str(error)}), 400
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
                            property.inSet.discard(convert2datatype(item, datatype))
                        except AttributeError:
                            return jsonify({"message": f"The entry '{item}' is not in the property and thus could not be deleted"}), 404
            elif attrval is None:
                delattr(property, attrname)
            else:
                return jsonify({"message": f"To modify {attrname} accepted is either a list, dict or None. Received {type(attrname).__name__} instead."}), 400
            continue

        if attrname == "name":
            try:
                process_langstring(property, PropClassAttr.NAME, attrval, property.notifier)
            except (OldapErrorKey, OldapErrorValue, OldapErrorInconsistency) as error:
                return jsonify({"message": str(error)}), 400
            except OldapError as error:
                return jsonify({"message": str(error)}), 500
            continue
        if attrname == "description":
            try:
                process_langstring(property, PropClassAttr.DESCRIPTION, attrval, property.notifier)
            except (OldapErrorKey, OldapErrorValue, OldapErrorInconsistency) as error:
                return jsonify({"message": str(error)}), 400
            except OldapError as error:
                return jsonify({"message": str(error)}), 500
            continue

        if attrval is None:
            delattr(property, attrname)
        else:
            try:
                property.oldapSetAttr(attrname, attrval)
            except ValueError as error:
                return jsonify({'message': str(error)}), 400
        continue
    return jsonify({"message": "Property in resource successfully updated"}), 200

@datamodel_bp.route('/datamodel/<project>/property/<property>', methods=['POST'])
def modify_standalone_property(project, property):
    """
    Viewfunction to modify a standalone property. A JSON is expected that has the following form. At least one field
    must be given. All fields are optional. At least one field must be given.
    json={
        "name": ["kappa@de"],
        "description": ["gigakappa@de"] or {'add': ['gigakappa@fr', ...], 'del': ['gaga@it', ...]},
        "languageIn": ['de', 'en', ...] or {'add': ['zu'], 'del': ['fr', 'it']},
        "uniqueLang": True,
        "minLength": 2,
        "maxLength": 51,
        "pattern": r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$",
        "minExclusive": 5.6,
        "minInclusive": 5.6,
        "maxExclusive": 5.6,
        "maxInclusive": 5.6,
    }
    :param project: The project where the standalone property is located
    :param property: The property Iri to be modified
    :return: A JSON informing about the success of the operation that has the following form:
    json={'message': 'Data model successfully modified'}
    """
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
            return jsonify({'message': str(error)}), 403
        except OldapError as error:
            return jsonify({'message': str(error)}), 500  # Should not be reachable
        return jsonify({'message': 'Data model successfully modified'}), 200
    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400


@datamodel_bp.route('/datamodel/<project>/<resource>', methods=['POST'])
def modify_resource(project, resource):
    """
    Viewfunction to modify a resource. A JSON is expected that has the following form. All fields are optional -- at least one needs to be given
    Note: To modify the fields of a property of the resource -- use modify_attribute_in_has_prop instead.
    json={
        "closed": False,
        "label": {"add": ["Ein Test@zu"], "del": ["Eine Buchseite@de"]},
        "comment": {"add": ["Ein Test@zu"], "del": ["A page of a book@en"]},
    }
    :param project: The project where the resource is located
    :param resource: The resource (Iri) to be modified
    :return: A JSON informing about the success of the operation that has the following form:
    json={'message': 'Data model successfully modified'}
    """
    known_json_fields = {"label", "comment", "closed"}
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
            if attrname == "label":
                try:
                    process_langstring(dm[Iri(resource)], ResClassAttribute.LABEL, attrval, dm[Iri(resource)].notifier)
                except (OldapErrorKey, OldapErrorValue, OldapErrorInconsistency) as error:
                    return jsonify({"message": str(error)}), 400
                except OldapError as error:
                    return jsonify({"message": str(error)}), 500
                continue
            if attrname == "comment":
                try:
                    process_langstring(dm[Iri(resource)], ResClassAttribute.COMMENT, attrval, dm[Iri(resource)].notifier)
                except (OldapErrorKey, OldapErrorValue, OldapErrorInconsistency) as error:
                    return jsonify({"message": str(error)}), 400
                except OldapError as error:
                    return jsonify({"message": str(error)}), 500
                continue

            # if attrname == "label" or attrname == "comment":
            #     if isinstance(attrval, list):
            #         if not attrval:
            #             return jsonify({"message": f"Using an empty list is not allowed in the modify"}), 400
            #         for item in attrval:
            #             if item is None:
            #                 return jsonify({"message": f"Using a None in a modifylist is not allowed"}), 400
            #             try:
            #                 if item[-3] != '@':
            #                     return jsonify({"message": f"Please add a correct language tags e.g. @de"}), 400
            #             except IndexError as error:
            #                 return jsonify({"message": f"Please add a correct language tags e.g. @de"}), 400
            #             lang = item[-2:].upper()
            #             try:
            #                 Language[lang]
            #             except KeyError as error:
            #                 return jsonify({"message": f"{lang} is not a valid language. Supportet are {known_languages}"}), 400
            #
            #             setattr(dm[Iri(resource)], attrname, LangString(attrval))
            #     elif isinstance(attrval, dict):
            #         if not attrval:
            #             return jsonify({"message": f"Using an empty dict is not allowed in the modify"}), 400
            #         if not set(attrval.keys()).issubset({"add", "del"}):
            #             return jsonify({"message": f"The sended command (keyword in dict) is not known"}), 400
            #         if "add" in attrval:
            #             adding = attrval.get("add", [])
            #             if not isinstance(adding, list):
            #                 return jsonify({"message": "The given attributes in add and del must be in a list"}), 400
            #             if not adding:
            #                 return jsonify({"message": f"Using an empty list is not allowed in the modify"}), 400
            #             for item in adding:
            #                 if item is None:
            #                     return jsonify({"message": f"Using a None in a modifylist is not allowed"}), 400
            #                 try:
            #                     if item[-3] != '@':
            #                         return jsonify({"message": f"Please add a correct language tags e.g. @de"}), 400
            #                 except IndexError as error:
            #                     return jsonify({"message": f"Please add a correct language tags e.g. @de"}), 400
            #                 lang = item[-2:].upper()
            #                 try:
            #                     tmp = getattr(dm[Iri(resource)], attrname)
            #                     tmp[Language[lang]] = item[:-3]
            #                     #dm[Iri(resource)]['rdfs:'+ attrname][Language[lang]] = item[:-3]
            #                 except KeyError as error:
            #                     return jsonify({"message": f"{lang} is not a valid language. Supportet are {known_languages}"}), 400
            #         if "del" in attrval:
            #             deleting = attrval.get("del", [])
            #             if not isinstance(deleting, list):
            #                 return jsonify({"message": "The given attributes in add and del must be in a list"}), 400
            #             if not deleting:
            #                 return jsonify({"message": f"Using an empty list is not allowed in the modify"}), 400
            #             for item in deleting:
            #                 if item is None:
            #                     return jsonify({"message": f"Using a None in a modifylist is not allowed"}), 400
            #                 try:
            #                     if item[-3] != '@':
            #                         return jsonify({"message": f"Please add a correct language tags e.g. @de"}), 400
            #                 except IndexError as error:
            #                     return jsonify({"message": f"Please add a correct language tags e.g. @de"}), 400
            #                 lang = item[-2:].upper()
            #                 try:
            #                     tmp = getattr(dm[Iri(resource)], attrname)
            #                     del tmp[Language[lang]]
            #                 except KeyError as error:
            #                     return jsonify({"message": f"{lang} is not a valid language. Supportet are {known_languages}"}), 400
            #     elif attrval is None:
            #         delattr(dm[Iri(resource)], attrname)
            #         # del dm[Iri(resource)][attrname]
            #     else:
            #         return jsonify({"message": f"To modify {attrname} accepted is either a list, dict or None. Received {type(attrname).__name__} instead."}), 400
            #     continue

            if attrval is not None:
                setattr(dm[Iri(resource)], attrname, attrval)
        try:
            dm.update()
        except OldapErrorNoPermission as error:
            return jsonify({'message': str(error)}), 403
        except OldapError as error:
            return jsonify({'message': str(error)}), 500  # Should not be reachable
        return jsonify({'message': 'Data model successfully modified'}), 200
    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400


@datamodel_bp.route('/datamodel/<project>/<resiri>/<propiri>', methods=['POST'])
def modify_attribute_in_has_prop(project, resiri, propiri):
    """
    Viewfunction to modify the fields of a single property inside a resource.A JSON is expected that has the following form.
    json={
        "property": {
            "subPropertyOf": "hyha:kappa",
            "class": "hyha:kappa",
            "datatype": "xsd:string",
            "name": ["pappakappa@de"],
            "description": ["descriptiv stuff@en"],
            "languageIn": {"add": ["zu"], "del": ["fr"]},
            "uniqueLang": True,
            "inSet": ["Renault", "Opel", "BMW", "Mercedes"],
            "minLength": 2,
            "maxLength": 5,
            "pattern": r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$",
            "minExclusive": 5.5,
            "minInclusive": 5.5,
            "maxExclusive": 5.5,
            "maxInclusive": 5.5,
            "lessThan": 2,
            "lessThanOrEquals": 2
        },
        "maxCount": 4,
        "minCount": 2,
        "order": 42
    }
    :param project: The project where the resource is located
    :param resiri: The Iri of the resource where the attributes are located that should be changed
    :param propiri: The Iri of the property where the attributes are located that should be changed
    :return: A JSON informing about the success of the operation that has the following form:
    json={'message': 'Data model successfully modified'}
    """
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
        return jsonify({'message': str(error)}), 403
    except OldapError as error:
        return jsonify({'message': str(error)}), 500  # Should not be reachable
    return jsonify({'message': 'Data model successfully modified'}), 200











