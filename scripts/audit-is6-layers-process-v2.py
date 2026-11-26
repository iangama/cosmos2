"""Confirm normal pair-host exit, archived identity and unchanged owner session."""
from pathlib import Path
import argparse
import hashlib
import json
import psutil
import traceback

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--kind', choices=['native', 'profile'], required=True)
    parser.add_argument('--label', required=True)
    parser.add_argument('--host-label', required=True)
    args = parser.parse_args()
    for label in [args.label, args.host_label]:
        if not label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label):
            parser.error('Invalid label')
    prefix = 'is6-layers-native-' if args.kind == 'native' else 'is6-layers-profile-'
    source = ROOT / ('evidence/' + prefix + args.label + '.json')
    out = ROOT / ('evidence/is6-layers-' + args.kind + '-process-' + args.label + '.json')
    if out.exists():
        raise FileExistsError('Preserve process audit')
    record = json.loads(source.read_text())
    r = dict(accepted=False, completed=False, source_sha256={source.relative_to(ROOT).as_posix(): sha(source),
             Path(__file__).relative_to(ROOT).as_posix(): sha(Path(__file__))})
    try:
        assert record['completed'] and not record.get('failure') and not record.get('cleanup_failure')
        if args.kind == 'native':
            assert record['accepted']
        else:
            audit = ROOT / ('evidence/is6-layers-profile-audit-' + args.label + '.json')
            assert json.loads(audit.read_text())['accepted']
            r['source_sha256'][audit.relative_to(ROOT).as_posix()] = sha(audit)
        host = ROOT / ('output/is6-layers-host-' + args.host_label + '.log')
        lines = [json.loads(line) for line in host.read_text().splitlines() if line.startswith('{')]
        initial = next(v for v in lines if 'app' in v)
        assert initial['bootstrap_exit'] == 0 and lines[-1]['engine_exit'] == 0
        session_path = None
        for path in (ROOT / 'output/is6-layers-product0.19.1/execution-logs').glob('*/session.json'):
            session = json.loads(path.read_text(encoding='utf-8-sig'))
            if session['app'] == initial['app'] and session['server'] == initial['server']:
                session_path = path
                break
        assert session_path is not None
        session = json.loads(session_path.read_text(encoding='utf-8-sig'))
        process_path = session_path.with_name('process-result.json')
        process = json.loads(process_path.read_text())
        assert process == dict(app_exit=0, server_exit=0)
        alive = {k: psutil.pid_exists(session[k]) for k in ['app', 'server', 'launcher']}
        assert not any(alive.values()), alive
        remaining = []
        for p in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
            try:
                if p.info['name'].lower() == 'openspace.exe' and Path(p.info['exe']).is_relative_to(ROOT):
                    remaining.append(p.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, TypeError):
                continue
        assert not remaining, remaining
        assert sha(ROOT / 'user/sessions/latest.json') == record['owner_sha256']
        for p in [host, session_path, process_path]:
            r['source_sha256'][p.relative_to(ROOT).as_posix()] = sha(p)
        r.update(accepted=True, completed=True, session=session, process_result=process,
                 pids_alive=alive, remaining_project_engines=remaining,
                 owner_sha256=record['owner_sha256'], scope='Own pair host exit only; no product promotion or broader milestone acceptance.')
    except Exception:
        r['failure'] = traceback.format_exc()
    out.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({k: v for k, v in r.items() if k not in ['source_sha256', 'session']}, ensure_ascii=False))
    return 0 if r['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
