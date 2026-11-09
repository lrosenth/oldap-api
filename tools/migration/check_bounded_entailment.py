"""Adversarial scoped-entailment checks on the rehearsal's OWNED dataset only."""
from rdflib import URIRef
from oldaplib.src.enums.sparql_result_format import SparqlResultFormat
from oldaplib.src.helpers.context import Context
from oldaplib.src.objectfactory import _build_resource_read_query, _build_resource_summaries_query
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName


def check_entailment(con):
    """Exercise real native queries, live registrations and unchanged ACL joins."""
    context = Context(name=con.context_name)
    context['entail'] = 'https://example.org/entailment/'
    prefix = context.sparql_context
    con.update_query(prefix + f'''INSERT DATA {{
      GRAPH oldap:admin {{ {con.userIri.toRdf} oldap:hasRole entail:Reader . }}
      GRAPH entail:shacl {{ entail:Vocabulary a oldap:ExternalOntology ; oldap:prefix "entail"^^xsd:NCName . }}
      GRAPH entail:onto {{
        entail:Type rdfs:subClassOf entail:Parent .
        entail:forward owl:inverseOf entail:back .
        entail:back2 owl:inverseOf entail:forward2 .
        oldap:attachedToRole owl:inverseOf entail:fakeRole .
        rdf:type owl:inverseOf entail:fakeType .
        oldap:createdBy owl:inverseOf entail:fakeCreator .
      }}
      GRAPH <urn:oldap:vocab:entail> {{
        entail:Equivalent owl:equivalentClass entail:Parent .
        entail:Equivalent rdfs:subClassOf entail:Ancestor .
        entail:Parent owl:equivalentClass entail:Equivalent .
        entail:Ancestor rdfs:subClassOf entail:Parent .
      }}
      GRAPH <urn:oldap:vocab:unregistered> {{ entail:Type rdfs:subClassOf entail:Unregistered . }}
      GRAPH entail:foreign {{ entail:Type rdfs:subClassOf entail:Foreign .
        entail:outsider entail:forward entail:item . }}
      GRAPH entail:data {{
        entail:item a entail:Type ; entail:back entail:linked ; oldap:attachedToRole entail:Reader .
        entail:grant rdf:reifies <<( entail:item oldap:attachedToRole entail:Reader )>> ; oldap:hasDataPermission oldap:DATA_VIEW .
        entail:linked entail:forward entail:item ; entail:forward2 entail:item .
        entail:blocked a entail:Type .
        entail:Reader entail:fakeRole entail:blocked ; entail:fakeRole entail:item .
        entail:FakeClass entail:fakeType entail:item .
        entail:actor entail:fakeCreator entail:item .
      }}
    }}''')
    checks = []
    ns = 'https://example.org/entailment/'
    item, rdf_type = URIRef(ns + 'item'), URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type')

    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append(name)

    def read(name='item'):
        query = _build_resource_read_query(con, Xsd_NCName('entail'), Iri('entail:' + name), con.userIri,
                                          include_creator=False, rdf12=True)
        return con.query(query, format=SparqlResultFormat.JSONLD)

    graph = read()
    check('Both inverse axiom directions work, with no duplicate asserted/inverse values',
          list(graph.objects(item, URIRef(ns + 'back'))) == [URIRef(ns + 'linked')]
          and list(graph.objects(item, URIRef(ns + 'back2'))) == [URIRef(ns + 'linked')])
    types = set(graph.objects(item, rdf_type))
    check('Equivalent classes, superclass chains and cycles across registered graphs terminate',
          types == {URIRef(ns + name) for name in ('Type', 'Parent', 'Equivalent', 'Ancestor')})
    check('Unregistered vocabularies and foreign data/schema graphs are excluded',
          URIRef(ns + 'Foreign') not in types and URIRef(ns + 'Unregistered') not in types
          and URIRef(ns + 'outsider') not in set(graph.objects(item, URIRef(ns + 'back'))))
    check('Inverse ACL/type axioms do not manufacture grants or asserted types',
          len(read('blocked')) == 0 and URIRef(ns + 'FakeClass') not in types
          and not list(graph.objects(item, URIRef('http://oldap.org/base#createdBy'))))
    batch_query = _build_resource_summaries_query(con, Xsd_NCName('entail'), [Iri('entail:item'), Iri('entail:blocked')],
                                               {Xsd_QName('entail:back2')}, rdf12=True)
    batch = con.query(batch_query, format=SparqlResultFormat.JSONLD)
    check('Batch summaries share inverse/class semantics and retain denied-resource exclusion',
          (item, URIRef(ns + 'back2'), URIRef(ns + 'linked')) in batch
          and set(batch.objects(item, rdf_type)) == types
          and not list(batch.triples((URIRef(ns + 'blocked'), None, None))))
    con.transaction_start()
    try:
        con.transaction_update(prefix + 'DELETE WHERE { GRAPH entail:shacl { ?s ?p ?o } }')
        query = _build_resource_read_query(con, Xsd_NCName('entail'), Iri('entail:item'), con.userIri,
                                          include_creator=False, rdf12=True)
        graph = con.transaction_query(query, result_format=SparqlResultFormat.JSONLD)
        check('Removing a vocabulary registration takes effect inside the caller transaction',
              URIRef(ns + 'Equivalent') not in set(graph.objects(item, rdf_type)))
    finally:
        con.transaction_abort()
    check('Rollback restores external schema selection without stale cache',
          URIRef(ns + 'Equivalent') in set(read().objects(item, rdf_type)))
    return checks
