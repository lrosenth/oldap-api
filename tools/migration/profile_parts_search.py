"""Diagnostic-only part-search controls on the owned real-data target.

Scoped diagnostic patches compare query shapes against the current runtime while
retaining the same endpoint, identity, permissions and expected result bodies.
Object-cache I/O remains disabled by the enclosing rehearsal. Timed query calls
may nest via authentication callbacks, so their durations must not be summed.
"""
import hashlib
import json
import statistics
import time
from unittest.mock import patch
from contextlib import nullcontext

from oldaplib.src.jena_connection import JenaConnection
from oldaplib.src import objectfactory
from oldaplib.src.xsd.iri import Iri


def profile_parts_search(call, check, output):
    """Measure baseline, direct-predicate and early-object-binding controls."""
    comparison = json.loads((output/'real-data-comparison.json').read_text())
    parent = next(row['parent'] for row in comparison['api_comparisons'] if row['expected'])
    original_pattern = objectfactory.property_pattern
    original_query = JenaConnection.query
    report = {'object_cache':'disabled','same_parent':True,'cases':{},
              'note':'Query durations include transport/identity and may overlap; do not sum.'}
    patterns = {'dcterms:isPartOf', '<http://purl.org/dc/terms/isPartOf>'}
    term = Iri(parent).toRdf

    def direct(graph, subject, predicate, value, **kwargs):
        if predicate in patterns:
            return f'GRAPH {graph}:data {{ {subject} {predicate} {value} }}'
        return original_pattern(graph, subject, predicate, value, **kwargs)

    def bound(graph, subject, predicate, value, **kwargs):
        if predicate in patterns and value.startswith("?"):
            # Retain all existing hierarchy/inverse rules and the OPTIONAL
            # contract, but push this one EQ-IRI constant into the match.
            return '{ ' + original_pattern(graph, subject, predicate, term, **kwargs) + f' }} BIND({term} AS {value})'
        return original_pattern(graph, subject, predicate, value, **kwargs)

    for endpoint, body in [
        ('rehearsal', {'includeProperties':['dcterms:isPartOf'],'limit':1000}),
        ('frontend', {'includeProperties':['schema:name'],'sortBy':['schema:name|asc'],'limit':100,'offset':0}),
    ]:
        path='/data/search/fasnacht' + ('/class/fasnacht:CarnivalThing' if endpoint=='frontend' else '')
        body={**body,'filter':[{'property':'dcterms:isPartOf','op':'==','value':parent,'type':'iri'}]}
        expected=None
        for variant, replacement in [('current',None),('direct_control',direct),('bound_object',bound)]:
            samples=[]; traces=[]
            for repeat in range(3):
                trace=[]
                def timed_query(self, query, *args, **kwargs):
                    started=time.perf_counter()
                    try:
                        return original_query(self,query,*args,**kwargs)
                    finally:
                        elapsed=(time.perf_counter()-started)*1000
                        digest=hashlib.sha256(query.encode()).hexdigest()[:12]
                        (output/f'profile-{endpoint}-{variant}-{digest}.rq').write_text(query)
                        trace.append({'ms':round(elapsed,3),'query_hash':digest,'chars':len(query),
                                      'resource_search':'?res' in query and 'SELECT' in query})
                context = patch.object(objectfactory,'property_pattern',replacement) if replacement else nullcontext()
                with context, patch.object(JenaConnection,'query',timed_query):
                    started=time.perf_counter(); rows=call('POST',path,body).json()
                    samples.append(round((time.perf_counter()-started)*1000,3))
                canonical=json.dumps(sorted(rows,key=lambda row:row['iri']),sort_keys=True)
                if expected is None:expected=canonical
                if canonical!=expected:raise AssertionError('Profile variant changes response: '+endpoint+'/'+variant)
                traces.append(trace)
            report['cases'][endpoint+'/'+variant]={'ms':samples,'median_ms':statistics.median(samples),
                'result_count':len(rows),'query_traces':traces,'same_response':True}
            print('PROFILE',endpoint,variant,report['cases'][endpoint+'/'+variant]['median_ms'],flush=True)
    (output/'parts-profile.json').write_text(json.dumps(report,indent=2)+'\n')
    check('Part-search diagnostic variants preserve exact API response bodies',True)
