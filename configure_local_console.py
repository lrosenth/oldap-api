"""Install the optional native Fuseki proxy after `make services-stop`.

Uses an accepted Jena distribution with adminLoopback support and an existing
private JSON credential file (username/password). Saves previous configuration;
never copies or opens the dataset. Run services-start to activate the result.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import secrets
import shutil
import socket
import subprocess
import tempfile


def install(distribution: Path, credentials: Path, caddy: Path):
    """Stage/validate the proxy, preserve rollback files, then install native config."""
    os.umask(0o077)
    runtime = Path.home() / 'Library/Application Support/OLDAP/local-jena'
    agents = Path.home() / 'Library/LaunchAgents'
    for port in (8000, 8001, 3031, 3030, 8040):
        with socket.socket() as connection:
            if connection.connect_ex(('127.0.0.1', port)) == 0:
                raise ValueError('Run make services-stop first; native ports must be free.')
    if credentials.stat().st_mode & 0o077:
        raise ValueError('Credential file must have mode 0600.')
    auth = json.loads(credentials.read_text())
    if not re.fullmatch(r'[A-Za-z0-9_-]+', auth['username']) or not auth['password']:
        raise ValueError('Invalid console credentials.')
    manifest = json.loads((distribution / 'build.json').read_text())
    artifacts = list((distribution / 'lib').glob('oldap-jena-service-*.jar'))
    if len(artifacts) != 1 or hashlib.sha256(artifacts[0].read_bytes()).hexdigest() != manifest['service_sha256']:
        raise ValueError('Jena service hash mismatch.')
    hashed = subprocess.run([str(caddy), 'hash-password', '--algorithm', 'bcrypt'],
                            input=auth['password'], text=True, capture_output=True, check=True).stdout.strip()
    secret = secrets.token_urlsafe(48)
    config = f'''{{
    admin off
    auto_https off
}}
http://127.0.0.1:3030 {{
    bind 127.0.0.1
    handle /_ready {{
        rewrite * /$/ping
        reverse_proxy 127.0.0.1:8040 {{
            header_up X-Oldap-Admin-Key {secret}
        }}
    }}
    handle {{
        basic_auth {{
            {auth['username']} {hashed}
        }}
        reverse_proxy 127.0.0.1:8040 {{
            header_up X-Oldap-Admin-Key {secret}
            header_up -Authorization
        }}
    }}
}}
'''
    with tempfile.NamedTemporaryFile(mode='w', suffix='.Caddyfile', dir=runtime) as staged:
        staged.write(config)
        staged.flush()
        result = subprocess.run([str(caddy), 'validate', '--adapter', 'caddyfile', '--config', staged.name],
                                capture_output=True)
        if result.returncode:
            raise ValueError('Caddy configuration validation failed.')
    service_config = runtime / 'service.properties'
    java_agent = agents / 'org.oldap.jena.plist'
    console_agent = agents / 'org.oldap.jena-console.plist'
    proxy_config = runtime / 'console.Caddyfile'
    backup = runtime / ('before-console-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    backup.mkdir(mode=0o700)
    for path in (service_config, java_agent, console_agent, proxy_config):
        if path.exists():
            shutil.copy2(path, backup / path.name)
    properties = '\n'.join(line for line in service_config.read_text().splitlines()
                           if not line.startswith(('adminPort=', 'adminOrigin=', 'adminSecret=', 'adminLoopback=')))
    service_config.write_text(properties + f'\nadminPort=8040\nadminSecret={secret}\nadminOrigin=http://127.0.0.1:3030\nadminLoopback=true\n')
    service_config.chmod(0o600)
    proxy_config.write_text(config)
    proxy_config.chmod(0o600)
    java = plistlib.loads(java_agent.read_bytes())
    java['ProgramArguments'][0] = str(distribution / 'start')
    java_agent.write_bytes(plistlib.dumps(java))
    console_agent.write_bytes(plistlib.dumps({
        'Label': 'org.oldap.jena-console',
        'ProgramArguments': [str(caddy), 'run', '--adapter', 'caddyfile', '--config', str(proxy_config)],
        'RunAtLoad': True, 'KeepAlive': True,
        'StandardOutPath': str(runtime / 'org.oldap.jena-console.stdout.log'),
        'StandardErrorPath': str(runtime / 'org.oldap.jena-console.stderr.log'),
    }))
    print('Installed local Fuseki console at http://127.0.0.1:3030')
    print('Private configuration backup:', backup)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--distribution', type=Path, required=True)
    parser.add_argument('--credentials', type=Path, required=True)
    parser.add_argument('--caddy', type=Path, default=Path('/opt/homebrew/bin/caddy'))
    args = parser.parse_args()
    install(args.distribution.resolve(), args.credentials.resolve(), args.caddy.resolve())
