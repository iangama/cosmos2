"""Durable gated CPU -> K4 profile -> isolated K5 first-native workflow."""
from pathlib import Path
import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import time
import traceback
import psutil

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / '.tooling/python/Scripts/python.exe'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    parser.add_argument('--worker', action='store_true')
    args = parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('Invalid label')
    base = ROOT / ('output/is6-k5-import-flow-' + args.label)
    if not args.worker:
        lock = base.with_name(base.name + '-launch').with_suffix('.json')
        if lock.exists() or base.with_suffix('.json').exists():
            raise FileExistsError('Preserve workflow; inspect it instead of launching again')
        with base.with_suffix('.log').open('xb') as stdout, base.with_name(base.name + '-errors').with_suffix('.log').open('xb') as stderr:
            child = subprocess.Popen([str(PYTHON), '-u', '-Xutf8', str(Path(__file__)), '--label', args.label, '--worker'],
                                     cwd=ROOT, stdout=stdout, stderr=stderr,
                                     creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
        lock.write_text(json.dumps(dict(pid=child.pid, started_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                                        source_sha256=sha(Path(__file__))), indent=2) + '\n', encoding='utf8')
        print(json.dumps(dict(pid=child.pid, workflow=base.with_suffix('.json').as_posix())))
        return 0
    report = dict(accepted=False, completed=False, pid=os.getpid(), steps=[], stage='first-native-s',
                  owner_sha256=sha(ROOT / 'user/sessions/latest.json'),
                  scope='Gated S/T native functional/process tests for 0.21.1 only; manual visual review, cut, own profile, promotion and complete IS6/v1 acceptance remain pending.')
    paths = [Path(__file__), *list((ROOT / 'output/is6-layers-migration-staging').glob('*.py')),
             *list((ROOT / 'output/is6-layers-migration-staging/ui').glob('*'))]
    report['source_sha256'] = {p.relative_to(ROOT).as_posix(): sha(p) for p in paths if p.is_file()}
    def persist(stage=None):
        if stage:
            report['stage'] = stage
            print(json.dumps(dict(stage=stage)), flush=True)
        base.with_suffix('.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    def unchanged():
        assert all(sha(ROOT / name) == seal for name, seal in report['source_sha256'].items())
        assert sha(ROOT / 'user/sessions/latest.json') == report['owner_sha256']
    def read(path):
        try:
            return json.loads(path.read_text(encoding='utf-8-sig'))
        except (FileNotFoundError, ValueError, PermissionError):
            return None
    def wait_receipt(path, *, accepted=False, timeout=7200):
        until = time.monotonic() + timeout
        while time.monotonic() < until:
            value = read(path)
            if value is not None:
                if value.get('failure') or value.get('cleanup_failure'):
                    raise RuntimeError('Failed prerequisite: ' + str(path))
                if not value.get('completed') and value.get('pid') and not psutil.pid_exists(value['pid']):
                    raise RuntimeError('Driver process exited without a completed receipt: ' + str(path))
                if value.get('completed'):
                    if accepted:
                        assert value.get('accepted'), path
                    return value
            time.sleep(3)
        raise TimeoutError(str(path))
    def run(script, *fields):
        unchanged()
        command = [str(PYTHON), '-u', '-Xutf8', str(ROOT / 'scripts' / script), *fields]
        entry = dict(script=script, args=list(fields), source_sha256=sha(ROOT / 'scripts' / script))
        report['steps'].append(entry)
        persist(script)
        result = subprocess.run(command, cwd=ROOT)
        entry['exit'] = result.returncode
        persist()
        assert result.returncode == 0, entry
    def bootstrap(label):
        path = ROOT / ('output/is6-layers-' + ('storage' if label.startswith('profile-k4') else 'import') + '-host-' + label + '.log')
        until = time.monotonic() + 180
        while time.monotonic() < until:
            if path.exists():
                for line in path.read_text().splitlines():
                    try:
                        value = json.loads(line)
                    except ValueError:
                        continue
                    if 'bootstrap_exit' in value:
                        assert value['bootstrap_exit'] == 0
                        return value, path
            time.sleep(2)
        raise TimeoutError('Bootstrap: ' + label)
    def exited(initial, path):
        until = time.monotonic() + 180
        while time.monotonic() < until:
            lines = [json.loads(line) for line in path.read_text().splitlines() if line.startswith('{')]
            if lines and 'engine_exit' in lines[-1]:
                assert lines[-1]['engine_exit'] == 0
                if not any(psutil.pid_exists(initial[key]) for key in ['app', 'server']):
                    time.sleep(3)
                    return
            time.sleep(2)
        raise TimeoutError('Process cleanup: ' + str(path))
    persist()
    try:
        for phase,label,host_label in [('first','20261104s','k5-first-s-20261104'),('restart','20261104t','k5-restart-t-20261104')]:
            persist('native-'+label)
            if not (ROOT/('output/is6-layers-import-host-'+host_label+'.json')).exists():
                run('start-is6-layers-import-background-v2.py','--label',host_label)
            initial,host=bootstrap(host_label)
            driver=ROOT/('output/is6-layers-import-native-'+label+'-driver.json')
            if not driver.exists():
                run('run-is6-layers-import-verification-v4.py','--label',label,'--phase',phase,'--seed-label','20261104s')
            outcome=wait_receipt(driver,timeout=2400)
            exited(initial,host)
            assert outcome['verification_exit']==0
            proof=ROOT/('evidence/is6-layers-import-native-'+label+'.json')
            wait_receipt(proof,accepted=True)
            process=ROOT/('evidence/is6-layers-import-native-process-'+label+'.json')
            if not process.exists():
                run('audit-is6-layers-import-process-v2.py','--kind','native','--label',label,'--host-label',host_label)
            wait_receipt(process,accepted=True)
        unchanged()
        report.update(accepted=True,completed=True)
        persist('native-S-T-complete-manual-visual-review-and-cut-pending')
    except Exception:
        report.update(completed=True, failure=traceback.format_exc())
        persist('stopped-at-failed-gate')
    return 0 if report['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
