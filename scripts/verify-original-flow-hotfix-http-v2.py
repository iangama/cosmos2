"""Check isolated HTTP models, persistence and texture recovery; no native UI acceptance."""
from pathlib import Path
import argparse
import contextlib
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / 'output/original-flow-hotfix-staging-v2'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('Invalid label')
    out = ROOT / ('evidence/original-flow-hotfix-http-' + args.label + '.json')
    folder = ROOT / ('output/original-flow-hotfix-http-' + args.label)
    assert not out.exists() and not folder.exists(), 'Preserve previous evidence'
    folder.mkdir()
    preparation = json.loads((STAGE / 'preparation.json').read_text())
    sources = {str((STAGE / name / relative).relative_to(ROOT)).replace('\\', '/'): digest
               for name in ['app', 'data'] for relative, digest in preparation[name + '_sha256'].items()}
    sources.update({str(p.relative_to(ROOT)).replace('\\', '/'): sha(p)
                    for p in [Path(__file__), STAGE / 'preparation.json']})
    protected_paths = [ROOT / name for name in [
        'output/session.json', 'Iniciar-Cosmos2.cmd', 'Abrir-Planetas.cmd', 'Abrir-Planetas-e-Luas.cmd',
        'output/original-forces-hotfix-staging/preparation.json',
        'evidence/original-forces-hotfix-http-20261114a.json',
        'evidence/original-forces-dependency-repair-20261114a.json']]
    for candidate in [ROOT / 'user/forces/latest.json', ROOT / 'user/sessions/latest.json']:
        if candidate.is_file():
            protected_paths.append(candidate)
    protected = {str(p.relative_to(ROOT)).replace('\\', '/'): sha(p) for p in protected_paths}
    proof = dict(accepted=False, completed=False, native_user_flow_accepted=False, installed=False,
                 scope='Separate loopback HTTP servers, existing scientific models, private persistence and asset-error handling only. No renderer or original-launcher acceptance.',
                 source_sha256=sources, protected_sha256=protected, checks=[], server_exits=[])
    (folder / 'recipe-before-execution.json').write_text(json.dumps(proof, indent=2)+'\n')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    @contextlib.contextmanager
    def backend(candidate, name):
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        env = os.environ.copy()
        env['COSMOS2_STORAGE'] = str(folder / name / 'gravity-sessions')
        log = (folder / (name + '.log')).open('xb')
        child = subprocess.Popen([sys.executable, '-u', '-Xutf8', str(candidate / 'app/server.py'), '--port', str(port)],
                                 cwd=ROOT, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)

        def request(route, payload=None):
            body = None if payload is None else json.dumps(payload).encode()
            req = urllib.request.Request('http://127.0.0.1:' + str(port) + route, data=body,
                                         headers={'Content-Type': 'application/json'} if body else {})
            try:
                response = opener.open(req, timeout=45)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                content = response.read()
                ctype = response.headers.get('Content-Type', '')
                return response.status, json.loads(content) if 'application/json' in ctype else content, ctype

        try:
            deadline = time.monotonic() + 60
            while True:
                assert child.poll() is None, name + ' backend exited before health'
                try:
                    code, health, _ = request('/health')
                    if code == 200 and health['application'] == 'cosmos2':
                        break
                except OSError:
                    pass
                assert time.monotonic() < deadline, 'Health timeout'
                time.sleep(.1)
            yield request
        finally:
            try:
                if child.poll() is None:
                    request('/api/shutdown', {})
                child.wait(timeout=15)
            except Exception:
                if child.poll() is None:
                    child.terminate()
                    child.wait(timeout=15)
            finally:
                log.close()
                proof['server_exits'].append(dict(name=name, exit_code=child.returncode))

    def record(name, **values):
        proof['checks'].append(dict(name=name, **values))

    try:
        assert all(sha(ROOT / name) == digest for name, digest in sources.items())
        with backend(STAGE, 'candidate') as request:
            code, catalog, _ = request('/api/forces/catalog')
            assert code == 200 and len(catalog['scenarios']) == 12
            record('local-scientific-catalog', scenarios=sorted(catalog['scenarios']))
            code, image, content_type = request('/api/geomagnetism/texture')
            assert code == 200 and content_type == 'image/jpeg' and image.startswith(b'\xff\xd8')
            digest = hashlib.sha256(image).hexdigest()
            assert digest == preparation['texture_sha256']
            record('earth-texture-complete', bytes=len(image), sha256=digest)
            for kind in ['spatial', 'layers']:
                code, state, _ = request('/api/' + kind + '/state')
                assert code == 200 and not state['active'] and not state['recovery_required'] and state['guard']
                record('inactive-private-service-state', kind=kind)
            code, value, _ = request('/api/forces/load', {})
            assert code == 400 and value['ok'] is False and value['error']
            record('empty-private-save-is-json-error', status=code)
            normalized = None
            for scenario in ['gravity', 'strong', 'weak', 'relativity', 'geomagnetic']:
                code, value, _ = request('/api/forces/evaluate', dict(scenario=scenario, controls={}, parameters={}))
                assert code == 200 and value['ok'] and value['configuration']['scenario'] == scenario
                if scenario == 'geomagnetic':
                    assert value['result']['geomagnetic']['grid'] and not value['result']['time_s']
                else:
                    assert len(value['result']['time_s']) == 241
                (folder / (scenario + '.json')).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
                record('existing-model-evaluates', scenario=scenario, physics_sha256=value['physics_sha256'])
                if scenario == 'strong':
                    normalized = value
            code, saved, _ = request('/api/forces/save', normalized['configuration'])
            assert code == 200 and saved['ok']
            code, loaded, _ = request('/api/forces/load', {})
            assert code == 200 and loaded['configuration'] == normalized['configuration']
            assert loaded['restoration']['status'] == 'same_generation'
            code, reevaluated, _ = request('/api/forces/evaluate', loaded['configuration'])
            assert code == 200 and reevaluated['physics_sha256'] == normalized['physics_sha256']
            record('private-save-load-retains-generation', physics_sha256=reevaluated['physics_sha256'])
            code, exported, _ = request('/api/forces/export', loaded['configuration'])
            assert code == 200 and exported['ok'] and exported['physics_sha256'] == normalized['physics_sha256']
            destination = Path(exported['export_file']).resolve()
            assert destination.is_relative_to(STAGE.resolve()) and destination.is_file()
            assert json.loads(destination.read_text(encoding='utf8')) == exported
            record('export-stays-inside-candidate', path=destination.relative_to(ROOT).as_posix(), sha256=sha(destination))
            code, error, _ = request('/api/forces/evaluate', dict(scenario='missing-model', controls={}, parameters={}))
            assert code == 400 and error['ok'] is False and error['error']
            assert request('/api/forces/load', {})[1]['configuration'] == loaded['configuration']
            record('invalid-model-preserves-saved-configuration', status=code)
        # A separate copy intentionally omits the texture. The reviewed candidate is never altered.
        missing = folder / 'missing-texture-copy'
        shutil.copytree(STAGE / 'app', missing / 'app', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        shutil.copytree(STAGE / 'data/science', missing / 'data/science')
        with backend(missing, 'missing-texture') as request:
            code, error, _ = request('/api/geomagnetism/texture')
            assert code == 503 and error['ok'] is False and 'textura' in error['error'].lower()
            assert request('/health')[0] == 200
            assert len(request('/api/forces/catalog')[1]['scenarios']) == 12
            record('missing-texture-returns-readable-error-and-server-recovers', status=code, message=error['error'])
        assert all(item['exit_code'] == 0 for item in proof['server_exits']) and len(proof['server_exits']) == 2
        assert all(sha(ROOT / name) == digest for name, digest in sources.items())
        assert all(sha(ROOT / name) == digest for name, digest in protected.items())
        proof.update(accepted=True, completed=True, protected_unchanged=True)
    except Exception:
        proof['failure'] = traceback.format_exc()
    finally:
        out.write_text(json.dumps(proof, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps(dict(accepted=proof['accepted'], completed=proof['completed'], checks=len(proof['checks']),
                          server_exits=proof['server_exits'], failure=proof.get('failure')), ensure_ascii=False))
    return 0 if proof['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
