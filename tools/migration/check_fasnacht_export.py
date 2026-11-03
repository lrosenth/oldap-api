"""Compare a real converted Fasnacht instance graph before/after part reversal.

Accounts are not restored. The owned audit actor receives the role identities
found in this dataset only in the disposable target, allowing permission-filtered
API comparison without changing a single imported instance or grant.
"""
import json


GRAPH = 'http://fasnacht.digital/ns/data'
PART = 'http://purl.org/dc/terms/isPartOf'
HAS = 'http://purl.org/dc/terms/hasPart'
BASE = 'http://oldap.org/base#'


def check_fasnacht_export(call, check, con, workspace, output):
    """Require exact instance preservation except the agreed relation reversal."""
    def snapshot():
        return con.query(f'SELECT ?s ?p ?o WHERE {{ GRAPH <{GRAPH}> {{ ?s ?p ?o }} }}')['results']['bindings']
    def key(row):
        return json.dumps(row, sort_keys=True)
    before = snapshot()
    expected_pairs = {(r['s']['value'], r['o']['value']) for r in before if r['p']['value'] == PART}
    legacy = [r for r in before if r['p']['value'] == HAS]
    expected_pairs.update((r['o']['value'], r['s']['value']) for r in legacy)
    untouched = {key(r) for r in before if r['p']['value'] not in (PART, HAS)}
    queries = workspace / 'oldaplib/tools/migration/sparql'
    con.transaction_start()
    try:
        issues = con.transaction_query((queries / 'fasnacht-parts-preflight.rq').read_text())['results']['bindings']
        (output / 'parts-preflight.json').write_text(json.dumps(issues, indent=2)+'\n')
        check('Real Fasnacht export passes canonical-part preflight', not issues)
        con.transaction_update((queries / 'fasnacht-parts.ru').read_text())
        con.transaction_commit()
    except Exception:
        if con.in_transaction():
            con.transaction_abort()
        raise
    after = snapshot()
    check('Real export preserves every non-part instance triple',
          {key(r) for r in after if r['p']['value'] not in (PART, HAS)} == untouched)
    actual_pairs = {(r['s']['value'], r['o']['value']) for r in after if r['p']['value'] == PART}
    check('Real export part pairs equal the exact forward/reversed union', actual_pairs == expected_pairs)
    check('Real export no longer contains hasPart instance assertions',
          not any(r['p']['value'] == HAS for r in after))
    con.update_query((queries / 'fasnacht-parts.ru').read_text())
    check('Real export conversion replay leaves all instance triples unchanged',
          {key(r) for r in snapshot()} == {key(r) for r in after})

    roles = sorted({r['o']['value'] for r in after if r['p']['value'] == BASE+'attachedToRole'})
    # Values originate from parsed IRI terms, never raw user-provided query text.
    from oldaplib.src.xsd.iri import Iri
    if roles:
        con.update_query('INSERT DATA { GRAPH <'+BASE+'admin> { <https://example.org/actor> <'+BASE+'hasRole> '+
                         ', '.join(Iri(role).toRdf for role in roles)+' } }')
    readable = {r['s']['value'] for r in con.query('''PREFIX oldap: <http://oldap.org/base#>
      PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
      SELECT DISTINCT ?s WHERE { GRAPH <http://fasnacht.digital/ns/data> {
        ?s a ?type ; oldap:attachedToRole ?role .
        ?grant rdf:reifies <<( ?s oldap:attachedToRole ?role )>> ; oldap:hasDataPermission ?permission .
      } GRAPH oldap:admin {
        <https://example.org/actor> oldap:hasRole ?role .
        ?permission oldap:permissionValue ?value . FILTER(?value >= 2)
      } }''')['results']['bindings']}
    parents = sorted({parent for child, parent in expected_pairs})
    comparisons = []
    for parent in parents:
        rows = call('POST', '/data/search/fasnacht', {'limit': 1000,
            'includeProperties': ['dcterms:isPartOf'], 'filter': [{
                'property': 'dcterms:isPartOf', 'op': '==', 'value': parent, 'type': 'iri'}]}).json()
        found = {row['iri'].replace('fasnacht:', 'http://fasnacht.digital/ns/', 1)
                 if row['iri'].startswith('fasnacht:') else row['iri'] for row in rows}
        wanted = {child for child, p in expected_pairs if p == parent and child in readable}
        comparisons.append({'parent':parent,'expected':sorted(wanted),'actual':sorted(found)})
        check('Real export API reverse lookup matches readable children '+str(len(comparisons)), found == wanted)
    if expected_pairs and readable:
        child = next((child for child, parent in sorted(expected_pairs) if child in readable), None)
        if child is not None:
            from urllib.parse import quote
            detail = call('GET', '/data/fasnacht/' + quote(child, safe='')).json()
            check('Real export single-resource API exposes the canonical parent field',
                  'dcterms:isPartOf' in detail and 'dcterms:hasPart' not in detail)
    check('Real export API comparison covers nonempty readable part relationships',
          bool(comparisons) and any(row['expected'] for row in comparisons))
    (output/'real-data-comparison.json').write_text(json.dumps({
        'before_triples':len(before),'after_triples':len(after),'legacy_hasPart':len(legacy),
        'canonical_pairs':len(actual_pairs),'preserved_other_triples':len(untouched),
        'audit_role_count':len(roles),'readable_resources':len(readable),'api_comparisons':comparisons,
        'account_restore':False,
        'subject_links_preserved':sum(r['p']['value']=='https://schema.org/about' for r in after),
        'archive_assignments_preserved':sum(r['p']['value']=='http://fasnacht.digital/ns/archiveUnit' for r in after)},indent=2)+'\n')
