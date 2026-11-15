"""Project-neutral, bounded archive placement summaries for content selection."""
from rdflib import Literal, URIRef

from oldaplib.src.archive_policy import ArchivePolicy, canonical_iri
from oldaplib.src.enums.datapermissions import DataPermission
from oldaplib.src.helpers.jena_entailment import CLASS_PATH, schema_dataset
from oldaplib.src.helpers.oldaperror import OldapErrorValue
from oldaplib.src.objectfactory import creator_or_max_perm_block
from oldaplib.src.resource_transaction import resource_query
from oldaplib.src.xsd.iri import Iri

MAX_TARGETS = 500


def placement_status(connection, project: str, body: dict) -> dict:
    """Count readable media and missing assignments in one aggregate query.

    Both targets and media require ordinary read grants (no admin bypass).
    Placement existence includes unreadable archive units, so a hidden unit is
    never mistaken for missing placement; neither its identity nor title leaks.
    Policy supplies all project-specific classes and the semantic parent edge.
    Results are advisory; writes must still enforce authoritative invariants.
    """
    if not isinstance(body, dict) or set(body) != {"targets"}:
        raise OldapErrorValue("Exactly one targets array is required.")
    targets = body["targets"]
    if not isinstance(targets, list) or not 1 <= len(targets) <= MAX_TARGETS:
        raise OldapErrorValue(f"Provide 1–{MAX_TARGETS} targets.")
    for target in targets:
        if (not isinstance(target, dict) or set(target) != {"iri", "kind"}
                or not isinstance(target["iri"], str) or not target["iri"].strip()
                or target["kind"] not in ("entry", "media")):
            raise OldapErrorValue("Each target requires an iri and entry/media kind.")
        Iri(target["iri"], validate=True)
    policy = ArchivePolicy.load(connection, project)
    if not policy.enabled or not policy.publication:
        raise OldapErrorValue("Archive content relationships are not configured.")
    query = placement_status_query(policy, targets)
    rows = resource_query(connection, query)["results"]["bindings"]
    return {"items": [{"iri": row["key"]["value"], "mediaCount": int(row["total"]["value"]),
                       "unassignedCount": int(row["unassigned"]["value"])} for row in rows]}


def placement_status_query(policy, targets: list[dict]) -> str:
    """Build an aggregate query with escaped terms and independent ACL aliases."""
    def term(value):
        return URIRef(canonical_iri(policy.context, value)).n3()

    graph = f"{policy.project.projectShortName}:data"
    user = policy.connection.userIri.toRdf
    rdf12 = getattr(policy.connection, "_resource_permissions_rdf12", False) is True
    dataset = (schema_dataset(policy.connection, policy.project.projectShortName)
               + f" FROM NAMED {graph} FROM NAMED oldap:admin") if rdf12 else ""

    def class_match(subject, expected, alias):
        """Match exact types or selected-schema ancestors on non-inferencing Jena."""
        if not rdf12:
            return f"GRAPH {graph} {{ {subject} a {expected} . }}"
        return (f"GRAPH {graph} {{ {subject} a ?{alias} . }} "
                f"FILTER (?{alias} = {expected} || EXISTS {{ ?{alias} {CLASS_PATH} {expected} }})")

    def readable(variable, alias):
        """Use bounded direct ACL joins on Jena; DISTINCT counts absorb multiple grants."""
        minimum = DataPermission.DATA_VIEW.numeric.toRdf
        if rdf12:
            return f"""GRAPH {graph} {{
              {variable} oldap:attachedToRole ?{alias}_role .
              ?{alias}_grant rdf:reifies <<( {variable} oldap:attachedToRole ?{alias}_role )>> ;
                  oldap:hasDataPermission ?{alias}_permission .
            }}
            GRAPH oldap:admin {{
              {user} oldap:hasRole ?{alias}_role .
              ?{alias}_permission oldap:permissionValue ?{alias}_value .
              FILTER (?{alias}_value >= {minimum})
            }}"""
        return creator_or_max_perm_block(graph_data=graph, resource_iri=variable,
            user_iri=user, min_perm=minimum, alias=alias, include_creator=False)

    values = "\n".join(f'({Literal(t["iri"]).n3()} {term(t["iri"])} {Literal(t["kind"]).n3()})'
                       for t in { (t["iri"], t["kind"]): t for t in targets }.values())
    media_classes = " ".join(term(v) for v in policy.media_classes)
    root_classes = " ".join(term(v) for v in policy.publication["rootClassIris"])
    parent = term(policy.publication["mediaToRootPropertyIri"])
    # Deduplicate candidate media before joining placements. A set-based OPTIONAL
    # placement join avoids repeating a correlated existence scan for each medium.
    # Bind branch inputs inside each UNION arm: BIND cannot depend on an outer
    # solution when that arm is evaluated independently by the SPARQL engine.
    entries = " ".join(term(t["iri"]) for t in targets if t["kind"] == "entry")
    media = " ".join(f'({term(t["iri"])} {term(t["iri"])})'
                     for t in targets if t["kind"] == "media")
    return policy.context.sparql_context + f"""
SELECT ?key (COUNT(DISTINCT ?media) AS ?total) (COUNT(DISTINCT ?free) AS ?unassigned)
{dataset}
WHERE {{
  VALUES (?key ?target ?kind) {{ {values} }}
  {readable('?target', 'targetAccess')}
  OPTIONAL {{
    {{ SELECT DISTINCT ?target ?kind ?media WHERE {{
    {{ VALUES ?kind {{ "entry" }} VALUES ?target {{ {entries} }}
       VALUES ?rootClass {{ {root_classes} }}
       {class_match('?target', '?rootClass', 'rootType')}
       GRAPH {graph} {{ ?media {parent} ?target . }}
    }} UNION {{ VALUES ?kind {{ "media" }} VALUES (?target ?media) {{ {media} }} }}
    VALUES ?mediaClass {{ {media_classes} }}
    {class_match("?media", "?mediaClass", "mediaType")}
    {readable('?media', 'mediaAccess')}
    }} }}
    OPTIONAL {{
      GRAPH {graph} {{ ?unit shared:hasMediaObject ?media . }}
      {class_match('?unit', 'shared:ArchiveUnit', 'unitType')}
    }}
    BIND(IF(BOUND(?unit), ?notUnassigned, ?media) AS ?free)
  }}
}} GROUP BY ?key
"""
