"""Preserve a legacy export's account header and convert its RDF privately.

Only a leading comment/blank preamble is separated, byte for byte. The original
file and header are retained; accounts are NOT restored in this data rehearsal.
The existing conservative native converter still validates all RDF content.
"""
import gzip
import hashlib
import json
from pathlib import Path
import subprocess


def prepare_export(source, output, library, java, jar):
    """Return the converted instance-only seed, retaining private audit files.

    Reject oversized input and account records outside the initial preamble.
    Run the verified RDF-star converter unchanged, then extract the exact named
    instance graph natively. Model/list/admin graphs remain in converted.trig.
    """
    raw = source.read_bytes()
    with gzip.open(source, 'rb') if raw[:2] == b'\x1f\x8b' else source.open('rb') as stream:
        content = stream.read(16 * 1024 * 1024 + 1)
    if len(content) > 16 * 1024 * 1024:
        raise ValueError('Export exceeds the converter size bound')
    lines = content.splitlines(keepends=True)
    boundary = 0
    for line in lines:
        if line.strip() and not line.lstrip().startswith(b'#'):
            break
        boundary += 1
    header, rdf = b''.join(lines[:boundary]), b''.join(lines[boundary:])
    if b'#>>' in rdf:
        raise ValueError('Account records outside the leading header require manual review')
    (output / 'original-export.bin').write_bytes(raw)
    (output / 'account-header.txt').write_bytes(header)
    (output / 'source-rdf.trig').write_bytes(rdf)
    def native(name, *args):
        result = subprocess.run([str(java), '--class-path', str(jar),
            str(library / 'tools/migration' / name), *map(str, args)], capture_output=True, timeout=120)
        (output / (name + '.log')).write_bytes(result.stdout + result.stderr)
        if result.returncode:
            raise AssertionError('Native export preparation failed: ' + name)
    native('ConvertLegacyRdfStar.java', output / 'source-rdf.trig', output / 'converted')
    seed = output / 'instance-data.trig'
    native('ExtractFasnachtData.java', output / 'converted/converted.trig', seed)
    report = {'source_sha256': hashlib.sha256(raw).hexdigest(),
        'account_header_sha256': hashlib.sha256(header).hexdigest(),
        'account_records_retained_not_restored': sum(line.lstrip().startswith(b'#>>') for line in header.splitlines()),
        'scope': 'Instance graph only; target model/taxonomies imported from migration YAML; source account header retained privately'}
    (output / 'export-preparation.json').write_text(json.dumps(report, indent=2)+'\n')
    return seed
