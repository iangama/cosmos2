"""Preserve existing Cosmos2 state before the authorized ordinary-input journey."""
from pathlib import Path
import argparse
import datetime as dt
import hashlib
import json
import os
import shutil

import psutil

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    assert args.label and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
    folder = ROOT / ('output/original-flow-native-' + args.label)
    out = ROOT / ('evidence/original-flow-native-preflight-' + args.label + '.json')
    assert not folder.exists() and not out.exists(), 'Preserve previous attempts'
    processes = []
    for p in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
        try:
            row = p.info
            executable = (row['exe'] or '').replace('\\', '/').lower()
            server = any(str(arg).replace('\\', '/').lower().endswith('/app/server.py')
                         and 'cosmos2/' in str(arg).replace('\\', '/').lower() for arg in row['cmdline'] or [])
            if ('cosmos2/' in executable and (row['name'] or '').lower() == 'openspace.exe') or server:
                processes.append(row)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    assert not processes, 'Preserve the live session before starting another application: ' + str(processes)
    folder.mkdir()
    selected = set()
    for pattern in ['user/sessions/**/*', 'user/navigation/**/*', 'user/forces/**/*',
                    'output/is6-expanded-journey-product0.27.0/gravity-sessions/**/*',
                    'output/is6-expanded-journey-product0.27.0/navigation/**/*',
                    'output/is6-principal-moons-navigation-product0.25.1/navigation/**/*',
                    'output/is6-planet-navigation-product0.24.0/navigation/**/*',
                    'output/original-flow-hotfix-product0.27.1/gravity-sessions/**/*',
                    'output/original-flow-hotfix-product0.27.1/navigation/**/*',
                    'output/original-flow-hotfix-product0.27.1/spatial-checkpoints/**/*',
                    'output/original-flow-hotfix-product0.27.1/layer-checkpoints/**/*',
                    'output/original-flow-hotfix-product0.27.1/user/forces/**/*']:
        selected.update(p for p in ROOT.glob(pattern) if p.is_file())
    for name in ['output/session.json', 'output/engine.log', 'output/engine-errors.log',
                 'output/server.log', 'output/server-errors.log', 'output/bootstrap-ui.log',
                 'output/bootstrap-ui-errors.log', 'output/bootstrap-ui.json',
                 'config/cosmos2.cfg', 'config/window.json', '.runtime-built/cosmos2.cfg',
                 '.runtime-is4-stream/cosmos2.cfg', 'Iniciar-Cosmos2.cmd',
                 'Abrir-Planetas.cmd', 'Abrir-Planetas-e-Luas.cmd']:
        if (ROOT / name).is_file():
            selected.add(ROOT / name)
    rows = []
    for source in sorted(selected):
        relative = source.relative_to(ROOT)
        destination = folder / 'preserved-before' / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        digest = sha(source)
        shutil.copy2(source, destination)
        assert sha(source) == sha(destination) == digest
        rows.append(dict(source=relative.as_posix(), preserved=destination.relative_to(ROOT).as_posix(),
                         bytes=source.stat().st_size, sha256=digest))
    result = dict(accepted=True, completed=True, captured_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                  processes=processes, files=rows, script_sha256=sha(Path(__file__)),
                  authorization='Owner: Continue o que precisar, after the report that native validation was pending. Proceed with necessary functional validation; preserve state first. Final visual integration remains deferred.',
                  scope='Local preservation and process inspection only. No launch or UI input in this preflight.')
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps(dict(accepted=True, files=len(rows), bytes=sum(row['bytes'] for row in rows), processes=processes)))


if __name__ == '__main__':
    main()
