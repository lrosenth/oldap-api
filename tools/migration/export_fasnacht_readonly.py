"""Read-only local GraphDB Fasnacht export using native TriG-star serialization.

No API login, mutation, inference, cache operation or account export is performed.
The explicit graph scope includes the project's data, ontology, shapes and lists.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import requests


def export(output):
    """Write a fresh private export and digest; require the expected namespace."""
    os.umask(0o077)
    output.mkdir(parents=True, exist_ok=False)
    endpoint = 'http://localhost:7200/repositories/oldap'
    query = '''PREFIX oldap: <http://oldap.org/base#>
      PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
      SELECT ?ns WHERE { GRAPH oldap:admin {
        ?p oldap:projectShortName "fasnacht"^^xsd:NCName ; oldap:namespaceIri ?ns
      } }'''
    response = requests.post(endpoint, data={'query':query,'infer':'false'},
                             headers={'Accept':'application/sparql-results+json'},timeout=60)
    response.raise_for_status()
    rows=response.json()['results']['bindings']
    if len(rows)!=1 or rows[0]['ns']['value']!='http://fasnacht.digital/ns/':
        raise ValueError('Unexpected source project namespace')
    graphs=['http://fasnacht.digital/ns/'+part for part in ('data','onto','shacl','lists')]
    response=requests.get(endpoint+'/statements',params=[('context','<'+g+'>') for g in graphs]+[('infer','false')],
                          headers={'Accept':'application/x-trigstar'},timeout=60)
    response.raise_for_status()
    (output/'source.trig').write_bytes(response.content)
    report={'sha256':hashlib.sha256(response.content).hexdigest(),'bytes':len(response.content),
            'graphs':graphs,'infer':False,'format':'application/x-trigstar','accounts_exported':False}
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    export(parser.parse_args().output)
