"""Real-export fulltext acceptance through YAML, normal API and owned Redis."""
import json
from pathlib import Path
import re
import subprocess
import time

import yaml


def check_fasnacht_fulltext(call, con, base, output, public, audit):
    """Activate the project field map and test real text plus an evolving model.

    All model/data/index mutations belong to the disposable real-export target.
    Source export and source YAML remain unchanged. The returned report contains
    search terms/identities/counts, never credentials or complete PDF text.
    """
    workspace = Path(__file__).resolve().parents[3]
    tools = workspace / 'oldap-tools'
    source = tools / 'examples/ontology/fasnacht-jena.yaml'
    report = {'checks': [], 'queries': []}

    def check(label, condition):
        if not condition:
            raise AssertionError(label)
        report['checks'].append(label)
        print('PASS FULLTEXT', label, flush=True)

    def load(path, dry=False):
        command = [str(tools / '.venv/bin/oldap-tools'), '--api', base, '--user', 'actor',
                   '--password', 'owned-fixture-password', 'ontology', 'load', '-i', str(path),
                   '--fulltext', 'apply', '--no-backup']
        if dry:
            command.append('--dry-run')
        started = time.monotonic()
        result = subprocess.run(command, capture_output=True, text=True, timeout=180)
        with (output / 'fulltext-tools.log').open('a') as log:
            log.write(result.stdout + result.stderr)
        if result.returncode:
            raise AssertionError('Fulltext YAML import failed; inspect fulltext-tools.log')
        return result.stdout, round((time.monotonic()-started)*1000)

    def search(field, term, headers, **options):
        started = time.monotonic()
        result = call('POST', '/data/search/fasnacht', {
            'ftfilter': [{'field': field, 'query': term}],
            'includeProperties': ['schema:name'], 'limit': 2000, **options}, headers=headers).json()
        report['queries'].append({'field': field, 'term': term,
            'identity': 'public' if headers is public else 'audit',
            'milliseconds': round((time.monotonic()-started)*1000),
            'count': result.get('count') if isinstance(result, dict) else len(result)})
        return result

    def identities(rows):
        return {row['iri'] for row in rows}

    check('Owned project starts without a managed fulltext index',
          call('GET', '/admin/fulltext/fasnacht').json()['status'] == 'absent')
    load(source, dry=True)
    _, elapsed = load(source)
    report['initial_import_ms'] = elapsed
    state = call('GET', '/admin/fulltext/fasnacht').json()
    check('Nine YAML fields activate on the existing real project', state['status'] == 'active'
          and len(state['configuration']['fields']) == 9)
    check('Unchanged YAML replay plans no writes', 'Planned 0' in load(source, dry=True)[0])
    title = search('archiveObjectTitle', 'Laterne', public)
    check('Public title search finds real lantern records', bool(title))
    count = search('archiveObjectTitle', 'Laterne', public, countOnly=True)
    check('Fulltext result and count agree', count['count'] == len(title))
    page = search('archiveObjectTitle', 'Laterne', public, limit=2, offset=0, sortBy=['schema:name|asc'])
    check('Sorted fulltext paging returns a subset', len(page) == 2 and identities(page) <= identities(title))
    check('Prefix search includes exact-word hits', identities(title) <= identities(search('archiveObjectTitle', 'Later*', public)))
    check('Quoted phrase search finds real titles', bool(search('archiveObjectTitle', '"BMG Stamm"', public)))
    combined = call('POST', '/data/search/fasnacht', {'ftfilter': [
        {'field': 'archiveObjectTitle', 'query': 'Laterne'}, 'OR',
        {'field': 'archiveMediaObjectTitle', 'query': 'Laterne'}], 'limit': 2000}, headers=public).json()
    check('Aliases sharing a predicate do not duplicate results', len(combined) == len(title) and identities(combined) == identities(title))
    words = search('archiveObjectTitle', 'Laterne Stamm', public)
    check('Multiple words match independently of order', bool(words) and identities(words) == identities(search('archiveObjectTitle', 'Stamm Laterne', public)))
    check('Every word is required', search('archiveObjectTitle', 'Laterne migrationabsentword', public) == [])
    check('Configured relation path finds represented-object titles', bool(search('representedArchiveObjectTitle', 'Laterne', public)))

    from oldaplib.src.helpers.context import Context
    prefix = Context(name=con.context_name).sparql_context
    rows = con.query(prefix + '''SELECT ?res (SUBSTR(STR(?text), 1, 800) AS ?sample) WHERE {
        GRAPH fasnacht:data { ?res fasnacht:searchableText ?text ; oldap:attachedToRole oldap:Unknown . }
    } ORDER BY ?res LIMIT 10''')['results']['bindings']
    check('Real export includes public extracted PDF text', bool(rows))
    sample = rows[0]
    word = re.search(r'[^\W\d_]{8,}', sample['sample']['value']).group()
    check('Public PDF text is indexed from existing data', sample['res']['value'] in identities(search('archiveMediaObjectText', word, public)))
    report['public_pdf_query'] = word
    internal = con.query(prefix + """SELECT ?res (SUBSTR(STR(?text), 1, 800) AS ?sample) WHERE {
        GRAPH fasnacht:data { ?res fasnacht:searchableText ?text .
            FILTER NOT EXISTS { ?res oldap:attachedToRole oldap:Unknown } }
    } ORDER BY ?res LIMIT 1""")['results']['bindings']
    if internal:
        private = internal[0]['res']['value']
        word = re.search(r'[^\W\d_]{8,}', internal[0]['sample']['value']).group()
        report['private_text_origin'] = 'existing exported extracted text'
    else:
        # Some exports contain OCR only for public documents. Exercise a real
        # internal PDF with unmistakably synthetic text in the disposable copy.
        private = 'urn:uuid:813a29d0-cbc3-41c3-b148-f0ad55dda343'
        word = 'migrationinternaldocument'
        con.update_query(prefix + f'INSERT DATA {{ GRAPH fasnacht:data {{ <{private}> fasnacht:searchableText "{word}" . }} }}')
        report['private_text_origin'] = 'synthetic text on a real internal PDF in owned target'
    report['private_pdf_iri'] = private
    check('Audit reader finds internal PDF extracted text', private in identities(search('archiveMediaObjectText', word, audit)))
    check('Public PDF text search excludes the internal document', private not in identities(search('archiveMediaObjectText', word, public)))
    report['private_pdf_query'] = word

    call('PUT', '/admin/datamodel/fasnacht/fasnacht:SearchProbe', {'label': ['Search probe@en'],
         'superclass': ['oldap:Thing'], 'properties': [
             {'iri': 'fasnacht:futureSearchText', 'datatype': 'xsd:string'}]})
    call('PUT', '/data/fasnacht/fasnacht:SearchProbe', {'iri': 'fulltext-evolution',
         'fasnacht:futureSearchText': ['migrationfuturefield', 'migrationsecondvalue', 'Zu\u0308rich Straße École Laternen'],
         'oldap:attachedToRole': {'oldap:Unknown': 'DATA_VIEW', 'oldap:WriterRecoveryOperator': 'DATA_PERMISSIONS'}})
    call('POST', '/data/search/fasnacht', {'ftfilter': [{'field': 'futureProjectText', 'query': 'migrationfuturefield'}]}, headers=public, status=400)
    config = yaml.safe_load(source.read_text())
    config['ontology']['fulltext']['fields']['futureProjectText'] = ['fasnacht:futureSearchText']
    expanded = output / 'future-fulltext.yaml'
    expanded.write_text(yaml.safe_dump(config, sort_keys=False))
    load(expanded)
    check('New model predicate becomes searchable by YAML configuration alone',
          identities(search('futureProjectText', 'migrationfuturefield', public)) == {'fasnacht:fulltext-evolution'})
    check('Multiple words can match separate values of the same field', bool(search('futureProjectText', 'migrationfuturefield migrationsecondvalue', public)))
    check('Normal API folds accents and sharp s in a newly configured field',
          identities(search('futureProjectText', 'zurich strasse ecole', public)) == {'fasnacht:fulltext-evolution'})
    check('Normal API accepts canonical Unicode and folds wildcard terms',
          identities(search('futureProjectText', 'Zu\u0308r* straß* éco*', public)) == {'fasnacht:fulltext-evolution'})
    check('Normal API keeps singular and plural separate',
          search('futureProjectText', 'Laterne', public) == [] and
          identities(search('futureProjectText', 'Laternen', public)) == {'fasnacht:fulltext-evolution'})
    check('API read preserves original decomposed text after indexing',
          'Zu\u0308rich Straße École Laternen' in call('GET', '/data/fasnacht/fasnacht:fulltext-evolution', headers=public).json()['fasnacht:futureSearchText'])

    edge = 'fasnacht:fulltext-evolution oldap:attachedToRole oldap:Unknown .'
    con.update_query(prefix + 'DELETE DATA { GRAPH fasnacht:data { ' + edge + ' } }')
    try:
        check('Revoked membership excludes indexed text despite orphan annotation',
              search('futureProjectText', 'migrationfuturefield', public) == []
              and search('futureProjectText', 'migrationfuturefield', public, countOnly=True)['count'] == 0)
    finally:
        con.update_query(prefix + 'INSERT DATA { GRAPH fasnacht:data { ' + edge + ' } }')
    check('Restored membership restores search without reindexing', bool(search('futureProjectText', 'migrationfuturefield', public)))
    # Explicit diagnostic: a public root must not be mistaken for permission
    # to expose text of every referenced resource. Remove this owned link after
    # observing the current root-only path policy; do not change source data.
    public_media = 'urn:uuid:3553c881-c53b-444a-ac8d-2995cf4966fe'
    linked = f'<{public_media}> fasnacht:archiveMediaObjectOf fasnacht:browser-private-child .'
    con.update_query(prefix + 'INSERT DATA { GRAPH fasnacht:data { ' + linked + ' } }')
    try:
        hits = identities(search('representedArchiveObjectTitle', 'Prüfobjekt', public))
        check('Private referenced text cannot reveal a public root through search', public_media not in hits)
        check('Audit reader may search the readable referenced title', public_media in identities(search('representedArchiveObjectTitle', 'Prüfobjekt', audit)))
        public_grant = '''fasnacht:browser-private-child oldap:attachedToRole oldap:Unknown .
            <urn:probe:fulltext-source-grant> rdf:reifies <<( fasnacht:browser-private-child oldap:attachedToRole oldap:Unknown )>> ;
                oldap:hasDataPermission oldap:DATA_VIEW .'''
        con.update_query(prefix + 'INSERT DATA { GRAPH fasnacht:data { ' + public_grant + ' } }')
        try:
            check('Granting source visibility enables the linked fulltext hit', public_media in identities(search('representedArchiveObjectTitle', 'Prüfobjekt', public)))
            con.update_query(prefix + 'DELETE DATA { GRAPH fasnacht:data { fasnacht:browser-private-child oldap:attachedToRole oldap:Unknown } }')
            check('Revoked source membership hides linked hits and counts despite orphan grant',
                  search('representedArchiveObjectTitle', 'Prüfobjekt', public) == [] and
                  search('representedArchiveObjectTitle', 'Prüfobjekt', public, countOnly=True)['count'] == 0)
        finally:
            con.update_query(prefix + 'DELETE DATA { GRAPH fasnacht:data { ' + public_grant + ' } }')
    finally:
        con.update_query(prefix + 'DELETE DATA { GRAPH fasnacht:data { ' + linked + ' } }')
    load(source)
    check('Original field map restored for browser testing', len(call('GET', '/admin/fulltext/fasnacht').json()['configuration']['fields']) == 9)
    # Browsers issue several searches concurrently. Configuration reads must
    # coexist with data readers instead of requesting index-maintenance locks.
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    ready = Barrier(4)

    def concurrent_search(_):
        ready.wait(timeout=10)
        return call('POST', '/data/search/fasnacht/class/fasnacht:ArchiveMediaObject', {
            'ftfilter': [{'field': 'archiveMediaObjectTitle', 'query': 'Laterne Stamm'}],
            'includeProperties': ['schema:name'], 'limit': 5000}, headers=public).json()

    with ThreadPoolExecutor(max_workers=4) as pool:
        parallel = list(pool.map(concurrent_search, range(4)))
    check('Concurrent class searches share configuration reads without conflicts',
          bool(parallel[0]) and all(identities(rows) == identities(parallel[0]) for rows in parallel))
    (output / 'fulltext-results.json').write_text(json.dumps(report, indent=2) + '\n')
    print('FULLTEXT_CHECKS_PASSED', len(report['checks']), flush=True)
