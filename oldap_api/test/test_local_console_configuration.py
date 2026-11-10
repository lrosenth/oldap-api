"""Native console installation preserves secrets and refuses an active backend."""
import json
import plistlib
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
import configure_local_console as console


def test_busy_service_refuses_before_configuration(tmp_path):
    with patch.object(console.socket, 'socket') as socket:
        socket.return_value.__enter__.return_value.connect_ex.return_value = 0
        with pytest.raises(ValueError, match='services-stop'):
            console.install(tmp_path, tmp_path / 'missing.json', tmp_path / 'caddy')


def test_installs_loopback_proxy_and_preserves_existing_configuration(tmp_path):
    runtime = tmp_path / 'Library/Application Support/OLDAP/local-jena'
    agents = tmp_path / 'Library/LaunchAgents'
    runtime.mkdir(parents=True)
    agents.mkdir(parents=True)
    original = 'dataset=/private/dataset\nport=3031\nserviceSecret=retained\n'
    (runtime / 'service.properties').write_text(original)
    (agents / 'org.oldap.jena.plist').write_bytes(plistlib.dumps({'ProgramArguments':['old/start','private.properties']}))
    distribution = tmp_path / 'distribution'
    (distribution / 'lib').mkdir(parents=True)
    (distribution / 'lib/oldap-jena-service-test.jar').write_bytes(b'artifact')
    (distribution / 'build.json').write_text(json.dumps({'service_sha256': console.hashlib.sha256(b'artifact').hexdigest()}))
    credentials = tmp_path / 'credentials.json'
    credentials.write_text(json.dumps({'username':'admin','password':'private password'}))
    credentials.chmod(0o600)
    with (patch.object(console.Path, 'home', return_value=tmp_path),
          patch.object(console.socket, 'socket') as socket,
          patch.object(console.subprocess, 'run', side_effect=[
              SimpleNamespace(stdout='hashed-password',returncode=0), SimpleNamespace(returncode=0)
          ]) as run):
        socket.return_value.__enter__.return_value.connect_ex.return_value = 1
        console.install(distribution, credentials, tmp_path / 'caddy')
    config = (runtime / 'console.Caddyfile').read_text()
    assert 'bind 127.0.0.1' in config
    assert 'basic_auth' in config and 'header_up -Authorization' in config
    assert 'private password' not in config
    assert run.call_args_list[0].kwargs['input'] == 'private password'
    assert 'private password' not in run.call_args_list[0].args[0]
    properties = (runtime / 'service.properties').read_text()
    assert properties.startswith(original)
    assert 'adminLoopback=true' in properties
    backup = next(runtime.glob('before-console-*'))
    assert (backup / 'service.properties').read_text() == original
    assert (runtime / 'console.Caddyfile').stat().st_mode & 0o077 == 0
    java = plistlib.loads((agents / 'org.oldap.jena.plist').read_bytes())
    assert java['ProgramArguments'] == [str(distribution / 'start'),'private.properties']
