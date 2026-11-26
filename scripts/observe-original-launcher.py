"""Open an actual owner shortcut and record its native window, without candidate URLs."""
from pathlib import Path
import argparse
import datetime as dt
import hashlib
import json
import os
import time
import traceback

import psutil
from ordinary_native_input import NativeInput

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--shortcut', choices=['Iniciar-Cosmos2.cmd', 'Abrir-Planetas.cmd', 'Abrir-Planetas-e-Luas.cmd'], required=True)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    assert args.label and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
    folder = ROOT / ('output/original-flow-native-' + args.label)
    out = ROOT / ('evidence/original-flow-entry-' + args.label + '.json')
    assert folder.is_dir() and not out.exists(), 'Preserve preflight and previous observations'
    assert not [p for p in psutil.process_iter(['name']) if (p.info['name'] or '').lower() == 'openspace.exe']
    before = time.time()
    result = dict(completed=False, accepted=False, original_entry=args.shortcut,
                  started_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                  shortcut_sha256=hashlib.sha256((ROOT / args.shortcut).read_bytes()).hexdigest(),
                  observer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  input_method='Windows ShellExecute of the existing .cmd, then ordinary Windows input',
                  scope='Original-entry baseline observation only; no claim that the feature is corrected.')
    try:
        os.startfile(str(ROOT / args.shortcut))
        deadline = time.monotonic()+300
        session = None
        while time.monotonic() < deadline:
            try:
                candidate = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
                process = psutil.Process(candidate['app'])
                if process.name().lower() == 'openspace.exe' and process.create_time() >= before-1:
                    session = candidate
                    break
            except (OSError, ValueError, KeyError, psutil.NoSuchProcess):
                pass
            time.sleep(.1)
        assert session is not None, 'The shortcut did not publish a new application session'
        result['session'] = session
        while time.monotonic() < deadline:
            assert psutil.pid_exists(session['app']), 'The application exited while opening'
            log = ROOT / 'output/bootstrap-ui.json'
            if log.exists() and log.stat().st_mtime >= before:
                time.sleep(1)
                break
            time.sleep(.2)
        else:
            raise TimeoutError('The shortcut did not confirm its native interface')
        window = NativeInput(session['app'])
        capture = folder / ('original-' + Path(args.shortcut).stem + '.png')
        result['capture'] = window.capture(capture)
        result['capture']['sha256'] = hashlib.sha256(capture.read_bytes()).hexdigest()
        result['completed'] = True
        result['accepted'] = True
    except Exception:
        result['failure'] = traceback.format_exc()
    finally:
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps({key:result.get(key) for key in ['accepted', 'completed', 'session', 'capture', 'failure']}, ensure_ascii=False))
    return 0 if result['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
