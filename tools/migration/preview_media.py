"""Owned SIPI fixture for the real Fasnacht browser rehearsal.

Only one derivative is copied; the source tree is never mounted or modified.
The existing signed-capability policy is used without anonymous API fallback.
"""
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

ASSET = 'bmg_archive_0024_001_stamm_1912_fotos_fasnacht_004'
MEDIA_IRI = 'urn:uuid:3553c881-c53b-444a-ac8d-2995cf4966fe'


@contextmanager
def preview_media(source_root, output, call, public_headers, con):
    """Copy one real derivative, check signed delivery and retain it for preview.

    Args:
        source_root: Read-only source media root containing the known Fasnacht asset.
        output: Private, newly created rehearsal directory.
        call: Authenticated owned API request helper.
        public_headers: Unknown-user access headers for capability issuance.
        con: Owned administrator connection for a reversible grant check.

    Yields:
        Local media origin. The owned container is removed on every exit.
    """
    relative = Path('fasnacht/image/bmg') / ASSET / 'derived/master.tif'
    root = source_root.resolve(strict=True)
    source = (root / relative).resolve(strict=True)
    if not source.is_relative_to(root):
        raise ValueError('Media fixture must stay inside its source root')
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    media_root = output / 'media'
    target = media_root / relative
    target.parent.mkdir(parents=True)
    shutil.copyfile(source, target)
    # The disposable copy must be readable by SIPI's unprivileged container user.
    target.chmod(0o444)
    for directory in relative.parents:
        (media_root / directory).chmod(0o755)
    name = 'oldap-jena-preview-' + uuid.uuid4().hex[:12]
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
    origin = f'http://127.0.0.1:{port}'
    # Docker must fail rather than reuse another listener if the port is taken.
    command = ['docker', 'run', '--detach', '--name', name, '--pull=never',
               '--publish', f'127.0.0.1:{port}:8182', '--read-only', '--cap-drop=ALL',
               '--security-opt=no-new-privileges:true', '--memory=1g', '--pids-limit=128',
               '--tmpfs', '/tmp:rw,noexec,nosuid,nodev,size=64m',
               '--mount', f'type=bind,source={media_root},target=/data/images,readonly',
               '--entrypoint', '/bin/sh', '-e', 'OLDAP_MEDIA_JWT_SECRET',
               '-e', 'OLDAP_SIPI_ANONYMOUS=false', '-e', 'SIPI_LISTEN_ADDRESS=0.0.0.0',
               '-e', 'SIPI_PORT=8182', '-e', 'SIPI_PUBLIC_BASE_URL=' + origin, '-e', 'SIPI_IIIF_ROOT=/data/images',
               '-e', 'SIPI_PREFLIGHT_SCRIPT=/opt/sipi/examples/oldap/preflight.lua',
               '-e', 'SIPI_SIZE_UPSCALING=true', '-e', 'SIPI_CORS_ORIGINS=*',
               'lrosenth/sipi-2:0.1.3', '/opt/sipi/examples/oldap/docker-entrypoint.sh']
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        for _ in range(100):
            try:
                if requests.get(origin + '/iiif/3/probe/info.json', timeout=2).status_code == 403:
                    break
            except requests.RequestException:
                pass
            time.sleep(.1)
        else:
            raise RuntimeError('Owned SIPI did not become ready')
        metadata = call('GET', '/data/mediaobject/id/' + ASSET, headers=public_headers).json()
        capability = metadata['token']
        checks = []
        info_url = origin + '/iiif/3/' + ASSET + '/info.json'
        info = requests.get(info_url, params={'token': capability}, timeout=15)
        assert info.status_code == 200, info.status_code
        checks.append('Public Jena identity receives usable SIPI capability')
        image_url = origin + '/iiif/3/' + ASSET + '/full/!800,800/0/default.jpg'
        response = requests.get(image_url, params={'token': capability}, timeout=30)
        assert response.status_code == 200 and response.content.startswith(b'\xff\xd8\xff')
        (output / 'media-preview.jpg').write_bytes(response.content)
        checks.append('Real TIFF derivative delivered as JPEG')
        cors = requests.head(image_url, params={'token': capability},
                             headers={'Origin': 'http://127.0.0.1:5179'}, timeout=15)
        assert cors.status_code == 200 and cors.headers.get('Access-Control-Allow-Origin') == '*'
        checks.append('Signed HEAD and browser CORS succeed')
        # A previously issued capability has its own bounded lifetime. Removing
        # the asserted role edge must prevent NEW issuance, even with its orphan
        # annotation still present. Restore the exact edge before browser use.
        edge = f'<{MEDIA_IRI}> <http://oldap.org/base#attachedToRole> <http://oldap.org/base#Unknown> .'
        from oldaplib.src.helpers.context import Context
        graph = str(Context(name=con.context_name)['fasnacht']) + 'data'
        con.update_query(f'DELETE DATA {{ GRAPH <{graph}> {{ {edge} }} }}')
        try:
            call('GET', '/data/mediaobject/id/' + ASSET, headers=public_headers, status=404)
            checks.append('Revoked public membership prevents new media capability issuance')
        finally:
            con.update_query(f'INSERT DATA {{ GRAPH <{graph}> {{ {edge} }} }}')
        renewed = call('GET', '/data/mediaobject/id/' + ASSET, headers=public_headers).json()['token']
        assert requests.get(info_url, params={'token': renewed}, timeout=15).status_code == 200
        checks.append('Restored membership issues a usable renewed capability')
        claims = jwt.decode(capability, os.environ['OLDAP_MEDIA_JWT_SECRET'], algorithms=['HS256'], audience='oldap-api-media')
        negatives = {'invalid': 'invalid', 'absent': None}
        for label, change in [('expired', {'exp': int(time.time()) - 60}),
                              ('wrong-asset', {'id': 'other', 'assetId': 'other'}),
                              ('no-permission', {'permval': 0})]:
            negatives[label] = jwt.encode(dict(claims, **change), os.environ['OLDAP_MEDIA_JWT_SECRET'], algorithm='HS256')
        for label, token in negatives.items():
            denied = requests.get(image_url, params={'token': token} if token else {}, timeout=15)
            assert denied.status_code == 403, (label, denied.status_code)
            checks.append(label + ' capability denied after successful image request')
        report = {'checks': checks, 'asset': ASSET, 'media_iri': MEDIA_IRI,
                  'source_sha256': digest, 'width': info.json()['width'], 'height': info.json()['height'],
                  'scope': 'Signed image delivery only; anonymous fallback, PDF, uploads and production load excluded.'}
        (output / 'media-results.json').write_text(json.dumps(report, indent=2) + '\n')
        yield origin
    finally:
        subprocess.run(['docker', 'rm', '--force', name], capture_output=True, check=False)
        if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
            raise AssertionError('Source derivative changed during rehearsal')
