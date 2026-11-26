"""Run both native compound journeys with real exits and restore the owner's view."""
import argparse
import datetime as dt
import hashlib
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path
import subprocess
import sys
import traceback

import psutil
from cef_page_v2 import Page
from is6_owned_profile_host import Host

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = 'output/is6-principal-moons-navigation-product0.25.1'
LAUNCHER = 'scripts/launch-is6-principal-moons-candidate-v2.py'
h = SourceFileLoader('moons_layers_cycle_helpers', str(ROOT/'scripts/benchmark-body-points-native.py')).load_module()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    parser.add_argument('--restart-label', required=True)
    args = parser.parse_args()
    for label in [args.label, args.restart_label]:
        if not label or len(label) > 20 or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label):
            parser.error('Invalid label')
    assert args.label != args.restart_label
    folder = ROOT/f'output/is6-moons-layers-native-cycle-{args.label}'
    out = ROOT/f'evidence/is6-moons-layers-native-cycle-{args.label}.json'
    if folder.exists() or out.exists():
        raise FileExistsError('Preserve compound journey cycle')
    folder.mkdir()
    r = dict(accepted=False, completed=False, candidate='0.25.1', steps=[],
             started_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
             script_sha256=sha(Path(__file__)),
             protected_sha256={name:sha(ROOT/name) for name in ['user/sessions/latest.json','Iniciar-Cosmos2.cmd']})
    original_id = None

    def persist():
        out.write_text(json.dumps(r, ensure_ascii=False, indent=2)+'\n', encoding='utf8')

    def open_app():
        number = len(list(folder.glob('open-*.log')))
        log = folder/f'open-{number}.log'
        with log.open('xb') as stream:
            done = subprocess.run([sys.executable, '-Xutf8', str(ROOT/'scripts/open-moons-app.py')],
                                  cwd=ROOT, stdin=subprocess.DEVNULL, stdout=stream,
                                  stderr=subprocess.STDOUT, timeout=360)
        assert done.returncode == 0, log.as_posix()
        r.setdefault('opens', []).append(dict(log=log.relative_to(ROOT).as_posix(), sha256=sha(log)))
        h._socket = None

    def close_current():
        session = json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
        assert Path(session['serverScript']).resolve() == ROOT/CANDIDATE/'app/server.py'
        wrapper = psutil.Process(session['launcher']).parent()
        assert any(LAUNCHER.split('/')[-1] in arg for arg in wrapper.cmdline())
        host = Host(folder, h, candidate=CANDIDATE, launcher=LAUNCHER)
        host.session, host.process = session, wrapper
        for role in ['app','server','launcher']:
            handle = host.kernel.OpenProcess(0x101000, False, session[role])
            if not handle:
                raise OSError('Cannot retain process handle: '+role)
            host.handles['engine' if role == 'app' else role] = handle
        processes = host.close()
        h._socket = None
        assert len(processes) == 4 and set(processes.values()) == {0}
        return session, processes

    persist()
    try:
        assert h.get('/api/state')['mode'] == 'atlas'
        r['original_navigation'] = h.get('/api/navigation/state')
        before = h.get('/api/navigation/favorites')['views']
        r['original_favorites'] = before
        saved = h.post('/api/navigation/save', dict(name='Camadas temporário · vista inicial'))['navigation']['views']
        original_id = next(x['id'] for x in saved if x['id'] not in {b['id'] for b in before})
        for phase, label in [('first', args.label), ('restart', args.restart_label)]:
            log = folder/(phase+'.log')
            with log.open('xb') as stream:
                done = subprocess.run([sys.executable, '-u', '-Xutf8', str(ROOT/'scripts/verify-native-is6-moons-layers.py'),
                    '--phase', phase, '--label', label, '--seed-label', args.label,
                    '--seed-process-label', args.label], cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
            native_path = ROOT/f'evidence/is6-moons-layers-native-{label}.json'
            native = json.loads(native_path.read_text()) if native_path.exists() else {}
            session, processes = close_current()
            process_path = ROOT/f'evidence/is6-moons-layers-native-process-{label}.json'
            assert not process_path.exists()
            process_report = dict(accepted=done.returncode == 0 and native.get('accepted') is True,
                                  completed=True, native_receipt=native_path.relative_to(ROOT).as_posix(),
                                  native_receipt_sha256=sha(native_path) if native_path.exists() else None,
                                  session=session, processes=processes, verification_exit=done.returncode,
                                  driver_sha256=sha(Path(__file__)))
            process_path.write_text(json.dumps(process_report, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
            r['steps'].append(dict(phase=phase, label=label, process_receipt=process_path.relative_to(ROOT).as_posix(),
                                  process_receipt_sha256=sha(process_path), accepted=process_report['accepted'],
                                  log=log.relative_to(ROOT).as_posix(), log_sha256=sha(log)))
            persist()
            open_app()
            restored = h.post('/api/navigation/restore', dict(id=original_id))['navigation']
            assert restored['et'] == r['original_navigation']['et']
            assert restored['navigation']['Anchor'] == r['original_navigation']['navigation']['Anchor']
            assert process_report['accepted'], native.get('failure', str(log))
            print(json.dumps(dict(phase=phase, accepted=True, captures=len(native['captures']), processes=processes)), flush=True)
        r.update(accepted=True, completed=True)
    except Exception:
        r['failure'] = traceback.format_exc()
    finally:
        try:
            open_app()
            if original_id:
                restored = h.post('/api/navigation/restore', dict(id=original_id))['navigation']
                h.post('/api/navigation/delete', dict(id=original_id))
                original_id = None
                assert restored['et'] == r['original_navigation']['et']
                assert restored['navigation']['Anchor'] == r['original_navigation']['navigation']['Anchor']
                with Page() as page:
                    page.wait_for_function('navigationState&&atlasState&&appState?.mode==="atlas"')
                    page.evaluate('selectTarget('+json.dumps(restored['target'])+',true)')
                    page.locator('#ui-scale').select_option('1')
            assert h.get('/api/navigation/favorites')['views'] == r['original_favorites']
            assert all(sha(ROOT/name) == seal for name,seal in r['protected_sha256'].items())
            assert len(h.get('/api/atlas/state')['bodies']) == 16
            r['owner_app_kept_open'] = True
            r['final_session'] = json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
        except Exception:
            r['cleanup_failure'] = traceback.format_exc()
            r['accepted'] = False
        persist()
    print(json.dumps(dict(accepted=r['accepted'], steps=r['steps'], failure=r.get('failure'),
                          cleanup_failure=r.get('cleanup_failure')), ensure_ascii=False), flush=True)
    return 0 if r['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
