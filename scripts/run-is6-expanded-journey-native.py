"""Own four native process handles, run the isolated journey, close normally and reopen the view."""
import argparse
import datetime as dt
import hashlib
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path
import subprocess
import sys
import traceback

from is6_owned_profile_host import Host
from cef_page_v2 import Page

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = 'output/is6-expanded-journey-product0.27.0'
LAUNCHER = 'scripts/launch-is6-expanded-journey-candidate.py'
h = SourceFileLoader('expanded_native_host_helpers', str(ROOT / 'scripts/benchmark-body-points-native.py')).load_module()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    parser.add_argument('--service-label', required=True)
    args = parser.parse_args()
    for label in [args.label, args.service_label]:
        assert label and len(label) <= 24 and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label)
    folder = ROOT / f'output/is6-expanded-journey-native-host-{args.label}'
    out = ROOT / f'evidence/is6-expanded-journey-native-host-{args.label}.json'
    assert not folder.exists() and not out.exists()
    folder.mkdir()
    result = dict(accepted=False, completed=False, started_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                  script_sha256=sha(Path(__file__)), launcher_sha256=sha(ROOT / LAUNCHER),
                  verifier_sha256=sha(ROOT / 'scripts/verify-native-is6-expanded-journey.py'))
    host = Host(folder, h, candidate=CANDIDATE, launcher=LAUNCHER)
    original_id = None
    def persist():
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    persist()
    try:
        result['session'] = host.start()
        result['original_navigation'] = h.get('/api/navigation/state')
        result['original_favorites'] = h.get('/api/navigation/favorites')['views']
        saved = h.post('/api/navigation/save', dict(name='Retorno do host ampliado'))['navigation']['views']
        original_id = next(v['id'] for v in saved if v['id'] not in {a['id'] for a in result['original_favorites']})
        result['temporary_favorite'] = original_id
        persist()
        with (folder / 'journey.log').open('xb') as stream:
            child = subprocess.run([sys.executable, '-u', '-Xutf8', str(ROOT / 'scripts/verify-native-is6-expanded-journey.py'),
                                    '--label', args.label, '--service-label', args.service_label], cwd=ROOT,
                                   stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT)
        path = ROOT / f'evidence/is6-expanded-journey-native-{args.label}.json'
        proof = json.loads(path.read_text()) if path.exists() else {}
        result.update(journey_exit=child.returncode, journey_accepted=proof.get('accepted') is True,
                      journey_receipt_sha256=sha(path) if path.exists() else None)
        result['processes'] = host.close()
        h._socket = None
        assert len(result['processes']) == 4 and set(result['processes'].values()) == {0}
        assert child.returncode == 0 and proof.get('accepted') is True, proof.get('failure')
        result.update(accepted=True, completed=True)
    except Exception:
        result['failure'] = traceback.format_exc()
    finally:
        try:
            if host.handles:
                result['cleanup_processes'] = host.close()
                h._socket = None
            with (folder / 'reopen.log').open('xb') as stream:
                opened = subprocess.run([sys.executable, '-Xutf8', str(ROOT / 'scripts/open-expanded-journey-app.py')],
                                        cwd=ROOT, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, timeout=360)
            assert opened.returncode == 0
            h._socket = None
            if original_id:
                restored = h.post('/api/navigation/restore', dict(id=original_id))['navigation']
                h.post('/api/navigation/delete', dict(id=original_id))
                assert restored['et'] == result['original_navigation']['et']
                assert h.get('/api/navigation/favorites')['views'] == result['original_favorites']
                with Page() as page:
                    page.wait_for_function('appState?.mode==="atlas"&&navigationState&&!pending')
                    page.locator('#ui-scale').select_option('1')
                    page.evaluate('selectTarget(' + json.dumps(restored['target']) + ',true)')
            result['owner_app_kept_open'] = True
            result['final_session'] = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
        except Exception:
            result['cleanup_failure'] = traceback.format_exc()
            result['accepted'] = False
        persist()
    print(json.dumps(dict(accepted=result['accepted'], processes=result.get('processes'),
                         journey_exit=result.get('journey_exit'), failure=result.get('failure'),
                         cleanup_failure=result.get('cleanup_failure'))), flush=True)
    return 0 if result['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
