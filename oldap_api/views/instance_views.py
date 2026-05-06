from pprint import pprint
from typing import Any
from urllib.parse import unquote
from flask import request, jsonify, Blueprint, current_app
from oldaplib.src.connection import Connection
from oldaplib.src.datamodel import DataModel
from oldaplib.src.enums.datapermissions import DataPermission
from oldaplib.src.enums.xsd_datatypes import XsdDatatypes
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorValue, OldapErrorKey, OldapErrorNoPermission, \
    OldapErrorAlreadyExists, OldapErrorNotFound, OldapErrorInUse
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.objectfactory import CompOp, FTSearchFilter, HLSearchFilter, LogicOp, ResourceInstance, \
    ResourceInstanceFactory, SearchFilter, SortBy, SortDir, SortKind, convert2datatype
from oldaplib.src.xsd.xsd import Xsd
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.listnode import HListNodeRef
from oldaplib.src.xsd.xsd_date import Xsd_date
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.xsd.xsd_decimal import Xsd_decimal
from oldaplib.src.xsd.xsd_integer import Xsd_integer
from oldaplib.src.xsd.floatingpoint import FloatingPoint
from oldaplib.src.xsd.xsd_boolean import Xsd_boolean
from oldaplib.src.xsd.dating import Dating

from oldaplib.src.helpers.context import Context
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.xsd_string import Xsd_string

instance_bp = Blueprint('instance', __name__, url_prefix='/data')


def get_authorization_token() -> tuple[str | None, tuple[Any, int] | None]:
    out = request.headers.get('Authorization')
    if out is None:
        return None, (jsonify({"message": "No authorization token provided"}), 401)
    parts = out.split()
    if len(parts) != 2:
        return None, (jsonify({"message": "Invalid authorization header"}), 401)
    b, token = parts
    if b.lower() != "bearer" or not token:
        return None, (jsonify({"message": "Invalid authorization header"}), 401)
    return token, None


def to_json_compatible_value(val):
    if isinstance(val, dict):
        return {str(k): to_json_compatible_value(v) for k, v in val.items()}
    elif isinstance(val, list):
        return [to_json_compatible_value(v) for v in val]
    elif isinstance(val, bool):
        return val
    elif isinstance(val, (int, float)):
        return val
    elif isinstance(val, Xsd_integer):
        return int(val) if val is not None else None
    elif isinstance(val, FloatingPoint):
        return float(val) if val is not None else None
    elif isinstance(val, Xsd_boolean):
        return bool(val) if val is not None else None
    else:
        return str(val) if val is not None else None


def parse_bool_query_param(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).lower() in {"1", "true", "t", "yes", "y"}


def parse_logic_op(value: str) -> LogicOp:
    logic_map = {
        "AND": LogicOp.AND,
        "&&": LogicOp.AND,
        "OR": LogicOp.OR,
        "||": LogicOp.OR,
        "(": LogicOp.LEFT_,
        "LEFT": LogicOp.LEFT_,
        "LEFT_": LogicOp.LEFT_,
        ")": LogicOp._RIGHT,
        "RIGHT": LogicOp._RIGHT,
        "_RIGHT": LogicOp._RIGHT,
    }
    try:
        return logic_map[str(value).upper()]
    except KeyError as err:
        raise OldapErrorValue(f'Invalid logic operator "{value}".') from err


def parse_comp_op(value: str) -> CompOp:
    for op in CompOp:
        if str(value).upper() == op.name or str(value).lower() == op.value:
            return op
    raise OldapErrorValue(f'Invalid comparison operator "{value}".')


