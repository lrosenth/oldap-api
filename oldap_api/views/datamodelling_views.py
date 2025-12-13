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
import json
from csv import excel
from pprint import pprint

from flask import Blueprint, request, jsonify, Response
from oldaplib.src.connection import Connection
from oldaplib.src.datamodel import DataModel
from oldaplib.src.dtypes.languagein import LanguageIn
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.dtypes.xsdset import XsdSet
from oldaplib.src.enums.externalontologyattr import ExternalOntologyAttr
from oldaplib.src.enums.language import Language
from oldaplib.src.enums.owlpropertytype import OwlPropertyType
from oldaplib.src.enums.propertyclassattr import PropClassAttr
from oldaplib.src.enums.resourceclassattr import ResClassAttribute
from oldaplib.src.enums.xsd_datatypes import XsdDatatypes
from oldaplib.src.externalontology import ExternalOntology
from oldaplib.src.hasproperty import HasProperty
from oldaplib.src.helpers.convert2datatype import convert2datatype
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.observable_set import ObservableSet
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorNotFound, OldapErrorValue, OldapErrorNoPermission, \
    OldapErrorInconsistency, OldapErrorAlreadyExists, OldapErrorKey, OldapErrorType
from oldaplib.src.iconnection import IConnection
from oldaplib.src.project import Project
from oldaplib.src.propertyclass import PropertyClass
from oldaplib.src.resourceclass import ResourceClass
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName

from oldap_api.apierror import ApiError
from oldap_api.helpers.process_langstring import process_langstring
from oldap_api.views import known_languages

