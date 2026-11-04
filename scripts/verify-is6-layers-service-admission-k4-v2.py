"""CPU-only K3 admission boundaries; real magnetic models, no fake native acceptance."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import sys
import threading
import traceback
import zipfile

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / 'output/is6-layers-product-staging-k4'
IO_STAGE = ROOT / 'output/is6-layers-persistence-staging'
APP = ROOT / 'output/is6-layers-product0.19.1/app'
sys.path[:0] = [str(STAGE), str(IO_STAGE), str(APP)]
import is6_layers_laboratory as service
import is6_layer_contract as contract
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('Invalid label')
    out = ROOT / ('evidence/is6-layers-service-admission-' + args.label + '.json')
    folder = ROOT / ('output/is6-layers-service-admission-' + args.label)
    if out.exists() or folder.exists():
        raise FileExistsError('Preserve admission evidence')
    anchor = ROOT / 'evidence/is6-native-layer-pair-20261103c.json'
    accepted = json.loads(anchor.read_text())
    assert accepted['accepted'] and accepted['completed']
    hashes = dict(accepted['source_sha256'])
    for p in [*STAGE.glob('*.py'), *[IO_STAGE/n for n in ['is6_layers_checkpoint_v2.py','is6_layers_store.py','is6_layers_saved_scene.py']], ROOT/'IS-6-COEXISTENCIA-PERSISTENCIA-K4-REVISAO-B.md', Path(__file__), ROOT / 'IS-6-COEXISTENCIA-PRODUTO-K3-CONTRATO.md', anchor]:
        hashes[p.relative_to(ROOT).as_posix()] = sha(p)
    assert all(sha(ROOT / p) == seal for p, seal in hashes.items())
    folder.mkdir()
    with zipfile.ZipFile(folder / 'executed-sources.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        for p in hashes:
            z.write(ROOT / p, p)
    phase = accepted['source_phase']
    state = dict(mode='experiment', physics=copy.deepcopy(phase))
    class Laboratory:
        gate = entered = None
        def status(self):
            if self.gate is not None:
                self.entered.set()
                if not self.gate.wait(5):
                    raise TimeoutError('Admission test gate')
            return copy.deepcopy(state)
    calls = []
    def no_native(code):
        calls.append(code)
        raise AssertionError('Negative admission must not reach native transport')
    laboratory = Laboratory()
    actor = service.LayerLaboratory(laboratory, storage=folder / 'previews', native=no_native)
    r = dict(accepted=False, completed=False, source_sha256=hashes, refusals=[], magnetic_models=[],
             owner_sha256=sha(ROOT / 'user/sessions/latest.json'),
             scope='CPU input and actor admission only. Laboratory.status is a frozen source adapter; real IGRF/JRM33 recomputed. No simulated native success, UI, scene, cancellation-cleanup or performance acceptance.')
    def refuse(name, request):
        before = actor.status()
        try:
            actor.command(request)
        except ValueError as error:
            r['refusals'].append(dict(name=name, error=str(error)))
        else:
            raise AssertionError('Invalid command accepted: ' + name)
        after = actor.status()
        assert after['guard'] == before['guard'] and not after['active'] and not after['recovery_required'] and not after['busy']
        assert not calls
    try:
        earth = next(b for b in phase['bodies'] if b['reference_id'] == 'sol:naif:399')
        jupiter = next(b for b in phase['bodies'] if b['reference_id'] == 'sol:naif:599')
        coordinates = dict(model='IGRF14', latitude_deg=-23.55, longitude_deg=-46.63, altitude_m=1000.)
        base = dict(command='create', guard=actor.status()['guard'], source_guard=contract.artifact.body.guard(phase),
            body_id=earth['id'], configuration={**contract.artifact.DEFAULT_CONFIGURATION, 'outer_radius_boundary_units': 3.}, magnetic=coordinates)
        for name, request in [('non-object', None), ('internal-close', dict(command='_close')),
                              ('command-list', dict(command=[], guard=base['guard'])),
                              ('unknown-command', dict(command='save', guard=base['guard'])),
                              ('missing-guard', {k:v for k,v in base.items() if k != 'guard'}),
                              ('no-saved-file', dict(command='load_saved', guard=base['guard'], source_guard=base['source_guard'])),
                              ('saved-missing-source-guard', dict(command='load_saved', guard=base['guard'])),
                              ('no-active-load', dict(command='load',guard=base['guard'])),
                              ('no-active-branch-load', dict(command='branch_load',guard=base['guard'],branch_id='../latest')),
                              ('no-active-export', dict(command='export',guard=base['guard'])),
                              ('extra-field', {**base, 'unexpected': 1}),
                              ('stale-guard', {**base, 'guard': {**base['guard'], 'revision': -1}}),
                              ('boolean-revision', {**base, 'guard': {**base['guard'], 'revision': False}}),
                              ('no-active-visibility', dict(command='set_visibility', guard=base['guard'], visible=dict(spatial=True, magnetic=True))),
                              ('no-active-artifact', dict(command='get_artifact', guard=base['guard']))]:
            refuse(name, request)
        for key, value in [('revision', False), ('time', False), ('time', float('nan')), ('frame', 'J2000')]:
            refuse('source-' + key + '-' + str(value), {**base, 'source_guard': {**base['source_guard'], key: value}})
        for key, value in [('radial_count', 257), ('vertical_amplification', 201), ('outer_radius_boundary_units', 8.)]:
            refuse('unprofiled-' + key, {**base, 'configuration': {**base['configuration'], key: value}})
        for key in ['latitude_deg', 'longitude_deg', 'altitude_m']:
            for value in [False, float('nan'), float('inf'), '0']:
                refuse('magnetic-' + key + '-' + str(value), {**base, 'magnetic': {**coordinates, key: value}})
        refuse('wrong-model', {**base, 'magnetic': {**coordinates, 'model': 'JRM33'}})
        refuse('unknown-body', {**base, 'body_id': 'missing'})
        refuse('unsupported-body', {**base, 'body_id': phase['bodies'][0]['id']})
        refuse('magnetic-extra', {**base, 'magnetic': {**coordinates, 'extra': 1}})
        for key in ['body_field_preview', 'fields_preview', 'orbit_preview', 'instruments_preview', 'probe_preview']:
            state[key] = dict(active=True)
            refuse('old-preview-' + key, base)
            state.pop(key)
        state['physics']['paused'] = False
        refuse('source-running', base)
        state['physics']['paused'] = True
        for b, settings in [(earth, coordinates), (jupiter, dict(model='JRM33', radius_m=1.5*71492000., latitude_deg=0., longitude_east_deg=0., degree=13))]:
            reading = service.magnetic_reading(phase, b['id'], settings)
            assert contract.magnetic(phase, reading) == reading
            r['magnetic_models'].append(dict(body=b['reference_id'], reading_sha256=contract.digest(reading)))
        for degree in [True, 13., 18, 0]:
            settings = dict(model='JRM33', radius_m=1.5*71492000., latitude_deg=0., longitude_east_deg=0., degree=degree)
            refuse('jovian-degree-' + str(degree), {**base, 'body_id': jupiter['id'], 'magnetic': settings})
        laboratory.gate, laboratory.entered = threading.Event(), threading.Event()
        first_errors = []
        def first():
            try:
                actor.command({**base, 'body_id': 'missing'})
            except ValueError as error:
                first_errors.append(str(error))
        thread = threading.Thread(target=first)
        thread.start()
        assert laboratory.entered.wait(2) and actor.status()['busy']
        try:
            actor.command(dict(command='get_artifact', guard=base['guard']))
        except ValueError as error:
            r['refusals'].append(dict(name='concurrent-actor-admission', error=str(error)))
        else:
            raise AssertionError('Concurrent actor command admitted')
        laboratory.gate.set()
        thread.join(timeout=3)
        assert not thread.is_alive() and len(first_errors) == 1 and not calls
        laboratory.gate = None
        assert state['physics'] == phase and sha(ROOT / 'user/sessions/latest.json') == r['owner_sha256']
        assert all(sha(ROOT / p) == seal for p, seal in hashes.items())
        r.update(accepted=True, completed=True, native_calls=len(calls), concurrent_request_refused=True)
    except Exception:
        r['failure'] = traceback.format_exc()
    finally:
        actor.close()
    out.write_text(json.dumps(r, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')
    print(json.dumps(dict(accepted=r['accepted'], refusals=len(r['refusals']), models=len(r['magnetic_models']), failure=r.get('failure', '').splitlines()[-1:])))
    return 0 if r['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