def parse_search_value(value: Any, value_type: str | None = None, lang: str | None = None):
    if isinstance(value, dict) and (value_type is None or value_type.lower() == "dating"):
        return Dating(dateStart=value.get("dateStart"),
                      dateEnd=value.get("dateEnd", None),
                      verbatimDate=value.get("verbatimDate", None))
    if value_type is None:
        value_type = "string"
    match value_type.lower():
        case "string" | "langstring":
            return Xsd_string(value, lang=lang)
        case "int" | "integer":
            return Xsd_integer(value, validate=True)
        case "decimal":
            return Xsd_decimal(value, validate=True)
        case "float" | "double":
            return FloatingPoint(value)
        case "bool" | "boolean":
            return Xsd_boolean(value, validate=True)
        case "iri":
            return Iri(value, validate=True)
        case "qname":
            return Xsd_QName(value, validate=True)
        case "date":
            return Xsd_date(value, validate=True)
        case "datetime":
            return Xsd_dateTime(value, validate=True)
        case "dating":
            return Dating(value)
        case _:
            raise OldapErrorValue(f'Invalid search value type "{value_type}".')


def parse_search_filter_items(items: list[Any]) -> list[SearchFilter | LogicOp]:
    result: list[SearchFilter | LogicOp] = []
    for item in items:
        if isinstance(item, str):
            result.append(parse_logic_op(item))
            continue
        if not isinstance(item, dict):
            raise OldapErrorValue("Filter entries must be objects or logic operator strings.")
        if "logic" in item:
            result.append(parse_logic_op(item["logic"]))
            continue
        prop = item.get("property", item.get("prop", None))
        op = item.get("op", None)
        if not prop or not op:
            raise OldapErrorValue('Filter entries require "property" and "op".')
        result.append(SearchFilter(prop=Xsd_QName(prop, validate=True),
                                   op=parse_comp_op(op),
                                   value=parse_search_value(item.get("value", None),
                                                            item.get("type", None),
                                                            item.get("lang", None))))
    return result


def parse_ftfilter_items(items: list[Any]) -> list[FTSearchFilter | str]:
    result: list[FTSearchFilter | str] = []
    for item in items:
        if isinstance(item, str):
            logic = str(item).upper()
            if logic not in {"AND", "OR"}:
                raise OldapErrorValue(f'Invalid fulltext logic operator "{item}".')
            result.append(logic)
            continue
        if not isinstance(item, dict):
            raise OldapErrorValue("Fulltext filter entries must be objects or AND/OR strings.")
        prop = item.get("property", item.get("prop", None))
        query = item.get("query", item.get("q", None))
        if not prop or not query:
            raise OldapErrorValue('Fulltext filter entries require "property" and "query".')
        result.append(FTSearchFilter(prop=Xsd_QName(prop, validate=True), query=str(query)))
    return result


def parse_hlfilter_items(items: list[Any]) -> list[HLSearchFilter | LogicOp]:
    result: list[HLSearchFilter | LogicOp] = []
    for item in items:
        if isinstance(item, str):
            result.append(parse_logic_op(item))
            continue
        if not isinstance(item, dict):
            raise OldapErrorValue("Hierarchical list filter entries must be objects or logic operator strings.")
        if "logic" in item:
            result.append(parse_logic_op(item["logic"]))
            continue
        prop = item.get("property", item.get("prop", None))
        node = item.get("node", None)
        if not prop or not node:
            raise OldapErrorValue('Hierarchical list filter entries require "property" and "node".')
        if isinstance(node, dict):
            list_id = node.get("listId", None)
            node_id = node.get("nodeId", None)
            if not list_id or not node_id:
                raise OldapErrorValue('Structured hierarchical list node references require "listId" and "nodeId".')
            node_ref = HListNodeRef(listId=list_id, nodeId=node_id, validate=True)
        else:
            node_ref = HListNodeRef.from_value(node, validate=True)
        result.append(HLSearchFilter(prop=Xsd_QName(prop, validate=True),
                                     node=node_ref))
    return result


