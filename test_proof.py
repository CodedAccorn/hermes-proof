import importlib.util
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location('proof_tools', Path(__file__).with_name('tools.py'))
tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tools)


def _configure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('HERMES_PROOF_ROOT', str(tmp_path))
    monkeypatch.setenv('HERMES_HOME', str(tmp_path / 'hermes-home'))

def test_verified(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    (tmp_path / 'app.txt').write_text('ready')
    report = json.loads(tools.proof_verify([{'type': 'file_contains', 'target': 'app.txt', 'expected': 'ready'}]))
    assert report['status'] == 'verified'

def test_failure(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    report = json.loads(tools.proof_verify([{'type': 'file_exists', 'target': 'missing.txt'}]))
    assert report['status'] == 'failed'

def test_traversal(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    report = json.loads(tools.proof_verify([{'type': 'file_exists', 'target': '../outside'}]))
    assert report['status'] == 'unverified'

def test_http_not_claimed_verified(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    report = json.loads(tools.proof_verify([{'type': 'http_status', 'target': 'https://example.com', 'expected': 200}]))
    assert report['status'] == 'unverified'


def test_invalid_contract_fails_closed(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    report = json.loads(tools.proof_verify([{'type': 'file_exists', 'target': 'x', 'surprise': True}]))
    assert report['status'] == 'unverified'
    assert 'unsupported check fields' in report['error']


def test_missing_content_target_is_unverified(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    report = json.loads(tools.proof_verify([{'type': 'file_contains', 'target': 'missing', 'expected': 'x'}]))
    assert report['status'] == 'unverified'


def test_hash_and_json_checks(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    data = b'proof\n'
    (tmp_path / 'artifact.bin').write_bytes(data)
    (tmp_path / 'result.json').write_text('{"deploy":{"ready":true}}', encoding='utf-8')
    report = json.loads(tools.proof_verify([
        {'name': 'immutable artifact', 'type': 'file_sha256', 'target': 'artifact.bin',
         'expected': hashlib.sha256(data).hexdigest()},
        {'name': 'deployment state', 'type': 'json_equals', 'target': 'result.json',
         'path': '$.deploy.ready', 'expected': True},
    ]))
    assert report['status'] == 'verified'
    assert all(item['status'] == 'verified' for item in report['checks'])


def test_report_persists_and_retrieves_by_id(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    (tmp_path / 'app.txt').write_text('ready', encoding='utf-8')
    created = json.loads(tools.proof_verify([{'type': 'file_exists', 'target': 'app.txt'}]))
    latest = json.loads(tools.proof_report())
    by_id = json.loads(tools.proof_report({'report_id': created['id']}))
    assert latest == created == by_id
    assert (tmp_path / 'hermes-home' / 'hermes-proof' / 'evidence' / f"{created['id']}.json").is_file()


def test_unset_root_fails_closed(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    monkeypatch.delenv('HERMES_PROOF_ROOT')
    (tmp_path / 'app.txt').write_text('ready', encoding='utf-8')
    report = json.loads(tools.proof_verify([{'type': 'file_exists', 'target': 'app.txt'}]))
    assert report['status'] == 'unverified'
    assert report['error'] == 'verification root is not configured'


def test_hermes_home_is_forbidden_without_secret_disclosure(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    home = tmp_path / 'hermes-home'
    home.mkdir()
    (home / 'auth.json').write_text('{"token":"do-not-disclose"}', encoding='utf-8')
    report_text = tools.proof_verify([
        {'type': 'json_equals', 'target': 'hermes-home/auth.json', 'path': '$',
         'expected': {'token': 'do-not-disclose'}}
    ])
    report = json.loads(report_text)
    assert report['status'] == 'unverified'
    assert 'do-not-disclose' not in json.dumps(report['checks'][0]['evidence'].get('observed'))


def test_sensitive_targets_are_forbidden(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    targets = ['.env', '.env.local', 'private.pem', 'private.key',
               '.ssh/id_ed25519', '.aws/credentials',
               '.config/gcloud/application_default_credentials.json']
    for target in targets:
        path = tmp_path / target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('secret', encoding='utf-8')
    report = json.loads(tools.proof_verify([
        {'type': 'file_contains', 'target': target, 'expected': 'secret'} for target in targets
    ]))
    assert report['status'] == 'unverified'
    assert all(check['status'] == 'unverified' for check in report['checks'])


def test_report_survives_fresh_process(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    (tmp_path / 'app.txt').write_text('ready', encoding='utf-8')
    created = json.loads(tools.proof_verify([{'type': 'file_exists', 'target': 'app.txt'}]))
    plugin_dir = Path(__file__).parent
    code = 'import json, tools; print(json.loads(tools.proof_report())["id"])'
    environment = os.environ.copy()
    environment['PYTHONPATH'] = str(plugin_dir)
    output = subprocess.check_output([sys.executable, '-c', code], cwd=tmp_path,
                                     env=environment, text=True).strip()
    assert output == created['id']


def test_bad_report_id_cannot_traverse(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    report = json.loads(tools.proof_report('../secret'))
    assert report['status'] == 'unverified'


def test_absolute_target_is_unverified(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    report = json.loads(tools.proof_verify([{'type': 'file_exists', 'target': str(tmp_path / 'x')}]))
    assert report['status'] == 'unverified'


def test_symlink_escape_is_unverified(tmp_path, monkeypatch):
    _configure(tmp_path, monkeypatch)
    outside = tmp_path.parent / f'{tmp_path.name}-outside.txt'
    outside.write_text('secret', encoding='utf-8')
    link = tmp_path / 'escape.txt'
    try:
        os.symlink(outside, link)
    except (OSError, NotImplementedError):
        import pytest
        pytest.skip('symlinks are unavailable for this test user')
    report = json.loads(tools.proof_verify([{'type': 'file_contains', 'target': 'escape.txt', 'expected': 'secret'}]))
    assert report['status'] == 'unverified'
