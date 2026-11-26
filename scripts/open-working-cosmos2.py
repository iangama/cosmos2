"""One owner entry point: preserve live sessions and open the selected local product."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import traceback

import psutil
from ordinary_native_input import NativeInput

ROOT = Path(__file__).resolve().parents[1]


def selection():
    value = json.loads((ROOT / 'config/local-working-product.json').read_text(encoding='utf8'))
    assert value['schema'] == 1
    product = (ROOT / value['product']).resolve()
    runtime = (ROOT / value['runtime']).resolve()
    assert product.is_relative_to(ROOT / 'output') and runtime.parent == ROOT and runtime.name.startswith('.runtime')
    manifest = json.loads((product / 'build-manifest.json').read_text(encoding='utf8'))
    assert manifest['candidate'] == value['candidate'] and manifest['scientific_python_unchanged'] == 137
    for name, digest in manifest['files_sha256'].items():
        path = (product / name).resolve()
        assert path.is_relative_to(product) and hashlib.sha256(path.read_bytes()).hexdigest() == digest, 'A versão local foi alterada: ' + name
    assert (runtime / 'bin/OpenSpace.exe').is_file()
    return value, product, runtime


def running():
    result = []
    for p in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            if (p.info['name'] or '').lower() == 'openspace.exe' and Path(p.info['exe']).is_relative_to(ROOT):
                result.append(p)
        except (psutil.NoSuchProcess, psutil.AccessDenied, TypeError):
            pass
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    value, product, runtime = selection()
    if args.check:
        print(json.dumps(dict(valid=True, candidate=value['candidate'], product=str(product), runtime=str(runtime))))
        return 0
    engines = running()
    if engines:
        assert len(engines) == 1, 'Há mais de uma sessão do Cosmos2. Preserve-as antes de continuar.'
        NativeInput(engines[0].pid).focus()
        current = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
        if Path(current['serverScript']).resolve() != product / 'app/server.py':
            print('A sessão atual foi preservada e ativada. Salve e feche essa janela para abrir a versão local atual.', flush=True)
            return 0
        print('Cosmos2 já está aberto. Sua sessão foi mantida.', flush=True)
        return 0
    stamp = str(time.time_ns())
    folder = ROOT / 'output/local-product-launches' / stamp
    folder.mkdir(parents=True)
    started = time.time()
    with (folder / 'launcher.log').open('xb') as log, (folder / 'launcher-errors.log').open('xb') as error:
        process = subprocess.Popen([sys.executable, '-u', '-Xutf8', str(ROOT / 'scripts/launch-working-cosmos2.py'), '--record', str(folder)],
                                   cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=error,
                                   creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
    deadline = time.monotonic()+300
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError('Não foi possível abrir o Cosmos2. Consulte '+str(folder / 'launcher-errors.log'))
        try:
            current = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
            engine = psutil.Process(current['app'])
            ready = ROOT / 'output/bootstrap-ui.json'
            if (current.get('localWorkingProduct') and Path(current['serverScript']).resolve() == product / 'app/server.py'
                    and engine.create_time() >= started-1 and ready.stat().st_mtime >= engine.create_time()):
                NativeInput(engine.pid).focus()
                print('Cosmos2 aberto: planetas, luas, forças, malha e camadas.', flush=True)
                return 0
        except (OSError, ValueError, KeyError, psutil.NoSuchProcess):
            pass
        time.sleep(.1)
    raise TimeoutError('A janela não confirmou a inicialização. Consulte '+str(folder))


if __name__ == '__main__':
    try:
        code = main()
    except Exception:
        log = ROOT / 'output' / ('local-product-open-error-' + str(time.time_ns()) + '.log')
        log.write_text(traceback.format_exc(), encoding='utf8')
        print('Não foi possível abrir o Cosmos2. A sessão existente foi preservada. Registro: '+str(log), file=sys.stderr, flush=True)
        code = 1
    raise SystemExit(code)