def parse_text_search_sort_by(sort_by_values: list[str | dict[str, Any]]) -> list[SortBy]:
    field_map = {
        "PROPVAL": Xsd_QName("oldap:propval"),
        "CREATED": Xsd_QName("oldap:creationDate"),
        "LASTMOD": Xsd_QName("oldap:lastModificationDate"),
    }
    sort_by_param: list[SortBy] = []
    for val in sort_by_values:
        kind = SortKind.AUTO
        if isinstance(val, dict):
            field = val.get("property", val.get("prop", None))
            if not field:
                raise OldapErrorValue('Sort entries require "property".')
            direction = SortDir(str(val.get("direction", val.get("dir", "asc"))).lower())
            kind = SortKind(str(val.get("kind", "auto")).lower())
        else:
            tmp = val.split("|")
            field = tmp[0]
            direction = SortDir.asc
            if len(tmp) > 1:
                if tmp[1].upper() == "DESC":
                    direction = SortDir.desc
                elif tmp[1].upper() != "ASC":
                    raise OldapErrorValue(f'The sort direction "{tmp[1]}" is invalid. Usable are "ASC" and "DESC".')
        if field.upper() in field_map:
            property_ = field_map[field.upper()]
        else:
            property_ = Xsd_QName(field, validate=True)
        sort_by_param.append(SortBy(property_, direction, kind))
    return sort_by_param


def parse_text_search_request(resclass: str | None = None,
                              allow_search_fulltext: bool = False) -> tuple[dict[str, Any] | None, tuple[Any, int] | None]:
    known_fields = {
        "q", "searchString", "ftProperty", "resClass", "resclass", "includeProperties", "filter", "ftfilter", "hlfilter",
        "countOnly", "sortBy", "sortBy[]", "limit", "offset",
    }

    if request.method == "POST":
        if not request.is_json:
            return None, (jsonify({"message": "Invalid request format, JSON required"}), 400)
        data = request.get_json()
        if not isinstance(data, dict):
            return None, (jsonify({"message": "Invalid request format, JSON object required"}), 400)
        unknown_field = set(data.keys()) - known_fields
        if unknown_field:
            return None, (jsonify({"message": f"The Field/s {unknown_field} is/are not used to search for an instance. Usable are {known_fields}. Aborted operation"}), 400)

        raw = {
            "search_string": data.get("q", data.get("searchString", None)),
            "count_only": parse_bool_query_param(data.get("countOnly", None)),
            "ft_property": data.get("ftProperty", None),
            "res_class": resclass or data.get("resClass", data.get("resclass", None)),
            "include_properties": data.get("includeProperties", None),
            "filter": data.get("filter", None),
            "ftfilter": data.get("ftfilter", None),
            "hlfilter": data.get("hlfilter", None),
            "sort_by": data.get("sortBy[]", data.get("sortBy", [])),
            "limit": data.get("limit", None),
            "offset": data.get("offset", None),
        }
    else:
        if request.args:
            unknown_field = set(request.args.keys()) - known_fields
        else:
            unknown_field = set()
        if unknown_field:
            return None, (jsonify({"message": f"The Field/s {unknown_field} is/are not used to search for an instance. Usable are {known_fields}. Aborted operation"}), 400)

        raw = {
            "search_string": request.args.get("q", request.args.get("searchString", None)),
            "count_only": parse_bool_query_param(request.args.get("countOnly", None)),
            "ft_property": request.args.get("ftProperty", None),
            "res_class": resclass or request.args.get("resClass", request.args.get("resclass", None)),
            "include_properties": request.args.getlist("includeProperties[]") or request.args.getlist("includeProperties"),
            "filter": None,
            "ftfilter": None,
            "hlfilter": None,
            "sort_by": request.args.getlist("sortBy[]") or request.args.getlist("sortBy"),
            "limit": request.args.get("limit", None),
            "offset": request.args.get("offset", None),
        }

    if allow_search_fulltext:
        if not raw["search_string"]:
            return None, (jsonify({"message": "No search string provided"}), 400)
        if any([raw["ft_property"], raw["include_properties"], raw["filter"], raw["ftfilter"], raw["hlfilter"]]):
            return None, (jsonify({"message": "Structured search options require /data/search."}), 400)

    try:
        params: dict[str, Any] = {
            'countOnly': raw["count_only"],
            'searchstr': str(raw["search_string"]).lower() if raw["search_string"] else None,
            'use_search_fulltext': False,
        }
        if raw["res_class"]:
            params['resClass'] = Xsd_QName(raw["res_class"], validate=True)
        if raw["include_properties"]:
            include_properties = raw["include_properties"]
            if not isinstance(include_properties, list):
                raise OldapErrorValue('"includeProperties" must be a list.')
            params['includeProperties'] = {Xsd_QName(x, validate=True) for x in include_properties}
        if raw["filter"]:
            if not isinstance(raw["filter"], list):
                raise OldapErrorValue('"filter" must be a list.')
            params['filter'] = parse_search_filter_items(raw["filter"])
        if raw["ftfilter"]:
            if not isinstance(raw["ftfilter"], list):
                raise OldapErrorValue('"ftfilter" must be a list.')
            params['ftfilter'] = parse_ftfilter_items(raw["ftfilter"])
        elif raw["search_string"]:
            if raw["ft_property"]:
                params['ftfilter'] = [FTSearchFilter(prop=Xsd_QName(raw["ft_property"], validate=True),
                                                    query=str(raw["search_string"]))]
            elif allow_search_fulltext and not any([raw["include_properties"], raw["filter"], raw["hlfilter"]]):
                params['use_search_fulltext'] = True
            else:
                raise OldapErrorValue('Fulltext search with "q" requires "ftProperty". Alternatively use "ftfilter".')
        if raw["hlfilter"]:
            if not isinstance(raw["hlfilter"], list):
                raise OldapErrorValue('"hlfilter" must be a list.')
            params['hlfilter'] = parse_hlfilter_items(raw["hlfilter"])
        if raw["sort_by"]:
            sort_by = raw["sort_by"]
            if not isinstance(sort_by, list):
                sort_by = [sort_by]
            params['sortBy'] = parse_text_search_sort_by(sort_by)
        if raw["limit"]:
            params['limit'] = int(raw["limit"])
        if raw["offset"]:
            params['offset'] = int(raw["offset"])
    except (ValueError, OldapErrorValue, OldapError) as error:
        return None, (jsonify({"message": str(error)}), 400)

    if not params['use_search_fulltext'] and not any([
        params.get('resClass'), params.get('filter'), params.get('ftfilter'), params.get('hlfilter')
    ]):
        return None, (jsonify({"message": "Search without filters requires resClass, filter, ftfilter or hlfilter."}), 400)

    return params, None


