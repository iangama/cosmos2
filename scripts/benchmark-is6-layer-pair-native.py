"""K2: native experimental spatial/magnetic pairs, static and 2 Hz visibility."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
import argparse
import copy
import datetime as dt
import hashlib
import json
import subprocess
import sys
import threading
import time
import traceback
import zipfile

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'output/is6-spatial-product0.18.5/app'
sys.path[:0] = [str(ROOT / 'output/is6-layer-coordination-staging'), str(APP)]
from cef_page import Page
from native_product_memory import product_memory
from is6_pair_profile_support import LIMITS, WINDOWS, COMBINATIONS
import is6_layer_scene_v3 as scene
import is6_layer_contract as contract
h = SourceFileLoader('pair_frame_helpers', str(ROOT / 'scripts/benchmark-body-points-native.py')).load_module()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
lock = threading.RLock()


def native(code):
    with lock:
        return h.native(code)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    parser.add_argument('--acceptance-label', default='20261103c')
    args = parser.parse_args()
    for label in [args.label, args.acceptance_label]:
        if not label or len(label) > 20 or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label):
            parser.error('Invalid label')
    folder = ROOT / ('output/is6-pair-profile-' + args.label)
    out = ROOT / ('evidence/is6-pair-profile-' + args.label + '.json')
    if folder.exists() or out.exists():
        raise FileExistsError('Preserve profile evidence')
    anchors = [ROOT / ('evidence/is6-native-layer-pair-' + args.acceptance_label + '.json'),
               ROOT / ('evidence/is6-layer-pair-visual-' + args.acceptance_label + '.json'),
               ROOT / ('evidence/is6-layer-pair-native-process-' + args.acceptance_label + '.json')]
    sources = {}
    for path in anchors:
        receipt = json.loads(path.read_text())
        assert receipt['accepted'], path
        sources.update(receipt['source_sha256'])
    files = [Path(__file__), Path(scene.__file__), ROOT / 'scripts/is6_pair_profile_support.py',
             ROOT / 'scripts/audit-is6-layer-pair-profile.py', ROOT / 'scripts/native_product_memory.py',
             ROOT / 'scripts/run-is6-pair-profile-background.py', ROOT / 'scripts/start-is6-spatial-background-v4.py',
             ROOT / 'scripts/launch-is6-spatial-revision-f.py', ROOT / 'config/window-1080.json', ROOT / 'config/cosmos2.cfg',
             ROOT / 'scripts/benchmark-body-points-native.py', ROOT / 'scripts/collect-is6-gpu-memory-scoped.ps1',
             ROOT / 'IS-6-COEXISTENCIA-PERFIL-K2-CONTRATO.md', *anchors]
    files += [p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    for path in files:
        sources[path.relative_to(ROOT).as_posix()] = sha(path)
    assert all(sha(ROOT / p) == seal for p, seal in sources.items())
    launch = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
    assert Path(launch['serverScript']).resolve() == (APP / 'server.py').resolve()
    folder.mkdir()
    archive = folder / 'executed-sources-and-inputs.zip'
    r = dict(completed=False, accepted=False, runs=[], inputs_before_execution=[], source_sha256=sources,
             session=launch, engine_sha256=sha(Path(launch['runtime']) / 'bin/OpenSpace.exe'),
             owner_sha256=sha(ROOT / 'user/sessions/latest.json'), limits_before_execution=LIMITS,
             warmup_s=30, window_s=60, page_errors=[], scene_files_before_execution=[],
             scope='K2 experimental pair rendering/visibility only; independent frozen models, no product UI, composite save, migration, solver throughput or promotion acceptance.')
    owner = gpu_job = producer = None
    stop = threading.Event()
    def persist():
        out.write_text(json.dumps(r, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')
    persist()
    try:
        with Page() as page:
            page.on('pageerror', lambda e: r['page_errors'].append(e))
            page.goto(h.test.BASE + '/')
            page.wait_for_function('appState&&atlasState&&!pending')
            assert h.get('/api/state')['mode'] == 'atlas'
            page.locator('#copy-solar').click()
            page.wait_for_function('appState.physics?.bodies.length===4&&!pending', timeout=70000)
            phase = h.get('/api/state')['physics']
            held = h.test.phase(copy.deepcopy(phase))
            r['source_phase'] = held
            owner = scene.Owner(native, phase)
            r['base_context'] = owner.context_now()
            page.locator('#ui-scale').select_option('1')
            page.evaluate('(()=>{const s=document.createElement("style");s.textContent="aside,#lab-details,#object-panel,#scene-targets{display:none!important}#pair-note{position:absolute;top:124px;left:28px;width:340px;padding:20px;pointer-events:auto;white-space:pre-line;font:13px/1.7 Segoe UI;color:#d9edf1}";document.head.append(s);const p=document.createElement("div");p.id="pair-note";p.className="glass";document.body.append(p);})()')
            page.evaluate('document.body.inert=true')
            inputs = []
            for index, (target, kind) in enumerate(WINDOWS, 1):
                b = next(b for b in phase['bodies'] if b['reference_id'] == 'sol:naif:' + target)
                run = contract.artifact.Run.create(phase, dict(body_id=b['id'], source_guard=contract.artifact.body.guard(phase)),
                    {**contract.artifact.DEFAULT_CONFIGURATION, 'outer_radius_boundary_units': 3.})
                reading = (contract.earth_magnetism.read(phase, b['id'], -23.55, -46.63, 1000.) if target == '399'
                           else contract.jupiter_magnetism.read(phase, b['id'], 1.5*71492000., 0., 0., 13))
                recipe = [dict(tick=tick, offset_s=tick*.5, visible=COMBINATIONS[tick % 4]) for tick in range(120)] if kind == 'visibility' else []
                data = dict(body=target, kind=kind, artifact=run.payload, reading=reading, recipe=recipe,
                            plan=contract.compose(phase, run.payload, reading, dict(spatial=True, magnetic=True)))
                path = folder / ('input-' + str(index) + '.json')
                path.write_text(json.dumps(data, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf8')
                r['inputs_before_execution'].append(dict(run=index, path=path.relative_to(ROOT).as_posix(), sha256=sha(path)))
                inputs.append((run, reading, recipe))
            with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
                for p in sources:
                    z.write(ROOT / p, p)
                for item in r['inputs_before_execution']:
                    z.write(ROOT / item['path'], item['path'])
            r['archive_sha256'] = sha(archive)
            persist()
            for index, ((target, kind), (run, reading, recipe)) in enumerate(zip(WINDOWS, inputs), 1):
                pair = owner.prepare(run, reading, folder / ('mesh-' + str(index)))
                owner.commit(pair, dict(spatial=True, magnetic=True))
                assert not owner.error
                initial = pair.read()
                context = owner.context_now()
                note = ('Protótipo de camadas independentes\n' + reading['provenance']['model']
                        + '\nÉpoca: ' + reading['epoch']['utc']
                        + '\nMalha exterior: 1–3 Rref · altura gráfica ×200'
                        + '\nCiano/violeta: corte de Schwarzschild\nVerde: B em tesla · seta de tamanho gráfico'
                        + '\nOuro: ponto da amostra\nPosições: metros · referencial GALACTIC'
                        + '\nModelos sem acoplamento GR–EM\nAmostra B não se limita ao domínio exterior da malha.')
                page.evaluate('document.getElementById("pair-note").textContent=' + json.dumps(note)
                              + ';document.getElementById("notice").textContent="Protótipo nativo · mesma fase orbital pausada"')
                scene_files = list(pair.spatial.folder.iterdir())
                for m in pair.magnetic.render['meshes']:
                    scene_files += [Path(m['file']), Path(m['names_file'])]
                scene_files += [Path(pair.magnetic.render['receipt'])]
                seals = {p.relative_to(ROOT).as_posix(): sha(p) for p in scene_files}
                with zipfile.ZipFile(archive, 'a', zipfile.ZIP_DEFLATED) as z:
                    for p in scene_files:
                        z.write(p, p.relative_to(ROOT).as_posix())
                r['scene_files_before_execution'].append(dict(run=index, sha256=seals))
                r['archive_sha256'] = sha(archive)
                persist()
                print(json.dumps(dict(stage='warmup', run=index, body=target, kind=kind, seconds=30)), flush=True)
                time.sleep(30)
                label = 'is6-pair-' + args.label + '-' + str(index)
                ready = ROOT / ('output/gpu-memory-ready-' + label + '.json')
                gpu_path = ROOT / ('evidence/gpu-memory-' + label + '.json')
                if ready.exists() or gpu_path.exists():
                    raise FileExistsError('Preserve GPU evidence')
                gpu_job = subprocess.Popen(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                    str(ROOT / 'scripts/collect-is6-gpu-memory-scoped.ps1'), '-Label', label, '-Samples', '66',
                    '-ExpectedMode', 'experiment', '-ExpectedWorker', 'paused', '-SignalReady'],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf8', errors='replace')
                until = time.monotonic()+30
                while not ready.exists():
                    if gpu_job.poll() is not None:
                        raise RuntimeError(gpu_job.communicate()[0])
                    if time.monotonic() > until:
                        raise TimeoutError('GPU readiness')
                    time.sleep(.05)
                signal = json.loads(ready.read_text(encoding='utf-8-sig'))
                assert signal['engine_pid'] == launch['app']
                row = dict(run=index, body=target, kind=kind, input=r['inputs_before_execution'][index-1],
                           initial=initial, context=context, samples=[], commands=[], producer_errors=[],
                           plan=pair.plan, spatial_scene=pair.spatial.prepared, magnetic_scene=pair.magnetic.prepared)
                r['pending_run'] = row
                persist()
                native('openspace.cosmos2BeginFrameCapture(12000);return {ready=true}')
                row['capture_start_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
                began = time.perf_counter()
                def produce():
                    try:
                        for item in recipe:
                            if stop.wait(max(0, began+item['offset_s']-time.perf_counter())):
                                return
                            entered = time.perf_counter()
                            with lock:
                                readback = owner.visibility(item['visible'])
                            finished = time.perf_counter()
                            row['commands'].append(dict(tick=item['tick'], visible=item['visible'], readback=readback,
                                started_offset_s=entered-began, finished_offset_s=finished-began, elapsed_s=finished-entered))
                    except Exception:
                        row['producer_errors'].append(traceback.format_exc())
                producer = threading.Thread(target=produce, daemon=True)
                producer.start()
                print(json.dumps(dict(stage='capture', run=index, body=target, kind=kind)), flush=True)
                for part in range(4):
                    remaining = began+part*20-time.perf_counter()
                    if remaining > 0:
                        time.sleep(remaining)
                    with lock:
                        readback = pair.read()
                        current_context = owner.context_now()
                    physics = h.get('/api/state')['physics']
                    assert h.test.phase(physics) == held
                    row['samples'].append(dict(offset_s=time.perf_counter()-began, source_phase=h.test.phase(physics),
                        paused=physics['paused'], readback=readback, context=current_context, ram=product_memory(launch),
                        engine_gpu=native('return openspace.cosmos2MemoryMetrics()')))
                row.update(capture=native('return openspace.cosmos2EndFrameCapture()'),
                           capture_end_utc=dt.datetime.now(dt.timezone.utc).isoformat(), wall_interval_s=time.perf_counter()-began,
                           final=pair.read())
                producer.join(timeout=2)
                assert not producer.is_alive() and not row['producer_errors']
                producer = None
                persist()
                output = gpu_job.communicate(timeout=30)[0]
                (folder / ('gpu-' + str(index) + '.log')).write_text(output, encoding='utf8')
                assert gpu_job.returncode == 0, output
                gpu_job = None
                row.update(gpu_report=gpu_path.relative_to(ROOT).as_posix(), gpu_sha256=sha(gpu_path))
                r['runs'].append(row)
                r.pop('pending_run')
                owner.close()
                r['runs'][-1]['context_after_cleanup'] = owner.context_now()
                nodes = [pair.spatial.frame, pair.spatial.wire, pair.spatial.focus, *pair.magnetic.nodes]
                r['runs'][-1]['nodes_after_cleanup'] = native('local r={};for _,n in ipairs(' + scene.lua(nodes) + ') do r[n]=openspace.hasSceneGraphNode(n) end;return r')
                assert not any(r['runs'][-1]['nodes_after_cleanup'].values())
                persist()
            page.evaluate('document.body.inert=false')
            h.post('/api/command', dict(command='atlas'))
            r['completed'] = True
    except Exception:
        r['failure'] = traceback.format_exc()
    finally:
        stop.set()
        if producer:
            producer.join(timeout=5)
        if gpu_job:
            try:
                (folder / 'interrupted-gpu.log').write_text(gpu_job.communicate(timeout=60)[0], encoding='utf8')
            except subprocess.TimeoutExpired:
                gpu_job.terminate()
                gpu_job.communicate(timeout=5)
        try:
            if owner:
                owner.close()
            with Page() as page:
                page.evaluate('document.body.inert=false')
            if h.get('/api/state')['mode'] == 'experiment':
                h.post('/api/command', dict(command='atlas'))
            native('openspace.toggleShutdown();return {closing=true}')
            assert sha(ROOT / 'user/sessions/latest.json') == r['owner_sha256']
            assert all(sha(ROOT / p) == seal for p, seal in sources.items())
        except Exception:
            r['cleanup_failure'] = traceback.format_exc()
            r['completed'] = False
        persist()
        if h._socket:
            h._socket.close()
    print(json.dumps(dict(completed=r['completed'], runs=len(r['runs']), failure=r.get('failure', '').splitlines()[-1:])), flush=True)
    return 0 if r['completed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
