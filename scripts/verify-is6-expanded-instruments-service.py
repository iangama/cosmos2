"""Real orbital/particle/nuclear workers and real layer stores; no renderer success adapter."""
import argparse
import copy
import datetime as dt
import hashlib
import json
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import threading
import time
import traceback
import zipfile

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'output/is6-expanded-journey-product0.27.0/app'
sys.path.insert(0, str(APP))
import system16_import
import solar_import
import solar_catalog
from is4_client import Client as ParticleClient
from is4_laboratory import ParticleLaboratory
from is4_product_store import Store as ParticleStore
from is5_compression_client import Client as SolarClient
import is6_layers_laboratory as layers
from is6_layers_import_store_v2 import Store as LayerStore

sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
contract = layers.contract
artifact = contract.artifact


def orbital_guard(p):
    return {k: p[k] for k in ['system_id', 'edit_token', 'revision']} | dict(
        expected_time=p['time'], frame=p['contract']['frame'])


def physical(p):
    return {k: copy.deepcopy(p[k]) for k in [
        'system_id', 'edit_token', 'revision', 'time', 'bodies', 'atlas_initial',
        'interventions', 'dynamics16', 'paused', 'contract', 'physical_scale']}


class OrbitalWorker:
    def __init__(self, storage):
        storage.mkdir(parents=True)
        self.errors = (storage / 'stderr.log').open('w', encoding='utf8')
        self.process = subprocess.Popen(
            [sys.executable, '-Xutf8', '-u', str(APP / 'worker.py'), '--storage', str(storage)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.errors,
            text=True, encoding='utf8')
        self.events, self.serial = queue.Queue(), 0
        def reader():
            try:
                for line in self.process.stdout:
                    self.events.put(json.loads(line))
            finally:
                self.events.put(dict(type='eof'))
        self.thread = threading.Thread(target=reader, daemon=True)
        self.thread.start()
        assert self.events.get(timeout=30)['type'] == 'ready'
        self.latest = self.events.get(timeout=30)
        assert self.latest['type'] == 'snapshot'

    def call(self, command_name, *, expect_error=False, **fields):
        self.serial += 1
        self.process.stdin.write(json.dumps(dict(
            command=command_name, id=self.serial, **fields), allow_nan=False) + '\n')
        self.process.stdin.flush()
        deadline = time.monotonic() + 40
        while True:
            result = self.events.get(timeout=max(.001, deadline - time.monotonic()))
            assert result['type'] != 'eof', result
            if result['type'] == 'snapshot':
                self.latest = result
            if result.get('id') == self.serial and result['type'] in ['ack', 'error']:
                assert (result['type'] == 'error') == expect_error, result
                return result

    def close(self):
        if self.process.poll() is None:
            self.call('quit')
        self.process.wait(timeout=10)
        self.errors.close()
        self.thread.join(timeout=2)
        self.process.stdin.close()
        self.process.stdout.close()
        assert self.process.returncode == 0


class SourceAdapter:
    """Read the current real-worker phase; only the absent native preview is adapted."""
    def __init__(self, orbital):
        self.orbital, self.reading = orbital, None

    def status(self):
        return dict(mode='experiment', physics=copy.deepcopy(self.orbital.latest),
                    body_field_preview=None if self.reading is None else dict(reading=copy.deepcopy(self.reading)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    assert args.label and len(args.label) <= 24 and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
    folder = ROOT / f'output/is6-expanded-instruments-service-{args.label}'
    receipt = ROOT / f'evidence/is6-expanded-instruments-service-{args.label}.json'
    assert not folder.exists() and not receipt.exists(), 'Preserve service evidence'
    manifest_path = APP.parent / 'build-manifest.json'
    manifest = json.loads(manifest_path.read_text())
    inventory_path = APP.parent / 'journey-inventory.json'
    assert sha(inventory_path) == manifest['journey_inventory_sha256']
    assert manifest['candidate'] == '0.27.0' and manifest['changed'] == [] and not manifest['promoted']
    assert {p.relative_to(APP).as_posix(): sha(p) for p in APP.rglob('*')
            if p.is_file() and '__pycache__' not in p.parts} == manifest['files_sha256']
    gates = [ROOT / 'evidence' / name for name in [
        'is6-expanded-journey-service-20261112b.json', 'is6-expanded-journey-http-20261112b.json']]
    assert all(json.loads(p.read_text())['accepted'] for p in gates)
    inventory = json.loads(inventory_path.read_text())
    recipe = copy.deepcopy(inventory['legacy_recipe'])
    recipe.update(utc='2026-10-11T12:00:00Z', particle_pitch_deg=60., particle_steps_per_command=64,
                  spatial_configuration=copy.deepcopy(artifact.DEFAULT_CONFIGURATION),
                  layer_configuration={**artifact.DEFAULT_CONFIGURATION, 'outer_radius_boundary_units': 3.},
                  layer_visibilities=[dict(spatial=a, magnetic=b) for a, b in [(True, True), (False, True), (True, False), (False, False)]])
    protected = {n: sha(ROOT / n) for n in [
        'user/sessions/latest.json', 'output/session.json', 'Abrir-Dinamica16.cmd',
        'Abrir-Planetas-e-Luas.cmd', 'Iniciar-Cosmos2.cmd', 'user/navigation/favorites.json'] if (ROOT / n).is_file()}
    sources = dict(manifest['source_sha256'])
    paths = [p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    paths += [Path(__file__), inventory_path, manifest_path, *gates,
              ROOT / 'IS-6-PERCURSO-AMPLIADO16-INSTRUMENTOS-CONTRATO.md']
    for module in tuple(sys.modules.values()):
        name = getattr(module, '__file__', None)
        if name:
            p = Path(name).resolve()
            if p.is_relative_to(ROOT) and p.suffix == '.py' and '.tooling' not in p.parts:
                paths.append(p)
    for path in paths:
        sources[path.relative_to(ROOT).as_posix()] = sha(path)
    assert all(sha(ROOT / n) == seal for n, seal in sources.items())
    folder.mkdir()
    (folder / 'recipe-before-execution.json').write_text(json.dumps(recipe, indent=2, allow_nan=False) + '\n')
    with zipfile.ZipFile(folder / 'executed-sources.zip', 'x', zipfile.ZIP_DEFLATED) as archive:
        for name in sources:
            archive.write(ROOT / name, name)
        archive.write(folder / 'recipe-before-execution.json', 'recipe-before-execution.json')
    report = dict(accepted=False, completed=False, candidate='0.27.0',
                  started_utc=dt.datetime.now(dt.timezone.utc).isoformat(), source_sha256=sources,
                  source_archive_sha256=sha(folder / 'executed-sources.zip'), protected_sha256=protected,
                  recipe_before_execution=recipe, steps=[], refusals=[], processes=[],
                  scope='Actual orbital, particle and Windows nuclear workers; actual magnetic/spatial science and layer stores. A source-status adapter supplies the real frozen orbital phase to particle parameter admission. No renderer success simulation. Layer actor/native scene, HTTP integration, UI, captures and performance remain separate.')
    def persist():
        receipt.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')
    def passed(name, **fields):
        report['steps'].append(dict(name=name, **fields))
        persist()
        print(json.dumps(dict(progress=name), ensure_ascii=False), flush=True)
    def close_client(client, kind):
        pid = client.process.pid
        client.close()
        assert client.process.returncode == 0
        report['processes'].append(dict(kind=kind, pid=pid, exit=0))
    def refuse(name, call, state=None):
        before = None if state is None else copy.deepcopy(state())
        try:
            call()
        except (ValueError, TypeError, KeyError) as error:
            report['refusals'].append(dict(name=name, error=str(error)))
        else:
            raise AssertionError('Invalid operation accepted: ' + name)
        if state is not None:
            assert state() == before, name
        persist()
    def particle_science(client):
        return client.snapshot()['experiment']
    orbital = particle = solar = None
    persist()
    try:
        sixteen = system16_import.prepare(system16_import.catalog.states(utc=recipe['utc']))
        four = solar_import.prepare(solar_catalog.states(recipe['utc']))
        assert sixteen['source']['epoch']['et_tdb_s'] == four['source']['epoch']['et_tdb_s']
        orbital = OrbitalWorker(folder / 'orbital-worker')
        orbital.call('import_atlas', initial_state=sixteen)
        initial16 = copy.deepcopy(orbital.latest)
        orbital.call('save')
        saved16 = folder / 'saved-sixteen'
        shutil.copytree(folder / 'orbital-worker', saved16)
        orbital.call('import_atlas', initial_state=four)
        phase = copy.deepcopy(orbital.latest)
        assert phase['paused'] and len(phase['bodies']) == 4 and phase['system_id'] != initial16['system_id']
        common = physical(phase)
        report['source_phase16'], report['common_source_phase4'] = initial16, phase
        source = SourceAdapter(orbital)
        initial_admission = ParticleLaboratory.__new__(ParticleLaboratory)
        initial_admission.lab = source
        def same_phase():
            orbital.call('snapshot')
            assert physical(orbital.latest) == common
        passed('Two origins at one epoch; four-center common phase paused')
        for naif, species in recipe['body_cases']:
            body = next(b for b in phase['bodies'] if b['reference_id'] == 'sol:naif:' + naif)
            point = recipe['magnetic_points'][naif]
            magnetic = (dict(model='IGRF14', latitude_deg=point['latitude'], longitude_deg=point['longitude'], altitude_m=point['altitude'])
                        if naif == '399' else dict(model='JRM33', radius_m=point['radius'], latitude_deg=point['latitude'],
                                                 longitude_east_deg=point['longitude'], degree=recipe['jovian_degree']))
            reading = layers.magnetic_reading(phase, body['id'], magnetic)
            assert contract.magnetic(phase, reading) == reading
            source.reading = reading
            request = dict(source_guard=artifact.body.guard(phase), species=species,
                           speed_m_s=recipe['particle_speeds_m_s'][species], pitch_deg=recipe['particle_pitch_deg'])
            p, r, parameters, unit, field = initial_admission._initial(request)
            assert p == phase and r == reading
            particle_folder = folder / ('particle-' + naif)
            particle = ParticleClient(particle_folder / 'worker')
            particle.call('create', dict(source_phase=p, source_reading=r, parameters=parameters,
                                         controls=dict(electric=True, magnetic=True, gravity=True)))
            first_guard = particle.guard(particle.snapshot())
            for _ in range(recipe['particle_steps']):
                particle.call('advance', dict(steps=recipe['particle_steps_per_command']))
            particle.call('sample')
            saved_phase = copy.deepcopy(particle.snapshot()['experiment']['phase'])
            particle.call('save')
            particle_record = json.loads((particle_folder / 'worker/latest.json').read_text())
            assert particle_record['source_phase'] == phase and particle_record['source_reading'] == reading
            store = ParticleStore(particle_folder / 'checkpoints')
            refuse('Orbital manifest is not particle checkpoint ' + naif,
                   lambda: store._validate(json.loads((saved16 / 'latest.json').read_text())))
            store.save(particle_record, dict(physical_unit_m=unit, visible=True))
            root_branch = store.save(particle_record, dict(physical_unit_m=unit, visible=True), name='Origem ' + species)
            child_branch = store.save(particle_record, dict(physical_unit_m=unit, visible=False), name='Filho ' + species, parent=root_branch['branch']['id'])
            loaded_child, _ = store.load(child_branch['branch']['id'])
            assert loaded_child['particle'] == particle_record and not loaded_child['view']['visible']
            assert loaded_child['branch']['parent'] == root_branch['branch']['id'] and all(row['valid'] for row in store.catalog())
            refuse('Particle stale microtime ' + naif, lambda: particle.call('advance', dict(steps=64), guard=first_guard), lambda: particle_science(particle))
            particle.call('advance', dict(steps=64))
            future = particle.call('export_payload')['result']
            view, _ = store.restore_to(particle_folder / 'worker')
            particle.call('load')
            assert particle.snapshot()['experiment']['phase'] == saved_phase and view['visible']
            prior_worker = particle.process.pid
            close_client(particle, 'particle-' + naif)
            particle = ParticleClient(particle_folder / 'reopened')
            store.restore_to(particle_folder / 'reopened')
            particle.call('load')
            assert particle.process.pid != prior_worker and particle.snapshot()['experiment']['phase'] == saved_phase
            particle.call('advance', dict(steps=64))
            actual_future = particle.call('export_payload')['result']
            assert {k: v for k, v in actual_future.items() if k != 'edit_token'} == {k: v for k, v in future.items() if k != 'edit_token'}
            close_client(particle, 'particle-reopened-' + naif)
            particle = None
            source16 = copy.deepcopy(source.orbital.latest)
            try:
                source.orbital.latest = initial16
                refuse('Particle source16 ' + naif, lambda: initial_admission._initial(request))
            finally:
                source.orbital.latest = source16
            same_phase()
            passed('Particle real worker exact checkpoint/reopen/future ' + naif,
                   species=species, accepted_steps=256, future_steps=64, physical_unit_m=unit,
                   source_guard=artifact.body.guard(phase), independent_time_s=saved_phase['time_s'],
                   initial_parameters=parameters, initial_field_T=field, reading=reading)
            spatial = artifact.Run.create(phase, dict(body_id=body['id'], source_guard=artifact.body.guard(phase)), recipe['spatial_configuration'])
            assert artifact.Run.restore(spatial.payload).payload == spatial.payload
            run = artifact.Run.create(phase, dict(body_id=body['id'], source_guard=artifact.body.guard(phase)), recipe['layer_configuration'])
            plan = contract.compose(phase, run.payload, reading, dict(spatial=True, magnetic=True))
            scientific = dict(schema=1, kind='independent_frozen_layer_pair', spatial=run.payload, magnetic=reading, admission=plan)
            layer_store = LayerStore(folder / ('layers-' + naif))
            for visible in recipe['layer_visibilities']:
                layer_store.save(scientific, visible)
                science, restored_visible, _, origin = layer_store.load()
                assert science == scientific and restored_visible == visible and origin is None
            branch = layer_store.branch(scientific, dict(spatial=True, magnetic=True), record_name='Origem ' + naif)
            child = layer_store.branch(scientific, dict(spatial=False, magnetic=True), record_name='Filho ' + naif, parent=branch['record']['id'])
            child_science, child_visible, child_record, _ = layer_store.load(child['record']['id'])
            assert child_science == scientific and not child_visible['spatial'] and child_record['parent'] == branch['record']['id']
            export = layer_store.export(scientific, child_visible)
            assert layers.migration.store.decode(json.loads(Path(export['path']).read_text()))[0] == scientific
            before = {p.relative_to(layer_store.folder).as_posix(): sha(p) for p in layer_store.folder.rglob('*.json')}
            refuse('Sixteen phase cannot relabel four-layer artifact ' + naif, lambda: contract.compose(initial16, run.payload, reading, dict(spatial=True, magnetic=True)))
            refuse('Orbital manifest is not layer checkpoint ' + naif, lambda: layers.migration.checkpoint.restore(json.loads((saved16 / 'latest.json').read_text())))
            assert before == {p.relative_to(layer_store.folder).as_posix(): sha(p) for p in layer_store.folder.rglob('*.json')}
            same_phase()
            passed('Real spatial/magnetic science and layer checkpoint/branches/visibilities ' + naif,
                   scientific_sha256=contract.digest(scientific), plan=plan, export=export)
        solar = SolarClient(folder / 'solar-zone')
        passed('Nuclear real Windows worker started; beginning prescribed-density calculation')
        solar.call('create', dict(source_phase=phase, configuration=recipe['solar_configuration']))
        assert solar.snapshot()['configuration'] == recipe['solar_configuration']
        assert len(solar.snapshot()['configuration']['channel_switches']) == 18
        solar.call('sample', dict(index=recipe['solar_knots'][0]))
        saved = copy.deepcopy(solar.snapshot())
        payload = solar.call('get_result')['result']
        assert payload['source_phase'] == phase
        solar.call('save')
        checkpoint_sha = sha(folder / 'solar-zone/saved.json')
        saved_guard = solar.guard(solar.snapshot())
        solar.call('sample', dict(index=recipe['solar_knots'][1]))
        solar.call('load')
        assert solar.snapshot()['sample'] == saved['sample'] and solar.snapshot()['artifact_sha256'] == saved['artifact_sha256']
        refuse('Solar stale token after reload', lambda: solar.call('sample', dict(index=121), guard=saved_guard), lambda: {k: solar.snapshot()[k] for k in ['artifact_id', 'artifact_sha256', 'edit_token', 'revision', 'sample', 'view', 'source']})
        branch = solar.call('branch_create', dict(name='Origem solar ampliada', parent=None))['result']
        child = solar.call('branch_create', dict(name='Filho solar ampliado', parent=branch['branch']['id']))['result']
        solar.call('sample', dict(index=121))
        solar.call('branch_load', dict(branch_id=child['branch']['id']))
        assert solar.snapshot()['sample'] == saved['sample']
        export = solar.call('export')['result']
        exported = json.loads(Path(export['path']).read_text())
        assert exported['run'] == payload and exported['sample'] == saved['sample']
        preferences = copy.deepcopy(solar.snapshot()['view'])
        preferences['visible']['neutrinos'] = False
        solar.call('set_view', dict(view=preferences))
        assert solar.snapshot()['artifact_sha256'] == saved['artifact_sha256'] and not solar.snapshot()['view']['visible']['neutrinos']
        same_phase()
        passed('Nuclear18 channels exact save/load/branch-child/export and independent visibility', export=export,
               artifact_id=saved['artifact_id'], artifact_sha256=saved['artifact_sha256'], source=saved['source'], sample=saved['sample'])
        configuration = copy.deepcopy(recipe['solar_configuration'])
        configuration['acting']['weak'] = False
        solar.call('configure', dict(configuration=configuration))
        assert not solar.snapshot()['configuration']['acting']['weak'] and solar.snapshot()['artifact_id'] != saved['artifact_id']
        off = solar.call('get_result')['result']
        assert off['source_phase'] == phase and off['actual'] != payload['actual']
        solar.call('load')
        assert solar.snapshot()['configuration']['acting']['weak'] and solar.snapshot()['sample'] == saved['sample']
        assert solar.snapshot()['artifact_sha256'] == saved['artifact_sha256'] and sha(folder / 'solar-zone/saved.json') == checkpoint_sha
        old_pid = solar.process.pid
        close_client(solar, 'solar-zone')
        solar = SolarClient(folder / 'solar-zone')
        assert solar.process.pid != old_pid
        solar.call('load')
        assert solar.snapshot()['sample'] == saved['sample'] and solar.call('get_result')['result'] == payload
        refused_guard = solar.guard(solar.snapshot())
        refuse('Sixteen source cannot create nuclear scenario', lambda: solar.call('create', dict(source_phase=initial16, configuration=recipe['solar_configuration'])), lambda: {k: solar.snapshot()[k] for k in ['artifact_id', 'artifact_sha256', 'edit_token', 'revision', 'sample', 'view', 'source']})
        assert solar.guard(solar.snapshot()) == refused_guard
        close_client(solar, 'solar-zone-reopened')
        solar = None
        same_phase()
        passed('Nuclear weak recomputation/restore/new worker; orbital phase unchanged')
        shutil.copy2(saved16 / 'latest.json', folder / 'orbital-worker/latest.json')
        orbital.call('load')
        restored = copy.deepcopy(orbital.latest)
        assert restored['bodies'] == initial16['bodies'] and restored['atlas_initial'] == sixteen
        assert restored['time'] == initial16['time'] and restored['dynamics16'] == initial16['dynamics16']
        assert restored['interventions'] == initial16['interventions'] and restored['edit_token'] != initial16['edit_token']
        before = physical(restored)
        response = orbital.call('solar_reading', expect_error=True, **orbital_guard(phase), body_id=phase['bodies'][1]['id'])
        orbital.call('snapshot')
        assert physical(orbital.latest) == before
        report['refusals'].append(dict(name='Four guard after final16 restore', error=response['message']))
        for body in restored['bodies']:
            assert len(orbital.call('dynamics16_reading', **orbital_guard(restored), body_id=body['id'])['result']['sources']) == 15
        pid = orbital.process.pid
        orbital.close()
        report['processes'].append(dict(kind='orbital', pid=pid, exit=0))
        orbital = None
        assert all(sha(ROOT / n) == seal for n, seal in protected.items())
        assert all(sha(ROOT / n) == seal for n, seal in sources.items())
        passed('Exact16 final restore,16 readings15 sources,protected files and all worker exits zero')
        report.update(accepted=True, completed=True, completed_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                      common_four_phase_unchanged=True, original16_exact=True, protected_unchanged=True)
    except Exception:
        report['failure'] = traceback.format_exc()
    finally:
        for client in [particle, solar, orbital]:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    report.setdefault('cleanup_failures', []).append(traceback.format_exc())
                    report['accepted'] = False
        persist()
    print(json.dumps(dict(accepted=report['accepted'], steps=len(report['steps']), refusals=len(report['refusals']),
                          failure=report.get('failure', '').splitlines()[-1:])), flush=True)
    return 0 if report['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