def text_search_response(project: str, resclass: str | None = None, allow_search_fulltext: bool = False):
    route = f"/data/text/{project}" if allow_search_fulltext else f"/data/search/{project}"
    if resclass:
        route += f"/class/{resclass}"
    current_app.logger.info(f"{route} with {request.method} called")

    project = unquote(project)
    resclass = unquote(resclass) if resclass else None

    token, auth_error = get_authorization_token()
    if auth_error:
        return auth_error

    params, parse_error = parse_text_search_request(resclass=resclass,
                                                    allow_search_fulltext=allow_search_fulltext)
    if parse_error:
        return parse_error

    try:
        con = Connection(token=token,
                         context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    try:
        searchstr = params.pop('searchstr')
        use_search_fulltext = params.pop('use_search_fulltext')
        if use_search_fulltext:
            res = ResourceInstance.search_fulltext(con=con,
                                                   project=Xsd_NCName(project, validate=True),
                                                   searchstr=searchstr,
                                                   **params)
        else:
            res = ResourceInstance.search(con=con,
                                          project=Xsd_NCName(project, validate=True),
                                          **params)
    except OldapError as error:
        return jsonify({"message": f"Search failed: {str(error)}"}), 400

    if params['countOnly']:
        return jsonify({"count": to_json_compatible_value(res)}), 200
    else:
        if isinstance(res, dict):
            tmp = {str(key): {str(x): to_json_compatible_value(y) for x, y in value.items()} for key, value in res.items()}
        else:
            tmp = to_json_compatible_value(res)
        return jsonify(tmp), 200


@instance_bp.route('/mediaobject/id/<imageid>', methods=['GET'])
def media_object_by_id(imageid):
    current_app.logger.info(f"/data/mediaobject/id/{imageid} with GET called")

    out = request.headers.get('Authorization')
    current_app.logger.info("mediaobject_by_id: auth header present=%s", bool(out))
    if out is None:
        return jsonify({"message": "No authorization token provided"}), 401


    # Expected format: "Bearer <token>"
    parts = out.split()
    if len(parts) != 2:
        return jsonify({"message": "Invalid authorization header"}), 401
    b, token = parts
    if b.lower() != "bearer" or not token:
        return jsonify({"message": "Invalid authorization header"}), 401
    try:
        con = Connection(token=token, context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403
    try:
        res = ResourceInstance.get_media_object_by_id(con=con, mediaObjectId=imageid)
    except OldapError as error:
        current_app.logger.error(f"mediaobject_by_id: Retrieving MediaObject with id='{imageid}' failed: {str(error)}")
        return jsonify({"message": f"Retrieving MediaObject failed: {str(error)}"}), 400
    if not res:
        return jsonify({"message": "MediaObject not found"}), 404
    return jsonify({key: [to_json_compatible_value(x) for x in val] if isinstance(val, list) else to_json_compatible_value(val) for key, val in res.items()}), 200

@instance_bp.route('/mediaobject/iri/<path:imageiri>', methods=['GET'])
def media_object_by_iri(imageiri):
    current_app.logger.info(f"/data/mediaobject/iri/{imageiri} with GET called")
    imageiri = unquote(imageiri)
    out = request.headers.get('Authorization')
    if out is None:
        return jsonify({"message": "No authorization token provided"}), 401
    parts = out.split()
    if len(parts) != 2:
        return jsonify({"message": "Invalid authorization header"}), 401
    b, token = parts
    if b.lower() != "bearer" or not token:
        return jsonify({"message": "Invalid authorization header"}), 401
    try:
        con = Connection(token=token, context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403
    try:
        res = ResourceInstance.get_media_object_by_iri(con=con, mediaObjectIri=imageiri)
    except OldapError as error:
        return jsonify({"message": f"Retrieving MediaObject failed: {str(error)}"}), 400
    if not res:
        return jsonify({"message": "MediaObject not found"}), 404
    return jsonify({key: [to_json_compatible_value(x) for x in val] if isinstance(val, list) else to_json_compatible_value(val) for key, val in res.items()}), 200

@instance_bp.route('/text/<path:project>', methods=['GET'])
@instance_bp.route('/text/<path:project>/class/<path:resclass>', methods=['GET'])
def text_instance(project, resclass=None):
    return text_search_response(project=project, resclass=resclass, allow_search_fulltext=True)


@instance_bp.route('/search/<path:project>', methods=['GET', 'POST'])
@instance_bp.route('/search/<path:project>/class/<path:resclass>', methods=['GET', 'POST'])
def search_instance(project, resclass=None):
    return text_search_response(project=project, resclass=resclass)


@instance_bp.route('/textsearch/<path:project>', methods=['GET'])
def textsearch_instance(project):
    return text_search_response(project=project, allow_search_fulltext=True)


@instance_bp.route('/ofclass/<path:project>', methods=['GET'])
def allofclass_instance(project):
    current_app.logger.info(f"/data/ofclass/{project} with GET called")

    project = unquote(project)
    known_json_fields = {"resClass", "includeProperties[]", "countOnly", "sortBy[]", "limit", "offset"}
    out = request.headers['Authorization']
    b, token = out.split()

    if request.args:
        unknown_json_field = set(request.args.keys()) - known_json_fields
    else:
        unknown_json_field = set()
    if unknown_json_field:
        return jsonify({"message": f"The Field/s {unknown_json_field} is/are not used to search for an instance. Usable are {known_json_fields}. Aborded operation"}), 400

    resClass = getattr(request, "args", {}).get("resClass", None)
    includeProperties = getattr(request, "args", {}).getlist("includeProperties[]", None)
    countOnly = getattr(request, "args", {}).get("countOnly", None)
    sortBy = getattr(request, "args", {}).getlist("sortBy[]", None)
    limit = getattr(request, "args", {}).get("limit", None)
    offset = getattr(request, "args", {}).get("offset", None)

    current_app.logger.info(f"/data/allofclass/{project}: resClass: {resClass}, includeProperties: {includeProperties}, countOnly: {countOnly}, sortBy: {sortBy}, limit: {limit}, offset: {offset}")

    if not resClass:
        return jsonify({"message": "No resource class provided"}), 400
    try:
        count_only = parse_bool_query_param(countOnly)
        params: dict[str, Any] = {
            'resClass': Xsd_QName(resClass),
        }
        if includeProperties:
            params['includeProperties'] = {Xsd_QName(x, validate=True) for x in includeProperties} if isinstance(includeProperties, list) else {Xsd_QName(includeProperties, validate=True)}
        if countOnly is not None:
            params['countOnly'] = count_only
        if sortBy:
            sortByParam: list[SortBy] = []
            for val in sortBy:
                tmp = val.split("|")
                property = Xsd_QName(tmp[0], validate=True)
                if len(tmp) > 1 and tmp[1].upper() == "DESC":
                    sortByParam.append(SortBy(property, SortDir.desc))
                elif len(tmp) > 1 and tmp[1].upper() == "ASC":
                    sortByParam.append(SortBy(property, SortDir.asc))
                else:
                    sortByParam.append(SortBy(property))
            params['sortBy'] = sortByParam
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
        res = ResourceInstance.search(con=con,
                                      project=Xsd_NCName(project, validate=True),
                                      **params)
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 400

    if count_only:
        return jsonify({"count": to_json_compatible_value(res)}), 200
    else:
        tmp = to_json_compatible_value(res)

        return jsonify(tmp), 200


@instance_bp.route('/<path:project>/<resource>', methods=['PUT'])
def add_instance(project, resource):
    current_app.logger.info(f"/data/{project}/{resource} with GET called")

    project = unquote(project)
    resource = unquote(resource)
    current_app.logger.info(f"Starting add_instance for project: {project}, resource: {resource}")
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
        current_app.logger.error(f"Failed to create Python instance: {str(error)}")
        return jsonify({"message": str(error)}), 400
    try:
        instance.create()
    except OldapErrorNoPermission as error:
        current_app.logger.error(f"Failed to create instance in triplestore: {str(error)}")
        return jsonify({"message": str(error)}), 403
    except OldapErrorValue as error:
        return jsonify({"message": str(error)}), 409
    except OldapErrorAlreadyExists as error:
        return jsonify({"message": str(error)}), 409
    except OldapError as error:
        return jsonify({"message": str(error)}), 500
    return jsonify({"message": "Instance successfully created", "iri": str(instance.iri)}), 200

@instance_bp.route('/<path:project>/<path:instiri>', methods=['GET'])
def read_instance(project, instiri):
    current_app.logger.info(f"/data/{project}/{instiri} with GET called")

    # Sanitizes XSD values to primitive Python types
    def sanitize_datatype(val: Xsd | None) -> str | int | float | bool | list[str] | None:
        if val is None:
            return None
        if isinstance(val, LangString):
            return [str(langval) for langval in val]
        if isinstance(val, dict):
            return {sanitize_datatype(k): sanitize_datatype(v) for k, v in val.items()}
        elif isinstance(val, list):
            return [sanitize_datatype(v) for v in val]
        elif isinstance(val, (Xsd_integer, FloatingPoint, Xsd_boolean)):
            return val.value
        else:
            return str(val)

    project = unquote(project)
    instiri = unquote(instiri)
    out = request.headers['Authorization']
    b, token = out.split()

    try:
        con = Connection(token=token, context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    try:
        iri = Iri(instiri, validate=True)
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
    resource = None
    for r in res:
        resource = r['resclass']
    if resource is None:
        return jsonify({'message': f'Resource with iri <{iri}> not found.'}), 404

    try:
        factory = ResourceInstanceFactory(con=con, project=project)
        instance_class = factory.createObjectInstance(resource)
        data = ResourceInstance.read_data(con=con,
                                          iri=Iri(instiri, validate=True),
                                          projectShortName=Xsd_NCName(project, validate=True))
    except OldapErrorValue as error:
        return jsonify({"message": str(error)}), 400
    except OldapErrorNotFound as error:
        return jsonify({'message': str(error)}), 404
    except OldapError as error:
        return jsonify({'message': str(error)}), 500
    res = {}
    ordered_datatypes = {
        XsdDatatypes.langString,
        XsdDatatypes.integer,
        XsdDatatypes.nonPositiveInteger,
        XsdDatatypes.negativeInteger,
        XsdDatatypes.long,
        XsdDatatypes.int,
        XsdDatatypes.short,
        XsdDatatypes.byte,
        XsdDatatypes.nonNegativeInteger,
        XsdDatatypes.unsignedLong,
        XsdDatatypes.unsignedInt,
        XsdDatatypes.unsignedShort,
        XsdDatatypes.unsignedByte,
        XsdDatatypes.positiveInteger,
        XsdDatatypes.decimal,
        XsdDatatypes.float,
        XsdDatatypes.double,
    }
    for x, y in data.items():
        attr = Xsd_QName(str(x), validate=False)
        datatype = instance_class.properties.get(attr).datatype if instance_class.properties.get(attr) else None
        if isinstance(y, list):
            values = []
            for yy in y:
                if datatype is not None and not isinstance(yy, LangString):
                    yy = convert2datatype(yy, datatype)
                sanitized = sanitize_datatype(yy)
                if isinstance(yy, LangString):
                    values.extend(sanitized)
                else:
                    values.append(sanitized)
            if datatype in ordered_datatypes:
                values.sort()
            res[str(x)] = values
        else:
            res[str(x)] = sanitize_datatype(y)
    return jsonify(res), 200

@instance_bp.route('/<path:project>/<path:instiri>', methods=['POST'])
def update_instance(project, instiri):
    current_app.logger.info(f"/data/{project}/{instiri} with POST called")

    project = unquote(project)
    instiri = unquote(instiri)
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
        iri = Iri(instiri, validate=True)
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
                del instance[attr]
            elif isinstance(attrval, list):
                instance[attr] = attrval
            elif isinstance(attrval, dict):
                adding_langlist = []
                if "add" in attrval:
                    if (isinstance(attrval.get("add", []), list)):
                        adding = attrval.get("add", [])  # adding is now a list even if attrval["add"] not existing
                    else:
                        adding = [attrval['add']]
                    if instance.properties[attr].datatype == XsdDatatypes.langString:
                        #
                        # LangStrings are special – the can replace. We need a list of all languages added. Some
                        # of these may just replace an "old" value!
                        #
                        adding_langlist = [Xsd_string(x).lang.shortlang for x in adding]
                    if instance.get(attr) is None:
                        instance[attr] = adding
                    else:
                        for x in adding:
                            instance[attr].add(x)
                if "del" in attrval:
                    if (isinstance(attrval.get("del", []), list)):
                        deleting = attrval.get("del", [])
                    else:
                        deleting = [attrval['del']]
                    if instance.properties[attr].datatype == XsdDatatypes.langString:
                        #
                        # In Langstrings, adding a new lang that already exists results in a replacement.
                        # Therefore, we remove only languages that are not being replaced. The TypeScript
                        # langstring.ts cannot distinguish between adding and replacing.
                        #
                        deleting = list(set(deleting) - set(adding_langlist))
                    for x in deleting:
                        instance[attr].discard(x)
            else:
                # TODO: This else should never occur....
                if isinstance(instance[attr], LangString):
                    instance[attr] = attrval  # replace the complete LangString
                else:
                    instance[attr].replace([attrval])
        instance.update()
        return jsonify({"message": "Instance successfully updated"}), 200
    except OldapError as error:
        current_app.logger.exception("update_instance failed")
        return jsonify({"message": str(error)}), 500

@instance_bp.route('/<path:project>/<path:instiri>', methods=['DELETE'])
def delete_instance(project, instiri):
    current_app.logger.info(f"/data/{project}/{instiri} with DELETE called")

    project = unquote(project)
    instiri = unquote(instiri)
    out = request.headers['Authorization']
    b, token = out.split()

    try:
        con = Connection(token=token, context_name="DEFAULT")
    except OldapError as error:
        return jsonify({"message": f"Connection failed: {str(error)}"}), 403

    try:
        iri = Iri(instiri, validate=True)
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