datamodel_bp = Blueprint('datamodel', __name__, url_prefix='/admin')


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
        con = Connection(token=token,
                         context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    try:
        dm = DataModel.read(con, project)
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404
    except OldapError as error:
        return jsonify({'message': str(error)}), 500

    extontos = set(dm.get_extontos())
    propclasses = set(dm.get_propclasses())
    resclasses = set(dm.get_resclasses())

    res = {
        "project": project,
        "externalOntologies": [],
        "standaloneProperties": [],
        "resources": []
    }

    for onto in extontos:
        res['externalOntologies'].append({
            **({"created": str(dm[onto].created)} if dm[onto].created is not None else {}),
            **({"creator": str(dm[onto].creator)} if dm[onto].creator is not None else {}),
            **({"modified": str(dm[onto].modified)} if dm[onto].modified is not None else {}),
            **({"contributor": str(dm[onto].contributor)} if dm[onto].contributor is not None else {}),
            "prefix": str(dm[onto].prefix),
            "namespaceIri": str(dm[onto].namespaceIri),
            **({"label": [f'{value}@{lang.name.lower()}' for lang, value in dm[onto].label.items()]} if dm[onto].label else {}),
            **({"comment": [f'{value}@{lang.name.lower()}' for lang, value in dm[onto].comment.items()]} if dm[onto].comment else {}),
        })

    for prop in propclasses:
        if prop in {'dcterms:created', 'dcterms:creator', 'dcterms:modified', 'dcterms:contributor'}:
            continue
        data = {
            "iri": str(prop) if prop is not None else None,
            **({"created": str(dm[prop].created)} if dm[prop].created is not None else {}),
            **({"creator": str(dm[prop].creator)} if dm[prop].creator is not None else {}),
            **({"modified": str(dm[prop].modified)} if dm[prop].modified is not None else {}),
            **({"contributor": str(dm[prop].contributor)} if dm[prop].contributor is not None else {}),
            **({"type": [val.name for val in dm[prop].type if
                         val not in (OwlPropertyType.OwlDataProperty, OwlPropertyType.OwlObjectProperty)]} if dm[prop].type is not None else {}),
            **({"projectid": str(dm[prop].projectShortName)} if dm[prop].projectShortName is not None else {}),
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
            **({"inverseOf": str(dm[prop].inverseOf)} if dm[prop].inverseOf is not None else {}),
            **({"equivalentProperty": str(dm[prop].equivalentProperty)} if dm[prop].equivalentProperty is not None else {}),
        }
        res["standaloneProperties"].append(data)

    for resource in resclasses:
        superclass_iris = None
        if dm[resource].superclass:
            superclass_iris = [str(x) for x, y in dm[resource].superclass.items()]
        rdata = {
            "iri": str(resource),
            **({"created": str(dm[resource].created)} if dm[resource].created is not None else {}),
            **({"creator": str(dm[resource].creator)} if dm[resource].creator is not None else {}),
            **({"modified": str(dm[resource].modified)} if dm[resource].modified is not None else {}),
            **({"contributor": str(dm[resource].contributor)} if dm[resource].contributor is not None else {}),
            **({"projectid": str(dm[resource].projectid)} if dm[resource].projectid is not None else {}),
            **({"superclass": superclass_iris} if superclass_iris is not None else {}),
            **({"label": [f'{value}@{lang.name.lower()}' for lang, value in dm[resource].label.items()]} if dm[resource].label else {}),
            **({"comment": [f'{value}@{lang.name.lower()}' for lang, value in dm[resource].comment.items()]} if dm[resource].comment else {}),
            **({"closed": bool(dm[resource].closed)} if dm[resource].closed is not None else {}),
            "hasProperty": []
        }
        for iri, hp in dm[resource].properties.items():
            # hp.prop.subPropertyOf
            pdata = {
                "property": {
                    "iri": str(iri),
                    **({"created": str(hp.prop.created)} if hp.prop.created is not None else {}),
                    **({"creator": str(hp.prop.creator)} if hp.prop.creator is not None else {}),
                    **({"modified": str(hp.prop.modified)} if hp.prop.modified is not None else {}),
                    **({"contributor": str(hp.prop.contributor)} if hp.prop.contributor is not None else {}),
                    **({"type": [val.name for val in hp.prop.type if
                                 val not in (OwlPropertyType.OwlDataProperty, OwlPropertyType.OwlObjectProperty)]} if hp.prop.type is not None else {}),
                    **({"projectid": str(hp.prop.projectShortName)} if hp.prop.projectShortName is not None else {}),
                    **({"subPropertyOf": str(hp.prop.subPropertyOf)} if hp.prop.subPropertyOf is not None else {}),
                    **({"toClass": str(hp.prop.toClass)} if hp.prop.toClass is not None else {}),
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
                    **({"inverseOf": str(hp.prop.inverseOf)} if hp.prop.inverseOf is not None else {}),
                    **({"equivalentProperty": str(hp.prop.equivalentProperty)} if hp.prop.equivalentProperty is not None else {}),
                },
                **({"maxCount": hp.maxCount.value} if hp.maxCount is not None else {}),
                **({"minCount": hp.minCount.value} if hp.minCount is not None else {}),
                **({"order": hp.order.value} if hp.order is not None else {}),
            }
            rdata["hasProperty"].append(pdata)
        res["resources"].append(rdata)
    return res, 200

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
        con = Connection(token=token,
                         context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    dm = DataModel(con=con, project=project)

    try:
        dm.create()
    except OldapErrorNoPermission as error:
        return jsonify({"message": f"Permission denied: {str(error)}"}), 403
    except OldapErrorAlreadyExists as error:
        return jsonify({"message": f"A datamodel for the project {project} already exists"}), 400
    except OldapErrorInconsistency as error:
        return jsonify({"message": f"Datamodel creation failed due to inconsistency: {str(error)}"}), 400
    except OldapError as error:  # Should not be reachable
        return jsonify({"message": str(error)}), 500

    return jsonify({"message": "Empty datamodel successfully created"}), 200


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
        con = Connection(token=token,
                         context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    try:
        dm = DataModel.read(con, project, ignore_cache=True)
    except OldapErrorValue as error:
        return jsonify({'message': str(error)}), 400
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404

    try:
        dm.delete()
    except OldapError as error:  # Should not be reachable
        return jsonify({'message': str(error)}), 500
    return jsonify({'message': 'Data model successfully deleted'}), 200

#================================================================================

@datamodel_bp.route('/datamodel/<project>/download', methods=['GET'])
def download_datamodel(project):
    out = request.headers['Authorization']
    b, token = out.split()

    try:
        con = Connection(token=token,
                         context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403
    try:
        dm = DataModel.read(con, project)
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404
    except OldapError as error:
        return jsonify({'message': str(error)}), 500
    trigstr = dm.write_as_str()
    return Response(
        trigstr,
        mimetype='application/trig',
        headers={ 'Content-Disposition': f'attachment; filename="{dm._project.projectShortName}.trig"' })

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
    known_json_fields = {"superclass", "label", "comment", "closed"}
    out = request.headers['Authorization']
    b, token = out.split()

    resourceIri = Xsd_QName(resource, validate=True)

    try:
        con = Connection(token=token,
                         context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    try:
        dm = DataModel.read(con, project, ignore_cache=True)
    except OldapErrorValue as error:
        return jsonify({'message': str(error)}), 403
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404

    if request.is_json:
        data = request.get_json()
        unknown_json_field = set(data.keys()) - known_json_fields
        if unknown_json_field:
            return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to modify a standalone property. Usable are {known_json_fields}. aborted operation"}), 400
        if not set(data.keys()):
            return jsonify({"message": f"At least one field must be given to modify the standalone property. Usable for the modify-viewfunction are {known_json_fields}"}), 400

        for attrname, attrval in data.items():
            if attrname == "label":
                try:
                    process_langstring(dm[resourceIri], ResClassAttribute.LABEL, attrval, dm[resourceIri].notifier)
                except (OldapErrorKey, OldapErrorValue, OldapErrorInconsistency) as error:
                    return jsonify({"message": str(error)}), 400
                except OldapError as error:
                    return jsonify({"message": str(error)}), 500
                continue
            if attrname == "comment":
                try:
                    process_langstring(dm[resourceIri], ResClassAttribute.COMMENT, attrval, dm[resourceIri].notifier)
                except (OldapErrorKey, OldapErrorValue, OldapErrorInconsistency) as error:
                    return jsonify({"message": str(error)}), 400
                except OldapError as error:
                    return jsonify({"message": str(error)}), 500
                continue
            if attrname == "superclass":
                if isinstance(attrval, list):
                    if not attrval:
                        return jsonify({"message": f"Using an empty list is not allowed in the modify"}), 400
                    for item in attrval:
                        if item is None:
                            return jsonify({"message": f"Using a None in a modifylist is not allowed"}), 400
                    try:
                        setattr(dm[resourceIri], attrname, attrval)
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
                        try:
                            dm[resourceIri].add_superclasses(adding, validate=True)
                        except (OldapErrorKey, OldapErrorType, KeyError) as error:
                            return jsonify({"message": str(error)}), 400
                    if "del" in attrval:
                        deleting = attrval.get("del", [])
                        if not isinstance(deleting, list):
                            return jsonify({"message": "The given attributes in add and del must be in a list"}), 400
                        if not deleting:
                            return jsonify({"message": f"Using an empty list is not allowed in the modify"}), 400
                        try:
                            dm[resourceIri].del_superclasses(deleting, validate=True)
                        except (OldapErrorKey, OldapErrorType, KeyError) as error:
                            return jsonify({"message": str(error)}), 400
                continue
            if attrval is not None:
                setattr(dm[resourceIri], attrname, attrval)
        try:
            dm.update()
        except OldapErrorValue as error:
            return jsonify({'message': str(error)}), 403
        except OldapErrorNoPermission as error:
            return jsonify({'message': str(error)}), 403
        except OldapError as error:
            return jsonify({'message': str(error)}), 500  # Should not be reachable
        return jsonify({'message': 'Data model successfully modified'}), 200
    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400


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
    known_json_fields = {"iri", "type", "subPropertyOf", "class", "datatype", "name", "description", "languageIn", "uniqueLang",
                         "inSet", "minLength", "maxLength", "pattern", "minExclusive", "minInclusive", "maxExclusive",
                         "maxInclusive", "lessThan", "lessThanOrEquals", "inverseOf", "equivalentProperty"}

    unknown_json_field = set(data.keys()) - known_json_fields
    if unknown_json_field:
        raise ApiError(f"The Field/s {unknown_json_field} is/are not used to create a permissionset. Usable are {known_json_fields}. aborted operation")
    iri = property_iri  # Iri, z.B. "myproj:pageOf"
    typelist = data.get("type", None)  # z.B. ["StatementProperty", "SymmetricProperty"]
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
    inverseOf = data.get("inverseOf", None)
    equivalentProperty = data.get("equivalentProperty", None)

    if datatype is None and toClass is None:
        raise ApiError("At least one of the two -- datatype or class -- needs to be given")
    if datatype is not None and toClass is not None:
        raise ApiError("It is not allowed to give both the datatype and the class at the same time")
    if typelist:
        if not isinstance(typelist, (list, set)):
            typelist = {typelist}
        try:
            typelist = {OwlPropertyType[val] for val in typelist}
        except KeyError as error:
            raise ApiError(f"Invalid property type: {error}")

    prop = PropertyClass(
        con=con,
        project=project,
        type=None if typelist is None else typelist,
        property_class_iri=Xsd_QName(iri),
        subPropertyOf=subPropertyOf,
        toClass= None if toClass is None else Xsd_QName(toClass, validate=True),
        datatype = None if datatype is None else XsdDatatypes(datatype),
        name=LangString(name, validate=True),
        description=LangString(description, validate=True),
        languageIn=languageIn,
        uniqueLang=Xsd_boolean(uniqueLang, validate=True),
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
        inverseOf=inverseOf,
        equivalentProperty=equivalentProperty,
    )
    return prop

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
            con = Connection(token=token,
                             context_name="DEFAULT")
        except OldapError as error:
            return jsonify({"message": f"Connection failed: {str(error)}"}), 403

        data = request.get_json()

        unknown_json_field = set(data.keys()) - known_json_fields
        if unknown_json_field:
            return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to create a resource. Usable are {known_json_fields}. Aborted operation (2)"}), 400
        iri = resource
        superclass = data.get("superclass", None)
        label = data.get("label", None)
        comment = data.get("comment", None)
        closed = data.get("closed", None)
        hasProperty = data.get("hasProperty", None)

        try:
            project = Project.read(con, project)
        except OldapErrorValue as error:
            return jsonify({"message": str(error)}), 400
        except OldapErrorNotFound as error:
            return jsonify({"message": str(error)}), 404
        except OldapError as error:
            return jsonify({"message": str(error)}), 500


        try:
            dm = DataModel.read(con, project, ignore_cache=True)
        except OldapError as error:
            return jsonify({"message": str(error)}), 404

        try:
            resource = ResourceClass(con=con,
                                     project=project,
                                     owlclass_iri=iri,
                                     superclass=superclass,
                                     comment=comment,
                                     closed=closed,
                                     label=label,
                                     validate=True)
        except OldapErrorValue as error:
            return jsonify({"message": str(error)}), 400
        except OldapError as error:
            return jsonify({"message": f"Oldap Error: {str(error)}"}), 500
        try:
            dm[Xsd_QName(iri)] = resource
        except OldapErrorAlreadyExists as error:
            return jsonify({"message": str(error)}), 409

        if hasProperty and isinstance(hasProperty, list):
            for prop in hasProperty:
                unknown_hasproperty_field = set(prop.keys()) - known_hasproperty_fields
                if unknown_hasproperty_field:
                    return jsonify({"message": f"The Field/s {unknown_hasproperty_field} is/are not used to create a property in a resource. Usable are {known_hasproperty_fields}. aborted operation"}), 400
                if not mandatory_hasproperty_fields.issubset(set(prop.keys())):
                    return jsonify({"message": f"The Fields {mandatory_hasproperty_fields} are required to create a resource. Used where {set(prop.keys())}. Usable are {known_hasproperty_fields}"}), 400
                if isinstance(prop["property"], dict):
                    # we have a real internal, non-standalone property
                    if prop["property"].get("iri", None) is None:
                        return jsonify({"message": f"Property IRI is missing in HasProperty"}), 400
                    try:
                        property_iri = prop["property"]["iri"]
                        endprop = process_property(con=con, project=project, property_iri=property_iri, data=prop["property"])
                        hp1 = HasProperty(con=con, project=project, prop=endprop, minCount=prop.get("minCount"), maxCount=prop.get("maxCount"), order=prop.get("order"))
                    except ApiError as error:
                        return jsonify({"message": str(error)}), 400
                    dm[Xsd_QName(iri)][endprop.property_class_iri] = hp1
                elif isinstance(prop["property"], str):
                    # we reference a standalone property
                    if prop["property"] not in dm.get_propclasses():
                        return jsonify({"message": f"Property {prop['property']} is not in the datamodel"}), 400
                    hp1 = HasProperty(con=con, project=project, prop=Xsd_QName(prop["property"]), minCount=prop["minCount"],
                                      maxCount=prop["maxCount"], order=prop["order"])
                    dm[Xsd_QName(iri)][Xsd_QName(prop["property"])] = hp1
                else:
                    return jsonify({"message": f"The Field 'property' must be an iri of a standalone property or a dictionary with ainternal property definition."}), 400

        try:
            dm.update()
        except OldapErrorValue as error:
            return jsonify({"message": str(error)}), 400
        except OldapErrorAlreadyExists as error:
            return jsonify({"message": str(error)}), 409
        except OldapError as error:  # Should not be reachable
            return jsonify({"message": str(error)}), 500
        return jsonify({"message": f"Resource in datamodel {project} successfully created"}), 200
    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400

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
        con = Connection(token=token,
                         context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    try:
        dm = DataModel.read(con, project, ignore_cache=True)
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404

    try:
        del dm[resource]
        dm.update()
    except OldapErrorValue as error:
        return jsonify({'message': str(error)}), 404
    except OldapError as error:
        return jsonify({'message': str(error)}), 500  # Should not be reachable
    return jsonify({'message': f'Resource in datamodel {project} successfully deleted'}), 200


@datamodel_bp.route('/datamodel/<project>/extonto/<prefix>', methods=['PUT'])
def add_external_ontology_to_datamodel(project, prefix):
    """
    Adds an external ontology reference to a specified data model in a project. This operation validates the provided
    data fields and ensures compliance with the ontology addition rules. It establishes a connection using a provided
    authorization token and processes the request's JSON data. The function performs necessary checks for valid fields
    and handles exceptions appropriately during both the connection and ontology reference creation processes.

    :param project: The name of the project where the external ontology reference will be added
    :type project: str
    :param prefix: The prefix identifying the ontology within the project
    :type prefix: str
    :return: A Flask response object containing a message and an HTTP status code
    :rtype: flask.Response
    :raises: Raises exceptions for various connection, validation, and processing errors handled internally to
             provide user-friendly error messages with appropriate HTTP status codes
    """
    known_json_fields = {"namespaceIri", "label", "comment"}
    out = request.headers['Authorization']
    b, token = out.split()

    if not request.is_json:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400

    try:
        con = Connection(token=token,
                         context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    data = request.get_json()
    unknown_json_field = set(data.keys()) - known_json_fields
    if unknown_json_field:
        return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to add an external ontology reference. Usable are {known_json_fields}. Aborted operation (1)"}), 400
    if not set(data.keys()):
        return jsonify({"message": f"At least one field must be given to add an external ontology reference. Usable for the add-viewfunction are {known_json_fields}"}), 400

    namespaceIri = data.get("namespaceIri", None)
    label = data.get("label", None)
    comment = data.get("comment", None)

    try:
        dm = DataModel.read(con, project, ignore_cache=True)
    except OldapError as error:
        return jsonify({"message": str(error)}), 404

    try:
        extonto = ExternalOntology(con=con,
                                   projectShortName=Xsd_NCName(project, validate=True),
                                   prefix=Xsd_NCName(prefix, validate=True),
                                   namespaceIri=NamespaceIRI(namespaceIri, validate=True),
                                   label=label,
                                   comment=comment,
                                   validate=True)
    except OldapErrorValue as error:
        return jsonify({"message": str(error)}), 400
    except OldapError as error:
        return jsonify({"message": f"Oldap Error: {str(error)}"}), 500

    try:
        dm[Xsd_QName(project, prefix)] = extonto
        dm.update()
    except OldapErrorValue as error:
        return jsonify({"message": str(error)}), 400
    except OldapErrorAlreadyExists as error:
        return jsonify({"message": str(error)}), 409
    except OldapError as error:  # Should not be reachable
        return jsonify({"message": str(error)}), 500
    return jsonify({"message": f'External ontology reference "{project}:{prefix}" successfully added'}), 200


@datamodel_bp.route('/datamodel/<project>/extonto/<prefix>', methods=['DELETE'])
def delete_external_ontology_to_datamodel(project, prefix):
    out = request.headers['Authorization']
    b, token = out.split()

    try:
        con = Connection(token=token,
                         context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    try:
        dm = DataModel.read(con, project, ignore_cache=True)
    except OldapErrorValue as error:
        return jsonify({'message': str(error)}), 400
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404

    try:
        del dm[Xsd_QName(project, prefix, validate=True)]
        dm.update()
    except OldapErrorValue as error:
        return jsonify({'message': str(error)}), 400
    except OldapError as error:  # Should not be reachable
        return jsonify({'message': str(error)}), 500
    return jsonify({'message': f'External ontology reference "{project}:{prefix}" successfully deleted'}), 200


@datamodel_bp.route('/datamodel/<project>/extonto/<prefix>', methods=['POST'])
def modify_external_ontology_in_datamodel(project, prefix):
    known_json_fields = {"namespaceIri", "label", "comment"}
    out = request.headers['Authorization']
    b, token = out.split()

    if not request.is_json:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400
    data = request.get_json()
    unknown_json_field = set(data.keys()) - known_json_fields
    if unknown_json_field:
        return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to modify an external ontology reference. Usable are {known_json_fields}. Aborted operation"}), 400
    if not set(data.keys()):
        return jsonify({"message": f"At least one field must be given to modify an external ontology reference. Usablable for the modify-viewfunction are {known_json_fields}"}), 400
    namespaceIri = data.get("namespaceIri", "NotSent")
    label = data.get("label", "NotSent")
    comment = data.get("comment", "NotSent")

    try:
        con = Connection(token=token,
                         context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    try:
        dm = DataModel.read(con, project, ignore_cache=True)
    except OldapErrorValue as error:
        return jsonify({'message': str(error)}), 400
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404

    onto = Xsd_QName(project, prefix, validate=True)

    try:
        if namespaceIri != "NotSent":
            dm[onto].namespaceIri = NamespaceIRI(namespaceIri, validate=True)
        process_langstring(dm[onto], ExternalOntologyAttr.LABEL, label, dm[onto].notifier)
        process_langstring(dm[onto], ExternalOntologyAttr.COMMENT, comment, dm[onto].notifier)
        dm.update()
    except OldapErrorKey as error:
        return jsonify({"message": str(error)}), 400
    except OldapErrorValue as error:
        return jsonify({"message": str(error)}), 400
    except OldapError as error:
        return jsonify({"message": str(error)}), 500
    return jsonify({"message": f'External ontology reference "{project}:{prefix}" successfully modified'}), 200


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
            con = Connection(token=token,
                             context_name="DEFAULT")
        except OldapError as error:
            return jsonify({"message": f"Connection failed: {str(error)}"}), 403

        data = request.get_json()
        try:
            prop = process_property(con=con, project=project, property_iri=property, data=data)
            prop.force_external()
        except (ApiError, AttributeError, TypeError, ValueError, OldapErrorValue, OldapErrorInconsistency) as error:
            return jsonify({"message": str(error)}), 400
        except OldapErrorNotFound as error:
            return jsonify({'message': str(error)}), 404
        except OldapError as error:
            return jsonify({'message': str(error)}), 500  # Should not be reachable

        try:
            dm = DataModel.read(con, project, ignore_cache=True)
            dm[prop.property_class_iri] = prop
            dm.update()

        except OldapErrorValue as error:
            return jsonify({'message': str(error)}), 400
        except OldapErrorAlreadyExists as error:
            return jsonify({"message": str(error)}), 409
        except OldapError as error:  # Should not be reachable
            return jsonify({"message": str(error)}), 500
        return jsonify({"message": f"Standalone property in datamodel {project} successfully created"}), 200
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
    known_json_fields = {"subPropertyOf", "datatype", "class", "name", "description", "languageIn", "uniqueLang", "inSet", "minLength", "maxLength", "pattern", "minExclusive", "minInclusive", "maxExclusive", "maxInclusive", "lessThan", "lessThanOrEquals", "minCount", "maxCount", "order"}
    out = request.headers['Authorization']
    b, token = out.split()

    if request.is_json:
        try:
            con = Connection(token=token,
                             context_name="DEFAULT")
        except OldapError as error:
            return jsonify({"message": f"Connection failed: {str(error)}"}), 403

        try:
            project = Project.read(con, project)
        except OldapErrorValue as error:
            return jsonify({"message": str(error)}), 400
        except OldapErrorNotFound as error:
            return jsonify({"message": str(error)}), 404
        except OldapError as error:
            return jsonify({"message": str(error)}), 500

        data = request.get_json()
        unknown_json_field = set(data.keys()) - known_json_fields
        if unknown_json_field:
            return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to create a resource. Usable are {known_json_fields}. Aborted operation (1)"}), 400
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

        if (data):
            # we have data for an internal property
            try:
                prop = process_property(con=con, project=project, property_iri=property, data=data)
            except ApiError as error:  # should not be reachable
                return jsonify({"message": str(error)}), 400
        else:
            # we should have a standalone property referenced
            try:
                prop = Xsd_QName(property)
            except OldapErrorValue as error:
                return jsonify({"message": str(error)}), 400
        hasprop = HasProperty(con=con, project=project, prop=prop, minCount=mincount, maxCount=maxcount, order=order)
        try:
            dm = DataModel.read(con, project, ignore_cache=True)
            dm[Xsd_QName(resource)][Xsd_QName(property)] = hasprop
        except KeyError as error:
            return jsonify({'message': str(error)}), 404
        except OldapErrorValue as error:
            return jsonify({"message": str(error)}), 400
        except OldapErrorNotFound as error:
            return jsonify({'message': str(error)}), 404
        except OldapErrorAlreadyExists as error:
            return jsonify({'message': str(error)}), 409
        except OldapError as error:
            return jsonify({'message': str(error)}), 500

        try:
            dm.update()
        except OldapErrorValue as error:
            return jsonify({"message": str(error)}), 400
        except OldapErrorAlreadyExists as error:
            return jsonify({'message': str(error)}), 409
        except OldapError as error:  # Should not be reachable
            return jsonify({"message": str(error)}), 500
        return jsonify({"message": f"Property in resource {resource} in datamodel {project} successfully created"}), 200
    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400


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
        con = Connection(token=token,
                         context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    try:
        dm = DataModel.read(con, project, ignore_cache=True)
    except OldapErrorValue as error:
        return jsonify({'message': str(error)}), 400
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404

    try:
        del dm[standaloneprop]
        dm.update()
    except OldapErrorValue as error:
        return jsonify({'message': str(error)}), 400
    except OldapError as error:  # Should not be reachable
        return jsonify({'message': str(error)}), 500
    return jsonify({'message': f'Standalone property in datamodel {project} successfully deleted'}), 200



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
        con = Connection(token=token,
                         context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    try:
        dm = DataModel.read(con, project, ignore_cache=True)
    except OldapErrorValue as error:
        return jsonify({'message': str(error)}), 404
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404

    try:
        del dm[Xsd_QName(resource)][Xsd_QName(property)]
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

    def process_owl_propertytype(items: list[str]) -> set[OwlPropertyType]:
        if None in items:
            raise OldapErrorValue("None is not allowed in the modify OwlPropertyType")
        tmpval = {OwlPropertyType[x] for x in items}
        if OwlPropertyType.OwlDataProperty in tmpval:
            raise OldapErrorValue("Setting OwlDataProperty directly is not allowed")
        if OwlPropertyType.OwlObjectProperty in tmpval:
            raise OldapErrorValue("Setting OwlObjectProperty directly is not allowed")
        return list(tmpval)

    known_json_fields = {"subPropertyOf", "type", "class", "datatype", "name", "description", "languageIn", "uniqueLang",
                         "inSet", "minLength", "maxLength", "pattern", "minExclusive", "minInclusive", "maxExclusive",
                         "maxInclusive", "lessThan", "lessThanOrEquals", "inverseOf", "equivalentProperty"}
    unknown_json_field = set(data.keys()) - known_json_fields
    if unknown_json_field:
        return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to modify a project. Usable are {known_json_fields}. Aborted operation"}), 400
    if not set(data.keys()):
        return jsonify({"message": f"At least one field must be given to modify the project. Usable for the modify-viewfunction are {known_json_fields}"}), 400
    for attrname, attrval in data.items():
        if attrname == 'type':
            if isinstance(attrval, list):
                if not attrval:
                    return jsonify({"message": f"Using an empty list is not allowed in the modify"}), 400
                if None in attrval:
                    return jsonify({"message": f"None is not allowed in the modify"}), 400
                try:
                    tmpval = process_owl_propertytype(attrval)
                    setattr(property, attrname, tmpval)  # TODO: IS THIS CORRECT? OR should it be an ObservableSet?
                    #property._attributes[attrname] = tmpval
                    #property.type = tmpval
                except (OldapErrorValue, OldapErrorType, KeyError) as error:
                    return jsonify({"message": str(error)}), 400
            elif isinstance(attrval, dict):
                if not set(attrval.keys()).issubset({"add", "del"}):
                    return jsonify({"message": f"The  command (keyword in dict) is not known"}), 400
                if "add" in attrval:
                    adding = attrval.get("add", [])
                    if not isinstance(adding, list):
                        return jsonify({"message": "The given attributes in add and del must be in a list"}), 400
                    if not adding:
                        return jsonify({"message": f"Using an empty list is not allowed in the modify"}), 400
                    try:
                        tmpval = process_owl_propertytype(adding)
                        for x in tmpval:
                            property.type.add(x)
                    except (OldapErrorValue, OldapErrorType) as error:
                        return jsonify({"message": str(error)}), 400
                if "del" in attrval:
                    deleting = attrval.get("del", [])
                    if not isinstance(deleting, list):
                        return jsonify({"message": "The given attributes in add and del must be in a list"}), 400
                    if not deleting:
                        return jsonify({"message": f"Using an empty list is not allowed in the modify"}), 400
                    try:
                        tmpval = process_owl_propertytype(deleting)
                        for x in tmpval:
                            property.type.discard(x)
                    except (OldapErrorValue, OldapErrorType) as error:
                        return jsonify({"message": str(error)}), 400
            elif attrval is None:
                property.type = None
            continue
        if attrname == "languageIn":  # is a set of Language items
            if isinstance(attrval, list):
                if not attrval:
                    return jsonify({"message": f"Using an empty list is not allowed in the modify"}), 400
                if None in attrval:
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
                    if None in adding:
                        return jsonify({"message": f"Using a None in a modifylist is not allowed"}), 400
                    for item in adding:
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
                    if None in deleting:
                        return jsonify({"message": f"Using a None in a modifylist is not allowed"}), 400
                    for item in deleting:
                        try:
                            property.languageIn.discard(Language[item.upper()])
                        except AttributeError:
                            return jsonify({"message": f"The entry '{item}' is not in the property and thus could not be deleted"}), 404
            elif attrval is None:
                delattr(property, attrname)
            else:
                return jsonify({"message": f"To modify {attrname} accepted is either a list, dict or None. Received {type(attrname).__name__} instead."}), 400
            continue
        if attrname == 'class':
            try:
                property.oldapSetAttr('toClass', attrval)
            except ValueError as error:
                return jsonify({'message': str(error)}), 400
            continue

        if attrname == "inSet":  # a set of items of the required datatype
            datatype = property.datatype
            if isinstance(attrval, list):
                if not attrval:
                    return jsonify({"message": f"Using an empty list is not allowed in the modify"}), 400
                if None in attrval:
                    return jsonify({"message": f"Using a None in a modifylist is not allowed"}), 400
                try:
                    tmpval = [convert2datatype(x, datatype, validate=True) for x in attrval]
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
                    if None in adding:
                        return jsonify({"message": f"Using a None in a modifylist is not allowed"}), 400
                    for item in adding:
                        try:
                            if property.inSet is None:
                                property.inSet = XsdSet(convert2datatype(item, datatype, validate=True))
                            else:
                                property.inSet.add(convert2datatype(item, datatype, validate=True))
                        except (OldapErrorValue, OldapErrorType) as error:
                            return jsonify({"message": str(error)}), 400
                if "del" in attrval:
                    deleting = attrval.get("del", [])
                    if not isinstance(deleting, list):
                        return jsonify({"message": "The given attributes in add and del must be in a list"}), 400
                    if not deleting:
                        return jsonify({"message": f"Using an empty list is not allowed in the modify"}), 400
                    if None in deleting:
                        return jsonify({"message": f"Using a None in a modifylist is not allowed"}), 400
                    for item in deleting:
                        try:
                            property.inSet.discard(convert2datatype(item, datatype, validate=True))
                        except OldapErrorValue as error:
                            return jsonify({"message": str(error)}), 400
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
    known_json_fields = {"iri", "subPropertyOf", "type", "class", "datatype", "name", "description", "languageIn",
                         "uniqueLang", "inSet", "minLength", "maxLength", "pattern", "minExclusive", "minInclusive",
                         "maxExclusive", "maxInclusive", "lessThan", "lessThanOrEquals",
                         "inverseOf", "equivalentProperty"}
    out = request.headers['Authorization']
    b, token = out.split()

    try:
        con = Connection(token=token,
                         context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    try:
        dm = DataModel.read(con, project, ignore_cache=True)
    except OldapErrorValue as error:
        return jsonify({"message": str(error)}), 400
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404

    if request.is_json:
        data = request.get_json()
        unknown_json_field = set(data.keys()) - known_json_fields
        if unknown_json_field:
            return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to modify a standalone property. Usable are {known_json_fields}. Aborted operation"}), 400
        if not set(data.keys()):
            return jsonify({"message": f"At least one field must be given to modify the standalone property. Usable for the modify-viewfunction are {known_json_fields}"}), 400

        jsonmsg, statuscode = property_modifier(data, dm[Xsd_QName(property)])
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
    known_json_fields = {"maxCount", "minCount", "order", "group", "property"}
    out = request.headers['Authorization']
    b, token = out.split()

    try:
        con = Connection(token=token,
                         context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    try:
        dm = DataModel.read(con, project, ignore_cache=True)
    except OldapErrorValue as error:
        return jsonify({'message': str(error)}), 403
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404

    if request.is_json:
        data = request.get_json()
    else:
        return jsonify({"message": f"JSON expected. Instead received {request.content_type}"}), 400
    unknown_json_field = set(data.keys()) - known_json_fields
    if unknown_json_field:
        return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to modify an attribute of a property in a resource. Usable are {known_json_fields}. aborted operation"}), 400
    if not set(data.keys()):
        return jsonify({"message": f"At least one field must be given to modify an attribute of a property in a resource. Usable for the modify-viewfunction are {known_json_fields}"}), 400

    if "minCount" in data:
        dm[Xsd_QName(resiri)][Xsd_QName(propiri)].minCount = data["minCount"]
    if "maxCount" in data:
        dm[Xsd_QName(resiri)][Xsd_QName(propiri)].maxCount = data["maxCount"]
    if "order" in data:
        dm[Xsd_QName(resiri)][Xsd_QName(propiri)].order = data["order"]
    if "group" in data:
        dm[Xsd_QName(resiri)][Xsd_QName(propiri)].group = Xsd_QName(data["group"])

    property_data = data.get("property", None)
    if property_data or property_data == {}:
        jsonmsg, statuscode = property_modifier(property_data, dm[Xsd_QName(resiri)][Xsd_QName(propiri)].prop)
        if statuscode != 200:
            return jsonmsg, statuscode

    try:
        dm.update()
    except OldapErrorNoPermission as error:
        return jsonify({'message': str(error)}), 403
    except OldapError as error:
        return jsonify({'message': str(error)}), 500  # Should not be reachable
    return jsonify({'message': 'Data model successfully modified'}), 200














