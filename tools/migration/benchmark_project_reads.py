"""Small repeatable HTTP read benchmark; clears only the caller-owned cache.

Cold means empty OLDAP object cache, not cold OS/TDB/JVM caches. Record raw
samples: these local serial measurements are not production/load guarantees.
"""
import statistics
import time
import requests
from redis import Redis


def benchmark_reads(base, headers, cache_url, project, iris):
    """Measure individual, batch and class-search reads on one isolated target."""
    cases = {
        'resource': ('GET', f'/data/{project}/{project}:LukasRosenthaler', None),
        'summaries': ('POST', f'/data/summaries/{project}', {'iris': iris,
            'includeProperties': ['schema:name', 'schema:hasPart', f'{project}:hasKnowledgeContribution']}),
        'search': ('GET', f'/data/search/{project}/class/schema:Thing', None),
    }
    # Keep this named sample explicit: another project needs its own representative
    # resource, rather than accidentally benchmarking a fast 404 response.
    if project != 'chama':
        raise ValueError('The benchmark currently defines representative Chama requests only')
    results = {}
    with Redis.from_url(cache_url) as cache, requests.Session() as client:
        client.headers.update(headers)
        for name, (method, path, body) in cases.items():
            values = {'cold_object_cache_ms': [], 'warm_object_cache_ms': []}
            for mode, repeats in [('cold_object_cache_ms', 3), ('warm_object_cache_ms', 7)]:
                for _ in range(repeats):
                    if mode == 'cold_object_cache_ms':
                        cache.flushdb()
                    start = time.perf_counter()
                    response = client.request(method, base + path, json=body, timeout=90)
                    elapsed = (time.perf_counter() - start) * 1000
                    if response.status_code != 200:
                        raise AssertionError(f'Benchmark {name}: HTTP {response.status_code}')
                    values[mode].append(round(elapsed, 3))
            results[name] = dict(values, medians_ms={key: statistics.median(samples) for key, samples in values.items()})
    return results


def add_synthetic_people(connection, project, count=1000):
    """Grow only the owned rehearsal dataset using existing modeled class/role.

    This is a query-size sensitivity check, not a representative production
    workload. It runs after all source/target comparisons and never on GraphDB.
    """
    from oldaplib.src.helpers.context import Context
    if project != 'chama' or not 1 <= count <= 10000:
        raise ValueError('Synthetic scale fixture requires Chama and 1..10000 rows')
    values = ' '.join(map(str, range(count)))
    connection.update_query(Context(name=connection.context_name).sparql_context + f'''
        INSERT {{ GRAPH chama:data {{
            ?copy a chama:Person ; schema:name "Synthetic benchmark person" ; oldap:attachedToRole ?role .
            ?grant rdf:reifies <<( ?copy oldap:attachedToRole ?role )>> ; oldap:hasDataPermission ?permission .
        }} }} WHERE {{
            GRAPH chama:data {{
                chama:LukasRosenthaler oldap:attachedToRole ?role .
                ?existing rdf:reifies <<( chama:LukasRosenthaler oldap:attachedToRole ?role )>> ;
                    oldap:hasDataPermission ?permission .
            }}
            VALUES ?i {{ {values} }}
            BIND(IRI(CONCAT("urn:oldap:benchmark:person:", STR(?i))) AS ?copy)
            BIND(IRI(CONCAT("urn:oldap:benchmark:grant:", STR(?i), ":", ENCODE_FOR_URI(STR(?role)))) AS ?grant)
        }}
    ''')
    result = connection.query('SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE { GRAPH <https://chama.salsah.org/ns/data> '
                              '{ ?s a <https://chama.salsah.org/ns/Person> . FILTER(STRSTARTS(STR(?s), "urn:oldap:benchmark:person:")) } }')
    if int(result['results']['bindings'][0]['n']['value']) != count:
        raise AssertionError('Synthetic population does not match requested scale')


def compare_class_cost(base, headers, project):
    """Pair identical-result class searches with/without the new entailment rules.

    This test-only control uses the same owned API/Jena process and asserted
    Chama Person selection. It restores the previous schema/path behavior for
    each control request. No production option or persistent flag is introduced.
    """
    from contextlib import ExitStack
    from unittest.mock import patch
    from oldaplib.src import objectfactory
    samples = {'bounded_entailment_ms': [], 'previous_rules_control_ms': []}
    expected = None
    with requests.Session() as client:
        client.headers.update(headers)
        for repetition in range(8):
            # Alternate order to reduce warmup/order bias. Discard the first pair.
            modes = list(samples) if repetition % 2 else list(reversed(samples))
            for mode in modes:
                with ExitStack() as stack:
                    if mode == 'previous_rules_control_ms':
                        stack.enter_context(patch.object(objectfactory, 'schema_dataset',
                            lambda con, graph: f'FROM {graph}:onto FROM shared:onto FROM oldap:onto'))
                        stack.enter_context(patch.object(objectfactory, 'class_choices',
                            lambda var, target, graph: f'FILTER({var} = {target} || EXISTS {{ {var} rdfs:subClassOf+ {target} }})'))
                    start = time.perf_counter()
                    response = client.get(base + f'/data/search/{project}/class/{project}:Person', timeout=90)
                    elapsed = (time.perf_counter() - start) * 1000
                    if response.status_code != 200:
                        raise AssertionError('Class-cost comparison failed')
                    actual = response.json()
                    if expected is None:
                        expected = actual
                    elif actual != expected:
                        raise AssertionError('Performance control changed the returned search page')
                    if repetition:
                        samples[mode].append(round(elapsed, 3))
    return dict(samples, medians_ms={name: statistics.median(values) for name, values in samples.items()},
                identical_result_page=True, page_size=len(expected))
