"""Exercise the legacy bulk-list contract through the real Jena connection."""
from oldaplib.src.objectfactory import ResourceInstance
from oldaplib.src.xsd.xsd_qname import Xsd_QName


def check_bulk_reads(call, check, create_connection):
    """Verify graph-local grants, counts, projection and transaction visibility."""
    con = create_connection(userId='writer', credentials='owned-writer-password')
    admin = create_connection(userId='actor', credentials='owned-fixture-password')
    body = Xsd_QName('demo:body')

    def records(**options):
        return ResourceInstance.all_resources(con, 'demo', 'demo:Record', **options)

    for name, permission in [('bulkvisible', 'DATA_VIEW'), ('bulkhidden', 'DATA_RESTRICTED')]:
        call('PUT', '/data/demo/demo:Record', {'iri': name, 'demo:body': name,
             'oldap:attachedToRole': {'demo:Writer': permission}})
    rows = records(includeProperties=[body, Xsd_QName('demo:absent')])
    check('Bulk list preserves list-valued IRIs, projected values and missing properties',
          len(rows) == 1 and str(rows[0]['iri'][0]) == 'demo:bulkvisible'
          and [str(value) for value in rows[0][body]] == ['bulkvisible']
          and rows[0][Xsd_QName('demo:absent')] == [])
    check('Bulk count applies the same DATA_VIEW threshold', int(records(countOnly=True)) == 1)
    check('Bulk pagination retains the existing row limit and offset',
          len(records(limit=1)) == 1 and records(limit=1, offset=1) == [])

    # Leave the reifier in place: only the asserted membership is removed.
    # The foreign graph must not supply a missing link in demo:data.
    admin.update_query('''PREFIX demo: <https://example.org/demo/>
        PREFIX oldap: <http://oldap.org/base#>
        DELETE DATA { GRAPH demo:data { demo:bulkvisible oldap:attachedToRole demo:Writer } };
        INSERT DATA { GRAPH demo:foreign { demo:bulkvisible oldap:attachedToRole demo:Writer } }''')
    check('Bulk listing rejects orphaned grants and foreign-graph memberships',
          records() == [] and int(records(countOnly=True)) == 0)
    admin.update_query('''PREFIX demo: <https://example.org/demo/>
        PREFIX oldap: <http://oldap.org/base#>
        INSERT DATA { GRAPH demo:data { demo:bulkvisible oldap:attachedToRole demo:Writer } }''')
    con.transaction_start()
    try:
        con.transaction_update('''PREFIX demo: <https://example.org/demo/>
            PREFIX oldap: <http://oldap.org/base#>
            DELETE DATA { GRAPH demo:data { demo:bulkvisible oldap:attachedToRole demo:Writer } }''')
        check('Bulk reads see changes inside their active transaction', records() == [])
    finally:
        con.transaction_abort()
    check('Bulk reads recover the committed membership after abort', len(records()) == 1)
    # Fixture cleanup does not depend on granting the hidden resource API-read rights.
    admin.update_query('''PREFIX demo: <https://example.org/demo/>
        DELETE WHERE { GRAPH demo:data { demo:bulkvisible ?p ?o } };
        DELETE WHERE { GRAPH demo:data { demo:bulkhidden ?p ?o } };
        DELETE WHERE { GRAPH demo:foreign { demo:bulkvisible ?p ?o } }''')
