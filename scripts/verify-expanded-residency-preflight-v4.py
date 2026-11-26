"""Thirty native schema6 samples only; retain current app and protected records."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import traceback
import zipfile

import psutil
import expanded_residency_contract_v3 as contract

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'output/is6-expanded-journey-product0.27.0/app'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    assert args.label and len(args.label) <= 20 and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
    folder = ROOT / f'output/is6-expanded-residency-preflight-{args.label}'
    out = ROOT / f'evidence/is6-expanded-residency-preflight-{args.label}.json'
    assert not folder.exists() and not out.exists()
    offline_path = ROOT / 'evidence/is6-expanded-history-offline-20261113a.json'
    offline = json.loads(offline_path.read_text())
    assert offline['accepted'] and offline['completed'] and len(offline['refusals']) == 9
    assert all(sha(ROOT / name) == seal for name, seal in offline['source_sha256'].items())
    seed_path = ROOT / 'evidence/is6-expanded-journey-native-20261113a.json'
    seed = json.loads(seed_path.read_text())
    assert seed['accepted'] and seed['completed']
    protected = {**seed['protected_sha256'], **{item['original']: item['sha256'] for item in seed['archives']}}
    assert all(sha(ROOT / name) == seal for name, seal in protected.items())
    folder.mkdir()
    sources = dict(offline['source_sha256'])
    for path in [Path(__file__), offline_path, seed_path]:
        sources[path.relative_to(ROOT).as_posix()] = sha(path)
    with zipfile.ZipFile(folder / 'executed-sources.zip', 'x', zipfile.ZIP_DEFLATED) as archive:
        for name in sources:
            archive.write(ROOT / name, name)
    result = dict(accepted=False, completed=False, source_sha256=sources, protected_sha256=protected,
                  scope='Thirty live native raw-PDH/RAM/identity samples of the current candidate only; no sustained residency/frame acceptance or repeated functional journey.')
    try:
        session_path = ROOT / 'output/session.json'
        session = json.loads(session_path.read_text(encoding='utf-8-sig'))
        try:
            engine = psutil.Process(session['app'])
            live = engine.name().lower() == 'openspace.exe' and Path(engine.exe()).resolve().is_relative_to(ROOT)
        except psutil.NoSuchProcess:
            live = False
        if not live:
            opened = subprocess.run([sys.executable, '-Xutf8', str(ROOT / 'scripts/open-expanded-journey-app.py')], cwd=ROOT,
                                    capture_output=True, text=True, encoding='utf8', timeout=360)
            (folder / 'open.log').write_text(opened.stdout + opened.stderr, encoding='utf8')
            assert opened.returncode == 0
            session = json.loads(session_path.read_text(encoding='utf-8-sig'))
            engine = psutil.Process(session['app'])
        assert Path(session['serverScript']).resolve() == APP / 'server.py'
        server = psutil.Process(session['server'])
        assert any(Path(argument).resolve() == APP / 'server.py' for argument in server.cmdline() if 'server.py' in argument.lower())
        assert server.create_time() <= engine.create_time()
        result['session'] = session
        control = dict(schema=1, id='preflight', kind='prepare', window=None, recipe=None, expected_scenario=None)
        (folder / 'control.json').write_text(json.dumps(control) + '\n')
        label = 'pre-' + args.label
        with (folder / 'collector.log').open('xb') as stream:
            done = subprocess.run([sys.executable, '-Xutf8', str(ROOT / 'scripts/collect_expanded_residency_v4.py'),
                                   '--label', label, '--folder', str(folder), '--max-samples', '30'], cwd=ROOT,
                                  stdout=stream, stderr=subprocess.STDOUT, timeout=75)
        path = ROOT / f'evidence/is6-expanded-residency-collector-{label}.json'
        report = json.loads(path.read_text())
        assert done.returncode == 0 and report['valid'] and report['completed'] and report['samples'] == 30, report.get('failure')
        rows = [json.loads(line) for line in (folder / 'memory.jsonl').read_text().splitlines()]
        assert len(rows) == 30 and all(not row.get('failure') and not row['boundary'] for row in rows)
        metrics = [contract.gpu_row(row, session) for row in rows]
        lifecycle = contract.ledger(report['process_records'], rows, session)
        assert all(sha(ROOT / name) == seal for name, seal in {**sources, **protected}.items())
        assert json.loads(session_path.read_text(encoding='utf-8-sig')) == session
        result.update(accepted=True, completed=True, collector_receipt=path.relative_to(ROOT).as_posix(),
                      collector_sha256=sha(path), samples=30, lifecycle=lifecycle,
                      peak_GPU_GiB=max(row['GPU_bytes'] for row in metrics) / 2**30,
                      peak_RAM_GiB=max(row['RAM_bytes'] for row in metrics) / 2**30, owner_app_unchanged=True)
    except Exception:
        result['failure'] = traceback.format_exc()
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({key: value for key, value in result.items() if key not in ['source_sha256', 'protected_sha256', 'session']}, ensure_ascii=False), flush=True)
    return 0 if result['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
