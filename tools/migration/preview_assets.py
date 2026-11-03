"""Exercise real Caddy/mediahelper file delivery with owned Jena capabilities."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
import uuid

import jwt
import requests

from preview_media import ASSET

PDF_ASSET = 'JS55Oy9IH15k'
PDF_IRI = 'urn:uuid:813a29d0-cbc3-41c3-b148-f0ad55dda343'


@contextmanager
def preview_assets(repository, source_root, output, call, public, api_url, iiif_url):
    """Keep isolated file delivery alive while checking bytes, ranges and grants.

    Uses unchanged Caddy routes and the installed mediahelper runtime with the
    repository source mounted read-only, so unreleased authorization fixes are tested.
    Copies only two PDF files and one image original; source hashes are verified
    on exit. All containers/network belong to this invocation and are removed.
    Yields the combined media origin for the existing browser preview.
    """
    root = source_root.resolve(strict=True)
    media = output / 'media'
    relatives = [Path('fasnacht/document/bmg') / PDF_ASSET / 'derived/document.pdf',
                 Path('fasnacht/document/bmg') / PDF_ASSET / 'original/1948_bmg-protokolle.pdf',
                 Path('fasnacht/image/bmg') / ASSET / 'original/004.jpg']
    hashes = {}
    for relative in relatives:
        source = (root / relative).resolve(strict=True)
        if not source.is_relative_to(root):
            raise ValueError('Source asset escapes media root')
        hashes[str(relative)] = hashlib.sha256(source.read_bytes()).hexdigest()
        destination = media / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        destination.chmod(0o444)
        for directory in relative.parents:
            (media / directory).chmod(0o755)
    name = 'oldap-jena-assets-' + uuid.uuid4().hex[:10]
    helper, proxy = name + '-helper', name + '-proxy'
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
    origin = f'http://127.0.0.1:{port}'
    config = (repository / 'Caddyfile').read_text().replace(
        'imageserver:8182', iiif_url.replace('http://127.0.0.1:', 'host.docker.internal:'))
    config_path = output / 'assets.Caddyfile'
    config_path.write_text(config)
    subprocess.run(['docker', 'network', 'create', name], check=True, capture_output=True)
    try:
        subprocess.run(['docker', 'run', '-d', '--name', helper, '--network', name,
            '--network-alias', 'mediaserver', '--pull=never', '--read-only', '--cap-drop=ALL',
            '--security-opt=no-new-privileges:true', '--tmpfs', '/tmp:rw,size=64m',
            '--mount', f'type=bind,source={media},target=/data/images,readonly',
            '--mount', f'type=bind,source={repository / "mediaserver"},target=/app,readonly',
            '-e', 'OLDAP_MEDIA_JWT_SECRET', '-e', 'OLDAP_ACCESS_JWT_SECRET',
            '-e', 'OLDAP_API_URL=' + api_url.replace('127.0.0.1', 'host.docker.internal'),
            '-e', 'OLDAP_INGEST_ROOT=/tmp/ingest', '-e', 'OLDAP_IMPORT_RECORDS_ROOT=/tmp/records',
            '-e', 'OLDAP_EXPORT_ROOT=/tmp/exports', '-e', 'OLDAP_MOBILE_UPLOAD_ROOT=/tmp/mobile',
            '-e', 'CORS_ORIGINS=http://127.0.0.1:5179',
            'lrosenth/oldap-mediahelper:normalization-local-20261010'], check=True, capture_output=True)
        subprocess.run(['docker', 'run', '-d', '--name', proxy, '--network', name,
            '--pull=never', '-p', f'127.0.0.1:{port}:8088', '--read-only', '--cap-drop=ALL',
            '--cap-add=NET_BIND_SERVICE',
            '--security-opt=no-new-privileges:true', '--tmpfs', '/data:rw,size=16m',
            '--tmpfs', '/config:rw,size=16m',
            '--mount', f'type=bind,source={media},target=/data/images,readonly',
            '--mount', f'type=bind,source={config_path},target=/etc/caddy/Caddyfile,readonly',
            'caddy:2.8'], check=True, capture_output=True)
        for _ in range(100):
            try:
                if requests.get(origin + '/health', timeout=2).status_code == 200:
                    break
            except requests.RequestException:
                pass
            time.sleep(.2)
        else:
            raise RuntimeError('Owned asset stack did not become ready')
        checks = []
        # This real PDF is internal: only the audit fixture holds its source roles.
        call('GET', '/data/mediaobject/id/' + PDF_ASSET, headers=public, status=404)
        token = call('GET', '/data/mediaobject/id/' + PDF_ASSET).json()['token']
        image_token = call('GET', '/data/mediaobject/id/' + ASSET, headers=public).json()['token']
        for asset, variant, relative, capability, mime in [
            (PDF_ASSET, 'derived', relatives[0], token, 'application/pdf'),
            (PDF_ASSET, 'original', relatives[1], token, 'application/pdf'),
            (ASSET, 'original', relatives[2], image_token, 'image/jpeg')]:
            url = f'{origin}/asset/{asset}/{variant}'
            params = {'token': capability, 'download': '1'}
            response = requests.get(url, params=params, timeout=30)
            assert response.status_code == 200, (variant, response.status_code)
            assert hashlib.sha256(response.content).hexdigest() == hashes[str(relative)]
            assert response.headers['Content-Type'].split(';')[0] == mime
            assert response.headers['Content-Disposition'].startswith('attachment;')
            assert 'X-Oldap-Internal-Path' not in response.headers
            head = requests.head(url, params=params, timeout=15)
            assert head.status_code == 200 and int(head.headers['Content-Length']) == len(response.content)
            part = requests.get(url, params=params, headers={'Range': 'bytes=0-31', 'Origin': 'http://127.0.0.1:5179'}, timeout=15)
            assert part.status_code == 206 and part.content == response.content[:32]
            assert part.headers['Access-Control-Allow-Origin'] == 'http://127.0.0.1:5179'
            checks.append(f'{asset}/{variant}: exact bytes, attachment, MIME, HEAD, range and CORS')
        pdf_url = f'{origin}/asset/{PDF_ASSET}/derived'
        inline = requests.get(pdf_url, params={'token': token}, timeout=30)
        assert inline.status_code == 200 and inline.headers['Content-Disposition'].startswith('inline;')
        checks.append('Authorized PDF inline delivery succeeds; anonymous API lookup returns 404')
        claims = jwt.decode(token, os.environ['OLDAP_MEDIA_JWT_SECRET'], algorithms=['HS256'], audience='oldap-api-media')
        for label, capability in [('absent', None), ('invalid', 'invalid'),
                ('expired', jwt.encode(dict(claims, exp=int(time.time())-60), os.environ['OLDAP_MEDIA_JWT_SECRET'], algorithm='HS256')),
                ('other-asset', image_token)]:
            response = requests.get(pdf_url, params={'token': capability} if capability else {}, timeout=30)
            assert response.status_code == (404 if label == 'absent' else 403), (label, response.status_code)
            checks.append(label + ' token cannot retrieve internal PDF')
        # Regressions for the formerly accepted signed zero grant and invalid
        # token fallback. Tokenless public delivery must remain available.
        zero = jwt.encode(dict(claims, permval=0), os.environ['OLDAP_MEDIA_JWT_SECRET'], algorithm='HS256')
        zero_status = requests.get(pdf_url, params={'token': zero}, timeout=30).status_code
        public_invalid = requests.get(f'{origin}/asset/{ASSET}/original', params={'token': 'invalid'}, timeout=30).status_code
        assert zero_status == 403 and public_invalid == 403
        assert requests.get(f'{origin}/asset/{ASSET}/original', timeout=30).status_code == 200
        checks.append('Zero permission and invalid supplied tokens denied; tokenless public original still available')
        report = {'policy_observations': {'signed_zero_permission_status': zero_status,
                  'invalid_token_public_original_status': public_invalid}, 'checks': checks, 'pdf_iri': PDF_IRI, 'source_sha256': hashes,
                  'scope': 'Installed mediahelper runtime with read-only repository source overlay and unchanged Caddy; invalid supplied capabilities fail closed. Tokenless public lookup retained.'}
        (output / 'asset-results.json').write_text(json.dumps(report, indent=2) + '\n')
        yield origin
    finally:
        for container in (proxy, helper):
            subprocess.run(['docker', 'rm', '-f', container], capture_output=True, check=False)
        subprocess.run(['docker', 'network', 'rm', name], capture_output=True, check=False)
        for relative, digest in hashes.items():
            if hashlib.sha256((root / relative).read_bytes()).hexdigest() != digest:
                raise AssertionError('Source asset changed: ' + relative)
