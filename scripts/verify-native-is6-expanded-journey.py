"""One actual CEF+engine journey through sixteen-body dynamics and separate four-body instruments."""
import argparse
import copy
import datetime as dt
import hashlib
from importlib.machinery import SourceFileLoader
import json
import math
from pathlib import Path
import shutil
import sys
import time
import traceback
import urllib.error
import urllib.request
import zipfile

import numpy as np
from PIL import Image
from cef_page_v2 import Page

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'output/is6-expanded-journey-product0.27.0/app'
sys.path.insert(0, str(APP))
import is6_layer_contract as contract
from is4_client import Client as ParticleClient
from is5_compression_client import Client as SolarClient
import body_field_scene
from is6_product_scene import lua

h = SourceFileLoader('expanded_native_helpers', str(ROOT / 'scripts/benchmark-body-points-native.py')).load_module()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def guard(p):
    return {k: p[k] for k in ['system_id', 'edit_token', 'revision']} | dict(expected_time=p['time'], frame=p['contract']['frame'])


def physical(p):
    return {k: copy.deepcopy(p[k]) for k in ['system_id', 'edit_token', 'revision', 'time', 'bodies',
                                           'atlas_initial', 'interventions', 'dynamics16', 'paused', 'contract', 'physical_scale']}


def post(path, payload, expected=200):
    request = urllib.request.Request('http://127.0.0.1:4700' + path, data=json.dumps(payload, allow_nan=False).encode(),
                                     headers={'Content-Type': 'application/json'})
    try:
        response = urllib.request.urlopen(request, timeout=750)
    except urllib.error.HTTPError as error:
        assert error.code == expected, (error.code, error.read().decode())
        return json.load(error)
    with response:
        assert response.status == expected
        return json.load(response)


def context(phase):
    names = ['LabGrid', 'LabBarycenter', 'LabProbe']
    for body in phase['bodies']:
        names.extend(body[k] for k in ['scene_node', 'label_node', 'shape_node', 'spin_node'] if body.get(k))
    layer = h.get('/api/state').get('body_field_preview')
    if layer:
        names.extend(mesh['node'] for mesh in layer['render']['meshes'])
        names.append(layer['render']['label_node'])
    return h.native('local f={};for _,n in ipairs(' + lua(names) + ') do if openspace.hasSceneGraphNode(n) then local ok,v=pcall(openspace.propertyValue,"Scene."..n..".Renderable.Enabled");if ok and type(v)=="boolean" then f[n]=v end end end;return {camera=openspace.navigation.getNavigationState("Root"),flags=f}')


def same_context(a, b):
    assert a['flags'] == b['flags'] and set(a['camera']) == set(b['camera'])
    for key, value in a['camera'].items():
        if key == 'Up':
            assert all(abs(x - y) <= 1e-12 for x, y in zip(value, b['camera'][key], strict=True))
        else:
            assert value == b['camera'][key], (key, value, b['camera'][key])


def geometry(phase):
    def array(value):
        return [value[str(i)] for i in range(1, len(value) + 1)] if isinstance(value, dict) else value
    expected = np.array([[math.fsum(row[k] * b['position'][k] * phase['physical_scale']['length_unit_m']
                                   for k in range(3)) for row in phase['atlas_initial']['j2000_to_render_frame']]
                         for b in phase['bodies']])
    budgets = np.array([[max(.001, 8 * math.ulp(float(x))) for x in row] for row in expected])
    code = 'return {positions={' + ','.join('openspace.propertyValue("Scene.' + b['scene_node'] + '.Translation.Position")' for b in phase['bodies']) + '}}'
    deadline = time.monotonic() + 8
    while True:
        actual = np.array([array(row) for row in array(h.native(code)['positions'])])
        error = np.abs(actual - expected)
        if np.all(error <= budgets):
            return dict(bodies=len(phase['bodies']), maximum_error_m=float(error.max()), maximum_budget_m=float(budgets.max()))
        if time.monotonic() > deadline:
            raise AssertionError(dict(error=error.tolist(), budgets=budgets.tolist()))
        time.sleep(.05)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    parser.add_argument('--service-label', required=True)
    args = parser.parse_args()
    for label in [args.label, args.service_label]:
        assert label and len(label) <= 24 and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label)
    folder = ROOT / f'output/is6-expanded-journey-native-{args.label}'
    receipt = ROOT / f'evidence/is6-expanded-journey-native-{args.label}.json'
    assert not folder.exists() and not receipt.exists(), 'Preserve native journey evidence'
    service_path = ROOT / f'evidence/is6-expanded-instruments-service-{args.service_label}.json'
    service = json.loads(service_path.read_text())
    assert service['accepted'] and service['completed']
    assert all(sha(ROOT / n) == seal for n, seal in service['source_sha256'].items())
    recipe = copy.deepcopy(service['recipe_before_execution'])
    packet = json.loads((APP.parent / 'build-manifest.json').read_text())
    assert {p.relative_to(APP).as_posix(): sha(p) for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts} == packet['files_sha256']
    sources = {(APP / name).relative_to(ROOT).as_posix(): seal for name, seal in packet['files_sha256'].items()}
    for path in [Path(__file__), service_path, APP.parent / 'build-manifest.json', APP.parent / 'journey-inventory.json',
                 ROOT / 'scripts/cef_page_v2.py', ROOT / 'scripts/benchmark-body-points-native.py',
                 ROOT / 'scripts/verify-native-solar-integration.py', ROOT / 'scripts/engine-command.py',
                 ROOT / 'scripts/run-is6-expanded-journey-native.py', ROOT / 'scripts/launch-is6-expanded-journey-candidate.py',
                 ROOT / 'scripts/is6_owned_profile_host.py', ROOT / 'IS-6-PERCURSO-AMPLIADO16-NATIVO-CONTRATO.md']:
        sources[path.relative_to(ROOT).as_posix()] = sha(path)
    folder.mkdir()
    with zipfile.ZipFile(folder / 'executed-sources.zip', 'x', zipfile.ZIP_DEFLATED) as archive:
        for name in sources:
            archive.write(ROOT / name, name)
    protected = {n: sha(ROOT / n) for n in ['user/sessions/latest.json', 'user/navigation/favorites.json',
                 'Iniciar-Cosmos2.cmd', 'Abrir-Dinamica16.cmd', 'Abrir-Planetas-e-Luas.cmd',
                 'output/is6-dynamics16-product0.26.2/navigation/favorites.json'] if (ROOT / n).is_file()}
    session = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
    assert Path(session['serverScript']).resolve() == APP / 'server.py' and session['is6ExpandedJourneyCandidate']
    result = dict(accepted=False, completed=False, candidate='0.27.0', session=session,
                  started_utc=dt.datetime.now(dt.timezone.utc).isoformat(), recipe_before_execution=recipe,
                  source_sha256=sources, source_archive_sha256=sha(folder / 'executed-sources.zip'),
                  service_source_archive_sha256=service['source_archive_sha256'], protected_sha256=protected,
                  steps=[], selections=[], geometry=[], captures=[], refusals=[], cleanups=[], archives=[], page_errors=[],
                  scope='First real CEF/native journey16->4 instruments->16. Original captures require separate direct inspection; process exits/reopen and residency remain separately audited.')
    original_id = None
    previous_scale = '1'
    def persist():
        receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')
    def passed(name, **fields):
        result['steps'].append(dict(name=name, **fields))
        persist()
        print(json.dumps(dict(progress=name), ensure_ascii=False), flush=True)
    def module(name):
        return h.get('/api/' + name + '/state')
    def command(name, **fields):
        return post('/api/command', dict(command=name, **fields))
    def same_phase():
        assert physical(h.get('/api/state')['physics']) == common4
    def click(page, selector, timeout=70000):
        page.evaluate('(()=>{const e=document.querySelector(' + json.dumps(selector) + ');if(e?.closest("#lab-panel")&&getComputedStyle($("lab-panel")).display==="none"&&document.body.classList.contains("details-open"))$("panel-toggle").click();for(let p=e?.parentElement;p;p=p.parentElement)if(p.tagName==="DETAILS")p.open=true;})()')
        page.wait_for_function('document.querySelector(' + json.dumps(selector) + ')&&!document.querySelector(' + json.dumps(selector) + ').matches(":disabled")', timeout=timeout)
        page.locator(selector).click()
        page.wait_for_function('!pending&&!spatialInstrument.pending&&!layerInstrument.pending&&!layerInstrument.snapshot?.busy&&!particlePending&&!solarZonePending', timeout=timeout)
    def removed(nodes, before, phase):
        nodes = list(dict.fromkeys(n for n in nodes if isinstance(n, str)))
        assert nodes
        exists = h.native('local r={};for _,n in ipairs(' + lua(nodes) + ') do r[n]=openspace.hasSceneGraphNode(n) end;return r')
        assert not any(exists.values()), exists
        after = context(phase)
        same_context(before, after)
        same_phase()
        result['cleanups'].append(dict(nodes=exists, before=before, after=after))
        persist()
    def refused(name, path, payload):
        def confirmed_instruments():
            values = {}
            for instrument in ['layers', 'spatial', 'particles', 'solar-zone']:
                state = module(instrument)
                value = dict(active=state['active'])
                if instrument in ['layers', 'spatial']:
                    value.update(guard=state['guard'], artifact=state.get('artifact'), scene=state.get('scene'))
                elif state['active'] and instrument == 'particles':
                    value.update(experiment=state['worker']['experiment'], nodes=state['view']['native_nodes'])
                elif state['active']:
                    value.update(worker={k: state['worker'][k] for k in ['artifact_id', 'artifact_sha256', 'edit_token', 'revision', 'sample', 'view']}, scene=state['scene'])
                values[instrument] = value
            return values
        before = physical(h.get('/api/state')['physics'])
        instruments = confirmed_instruments()
        camera = context(h.get('/api/state')['physics'])
        answer = post(path, payload, expected=400)
        assert answer.get('ok') is False and physical(h.get('/api/state')['physics']) == before
        assert confirmed_instruments() == instruments
        same_context(camera, context(h.get('/api/state')['physics']))
        result['refusals'].append(dict(name=name, error=answer['error'], physical_and_camera_unchanged=True))
        persist()
    def capture(page, name, scale, focus):
        page.locator('#ui-scale').select_option(scale)
        page.evaluate('(()=>{const e=document.getElementById(' + json.dumps(focus) + ');if(e.closest("#lab-panel")&&document.body.classList.contains("details-open"))$("panel-toggle").click();for(let p=e.parentElement;p;p=p.parentElement)if(p.tagName==="DETAILS")p.open=true;e.scrollIntoView({block:"start"});})()')
        time.sleep(.45)
        layout = page.evaluate('({scale:$("ui-scale").value,width:innerWidth,height:innerHeight,scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth})')
        assert layout['scale'] == scale and layout['scroll'] <= layout['client']
        before = set((ROOT / 'user/screenshots').rglob('*.png'))
        h.native('openspace.takeScreenshot();return {requested=true}')
        deadline = time.monotonic() + 20
        while True:
            fresh = set((ROOT / 'user/screenshots').rglob('*.png')) - before
            if fresh:
                assert len(fresh) == 1
                source = fresh.pop()
                try:
                    with Image.open(source) as image:
                        assert image.size == (1920, 1080)
                        image.load()
                    break
                except (OSError, SyntaxError):
                    pass
            if time.monotonic() > deadline:
                raise TimeoutError('Original framebuffer PNG incomplete')
            time.sleep(.1)
        target = folder / (str(len(result['captures']) + 1).zfill(2) + '-' + name + '-' + str(int(float(scale) * 100)) + '.png')
        shutil.copy2(source, target)
        assert sha(target) == sha(source)
        result['captures'].append(dict(path=target.relative_to(ROOT).as_posix(), sha256=sha(target),
            native_original=source.relative_to(ROOT).as_posix(), scale=scale, name=name, layout=layout,
            method='Unedited original OpenSpace framebuffer'))
        persist()
    def particle_ready(page):
        page.wait_for_function('!particlePending&&particleState.active&&particleState.worker.paused&&!particleState.view.pending_sequence&&particleState.view.confirmed_phase.time_s===particleState.worker.experiment.phase.time_s', timeout=30000)
        state = module('particles')
        assert not state['error'], state['error']
        return state
    def zone_ready(page):
        page.wait_for_function('solarZoneState.active&&!solarZonePending&&!solarZoneState.busy&&!solarZoneCurvePending&&solarZoneCurveId===solarZoneState.worker.artifact_id', timeout=750000)
        state = module('solar-zone')
        assert not state['error'], state['error']
        return state
    persist()
    try:
        with Page() as page:
            page.on('pageerror', lambda error: result['page_errors'].append(error))
            page.wait_for_function('appState?.mode==="atlas"&&atlasState&&layerInstrument.snapshot&&spatialInstrument.snapshot&&particleState&&solarZoneState&&!pending')
            previous_scale = page.evaluate('$("ui-scale").value')
            result['original_navigation'] = h.get('/api/navigation/state')
            result['original_favorites'] = h.get('/api/navigation/favorites')['views']
            saved = post('/api/navigation/save', dict(name='Percurso ampliado temporário'))['navigation']['views']
            original_id = next(v['id'] for v in saved if v['id'] not in {a['id'] for a in result['original_favorites']})
            page.locator('#ui-scale').select_option('1')
            page.evaluate('$("atlas-epoch").value=' + json.dumps(recipe['utc'].removesuffix('Z')))
            click(page, '#apply-atlas-epoch')
            atlas = h.get('/api/atlas/state')
            assert len(atlas['bodies']) == len(atlas['renderer']['positions']) == 16
            result['atlas_before'] = atlas
            for scale in ['1', '1.5']:
                capture(page, 'atlas16', scale, 'atlas-epoch')
            page.locator('#ui-scale').select_option('1')
            click(page, '#copy-sixteen')
            initial16 = copy.deepcopy(h.get('/api/state')['physics'])
            assert initial16['paused'] and len(initial16['bodies']) == 16 and initial16['time'] == 0
            for actual, expected in zip(initial16['bodies'], service['source_phase16']['bodies'], strict=True):
                assert {key: actual[key] for key in ['reference_id', 'applied_GM_m3_s2', 'mass', 'position', 'velocity']} == {key: expected[key] for key in ['reference_id', 'applied_GM_m3_s2', 'mass', 'position', 'velocity']}
            assert initial16['atlas_initial']['source']['epoch']['et_tdb_s'] == h.get('/api/atlas/state')['epoch']['et_tdb_s']
            assert not initial16['dynamics16']['electromagnetic_coupling'] and not initial16['dynamics16']['nuclear_coupling']
            result['geometry'].append(geometry(initial16))
            for scale in ['1', '1.5']:
                page.locator('#ui-scale').select_option(scale)
                for body in initial16['bodies']:
                    page.locator('#solar-body').select_option(body['id'])
                    click(page, '#solar-view-body')
                    click(page, '#solar-sample')
                    page.wait_for_function('solarReading?.body_id===' + json.dumps(body['id']) + '&&!pending', timeout=30000)
                    reading = page.evaluate('solarReading')
                    assert len(reading['sources']) == 15
                    expected = {}
                    for other in initial16['bodies']:
                        if other['id'] == body['id']:
                            continue
                        delta = [(other['position'][k] - body['position'][k]) * initial16['physical_scale']['length_unit_m'] for k in range(3)]
                        radius = math.hypot(*delta)
                        expected[other['id']] = [other['applied_GM_m3_s2'] * value / radius**3 for value in delta]
                    maximum = max(abs(value - expected[row['id']][k]) for row in reading['sources'] for k, value in enumerate(row['acceleration_m_s2']))
                    assert maximum <= 1e-10
                    assert h.native('return openspace.navigation.getNavigationState("Root")')['Anchor'] == body['scene_node']
                    result['selections'].append(dict(body=body['reference_id'], scale=scale, sources=15, maximum_component_error_m_s2=maximum))
                capture(page, 'dynamics16', scale, 'solar-body')
            page.locator('#ui-scale').select_option('1')
            click(page, '#save')
            checkpoint16 = copy.deepcopy(h.get('/api/state')['physics'])
            result['checkpoint16'] = checkpoint16
            page.evaluate('$("branch-name").value="Origem16 ampliada"')
            click(page, '#branch-create')
            first_branch = h.get('/api/state')['physics']['branches']['active_id']
            click(page, '#play')
            page.wait_for_function('appState.physics.time>0&&!appState.physics.paused', timeout=15000)
            time.sleep(.15)
            click(page, '#play')
            page.wait_for_function('appState.physics.paused', timeout=15000)
            page.evaluate('$("branch-name").value="Filho16 ampliado"')
            click(page, '#branch-create')
            child_branch = h.get('/api/state')['physics']['branches']['active_id']
            page.locator('#branch-first').select_option(first_branch)
            page.locator('#branch-second').select_option(child_branch)
            click(page, '#branch-compare')
            click(page, '#branch-export')
            result['comparison_export_notice'] = page.locator('#notice').inner_text()
            click(page, '#load')
            restored16 = h.get('/api/state')['physics']
            assert restored16['bodies'] == checkpoint16['bodies'] and restored16['dynamics16'] == checkpoint16['dynamics16']
            assert restored16['edit_token'] != checkpoint16['edit_token']
            result['sixteen_branches'] = dict(first=first_branch, child=child_branch)
            passed('Atlas16 and32 native selections/readings;16 checkpoint/parent-child/comparison/export')
            click(page, '#atlas')
            click(page, '#copy-solar')
            phase4 = copy.deepcopy(h.get('/api/state')['physics'])
            assert phase4['paused'] and len(phase4['bodies']) == 4 and phase4['dynamics16'] is None
            assert phase4['atlas_initial']['source']['epoch']['et_tdb_s'] == checkpoint16['atlas_initial']['source']['epoch']['et_tdb_s']
            page.evaluate('$("branch-name").value="Fase4 comum aos instrumentos"')
            click(page, '#branch-create')
            result['four_branch'] = h.get('/api/state')['physics']['branches']['active_id']
            phase4 = copy.deepcopy(h.get('/api/state')['physics'])
            common4 = physical(phase4)
            result['common_source_phase4'] = phase4
            refused('Old16 guard in4', '/api/command', dict(command='dynamics16_reading', **guard(restored16), body_id=restored16['bodies'][0]['id']))
            result['instrument_checkpoints'] = {}
            for naif, species in recipe['body_cases']:
                body = next(b for b in phase4['bodies'] if b['reference_id'] == 'sol:naif:' + naif)
                baseline = context(phase4)
                click(page, '#open-spatial')
                page.locator('#spatial-body').select_option(body['id'])
                click(page, '#spatial-create')
                spatial = module('spatial')
                assert spatial['active'] and spatial['artifact']['source']['body_id'] == body['id']
                for scale in ['1', '1.5']:
                    capture(page, 'mesh-' + naif, scale, 'spatial-title')
                page.locator('#ui-scale').select_option('1')
                refused('Nuclear while mesh ' + naif, '/api/solar-zone/command', dict(command='create', source_guard=contract.artifact.body.guard(phase4), configuration=recipe['solar_configuration']))
                old = module('spatial')['scene']
                click(page, '#spatial-leave')
                removed([old[k] for k in ['frame', 'wire', 'focus']], baseline, phase4)
                click(page, '#spatial-panel-close')
                baseline = context(phase4)
                click(page, '#open-layers')
                page.locator('#layers-body').select_option(body['id'])
                click(page, '#layers-create')
                layer = module('layers')
                assert layer['active'] and not layer['error'] and not layer['recovery_required']
                scientific = post('/api/layers/command', dict(command='get_artifact', guard=layer['guard']))['result']['scientific']
                source_phase = scientific['spatial']['phase']
                assert physical(source_phase) == common4 and scientific['spatial']['configuration'] == recipe['layer_configuration']
                assert contract.magnetic(source_phase, scientific['magnetic']) == scientific['magnetic']
                assert contract.compose(source_phase, scientific['spatial'], scientific['magnetic'], dict(spatial=True, magnetic=True)) == scientific['admission']
                scene = layer['scene']
                drawing = body_field_scene.build(scientific['magnetic'])
                expected_point = body_field_scene.product(drawing['body_to_render'], drawing['point_model_m'])
                native_point = h.native('return {local_point=openspace.propertyValue("Scene.' + scene['magnetic_frame'] + '_probe.Translation.Position"),point=openspace.worldPosition(' + lua(scene['magnetic_frame'] + '_probe') + '),center=openspace.worldPosition(' + lua(scene['magnetic_frame']) + ')}')
                assert max(abs(x - y) for x, y in zip(native_point['local_point'], expected_point, strict=True)) <= .001
                assert all(abs((p - c) - e) <= math.ulp(p) + math.ulp(c) + .001 for p, c, e in zip(native_point['point'], native_point['center'], expected_point, strict=True))
                result.setdefault('layer_native_coordinates', []).append(dict(body=naif, native=native_point, expected_relative_m=expected_point))
                digest = contract.digest(scientific)
                click(page, '#layers-save')
                page.evaluate('$("layers-branch-name").value=' + json.dumps('Camadas ampliadas ' + naif))
                click(page, '#layers-branch-create')
                layer_branch = module('layers')['branch_parent']
                for key in ['spatial', 'magnetic']:
                    click(page, '#layers-' + key + '-visible')
                assert module('layers')['artifact']['sha256'] == digest
                click(page, '#layers-load')
                assert module('layers')['artifact']['sha256'] == digest and module('layers')['artifact']['visible'] == dict(spatial=True, magnetic=True)
                click(page, '#layers-export')
                for scale in ['1', '1.5']:
                    capture(page, 'layers-' + naif, scale, 'layers-spatial-reading')
                page.locator('#ui-scale').select_option('1')
                refused('Particle while coordinated layers ' + naif, '/api/particles/command', dict(command='load_saved'))
                old = module('layers')['scene']
                click(page, '#layers-leave')
                removed([old['spatial_frame'], old['spatial_wire'], old['spatial_frame'].replace('SpatialFrame_', 'SpatialFocus_'),
                         old['magnetic_frame'], *old['magnetic_nodes'], *[old['magnetic_frame'] + suffix for suffix in ['_basis', '_probe', '_display_probe']]], baseline, phase4)
                click(page, '#layers-panel-close')
                page.locator('#solar-body').select_option(body['id'])
                page.locator('#body-field-representation').select_option('vector')
                prefix = 'earth-field-' if naif == '399' else 'jupiter-field-'
                for key, value in recipe['magnetic_points'][naif].items():
                    display = value / 1000 if key == 'altitude' else value / 71492000 if key == 'radius' else value
                    page.evaluate('document.getElementById(' + json.dumps(prefix + key) + ').value=' + json.dumps(str(display)))
                if naif == '599':
                    page.locator('#jupiter-field-degree').select_option('13')
                click(page, '#body-field-show')
                page.wait_for_function('appState.body_field_preview?.reading.body_id===' + json.dumps(body['id']), timeout=30000)
                baseline = context(phase4)
                page.locator('#particle-species').select_option(species)
                page.evaluate('$("particle-speed").value=' + json.dumps(str(recipe['particle_speeds_m_s'][species])) + ';$("particle-pitch").value="60"')
                click(page, '#particle-create')
                particle_ready(page)
                for _ in range(recipe['particle_steps']):
                    click(page, '#particle-step')
                    particle_ready(page)
                click(page, '#particle-sample')
                particle = particle_ready(page)
                saved_phase = copy.deepcopy(particle['worker']['experiment']['phase'])
                click(page, '#particle-save')
                page.evaluate('$("particle-branch-name").value=' + json.dumps('Partícula ampliada ' + naif))
                click(page, '#particle-branch-create')
                particle_branch = module('particles')['branch_parent']
                click(page, '#particle-step')
                particle_ready(page)
                click(page, '#particle-load')
                particle = particle_ready(page)
                assert particle['worker']['experiment']['phase'] == saved_phase
                click(page, '#particle-export')
                for scale in ['1', '1.5']:
                    capture(page, 'particle-' + naif, scale, 'particle-title')
                page.locator('#ui-scale').select_option('1')
                refused('Mesh while particle ' + naif, '/api/spatial/command', dict(command='create', guard=module('spatial')['guard'], source_guard=contract.artifact.body.guard(phase4), body_id=body['id'], configuration=recipe['spatial_configuration']))
                old = module('particles')['view']['native_nodes']
                click(page, '#particle-leave')
                removed(list(old.values()), baseline, phase4)
                click(page, '#body-field-clear')
                page.wait_for_function('!appState.body_field_preview&&!pending', timeout=30000)
                result['instrument_checkpoints'][naif] = dict(layer_branch=layer_branch, layer_sha256=digest,
                    layer_scientific=scientific, particle_branch=particle_branch, particle_phase=saved_phase)
                passed('Same4 phase: real mesh/layers/' + species + '/checkpoints/exports/native cleanup ' + naif)
            baseline = context(phase4)
            assert page.evaluate('zoneConfiguration()') == recipe['solar_configuration']
            click(page, '#zone-create', timeout=750000)
            zone = zone_ready(page)
            assert zone['worker']['configuration'] == recipe['solar_configuration']
            page.evaluate('$("zone-index").value="120";$("zone-index").dispatchEvent(new Event("change",{bubbles:true}))')
            page.wait_for_function('solarZoneState.worker.view.selected_index===120&&!solarZonePending', timeout=30000)
            zone = zone_ready(page)
            saved_zone = copy.deepcopy(zone['worker'])
            click(page, '#zone-save', timeout=750000)
            click(page, '#zone-step')
            click(page, '#zone-load', timeout=750000)
            assert zone_ready(page)['worker']['sample'] == saved_zone['sample']
            page.evaluate('$("zone-branch-name").value="Zona solar ampliada"')
            click(page, '#zone-branch-create')
            click(page, '#zone-export')
            export = Path(page.locator('#zone-file').inner_text().removeprefix('Exportado: '))
            exported = json.loads(export.read_text())
            assert exported['sample'] == saved_zone['sample']
            for scale in ['1', '1.5']:
                capture(page, 'nuclear18', scale, 'zone-probe')
            page.locator('#ui-scale').select_option('1')
            click(page, '#zone-show-neutrinos')
            assert zone_ready(page)['worker']['artifact_sha256'] == saved_zone['artifact_sha256']
            click(page, '#zone-weak')
            click(page, '#zone-recompute', timeout=750000)
            off = zone_ready(page)
            assert not off['worker']['configuration']['acting']['weak'] and off['worker']['artifact_id'] != saved_zone['artifact_id']
            click(page, '#zone-load', timeout=750000)
            assert zone_ready(page)['worker']['sample'] == saved_zone['sample']
            refused('Mesh while nuclear', '/api/spatial/command', dict(command='create', guard=module('spatial')['guard'], source_guard=contract.artifact.body.guard(phase4), body_id=phase4['bodies'][0]['id'], configuration=recipe['spatial_configuration']))
            old = module('solar-zone')['scene']
            click(page, '#zone-leave')
            removed([old['node'], old['label_node']], baseline, phase4)
            result['solar_checkpoint'] = dict(artifact_id=saved_zone['artifact_id'], artifact_sha256=saved_zone['artifact_sha256'], sample=saved_zone['sample'], source=saved_zone['source'])
            passed('Same4 phase: nuclear18 checkpoint/branch/export/visibility/weak recomputation/restore/cleanup')
            click(page, '#load')
            final16 = h.get('/api/state')['physics']
            assert final16['bodies'] == checkpoint16['bodies'] and final16['atlas_initial'] == checkpoint16['atlas_initial']
            assert final16['dynamics16'] == checkpoint16['dynamics16'] and final16['time'] == checkpoint16['time']
            assert final16['revision'] == checkpoint16['revision'] and final16['interventions'] == checkpoint16['interventions']
            assert final16['edit_token'] != checkpoint16['edit_token']
            result['geometry'].append(geometry(final16))
            refused('Four guard after16 restore', '/api/command', dict(command='solar_reading', **guard(phase4), body_id=phase4['bodies'][1]['id']))
            refused('Old16 token after final restore', '/api/command', dict(command='dynamics16_reading', **guard(checkpoint16), body_id=checkpoint16['bodies'][0]['id']))
            refused('Particle creation outside4 domain', '/api/particles/command', dict(command='create', source_guard=contract.artifact.body.guard(final16), species='proton', speed_m_s=100000., pitch_deg=60.))
            for scale in ['1', '1.5']:
                page.locator('#solar-body').select_option(final16['bodies'][-1]['id'])
                click(page, '#solar-view-body')
                click(page, '#solar-sample')
                assert len(page.evaluate('solarReading')['sources']) == 15
                capture(page, 'restored16', scale, 'solar-body')
            page.locator('#ui-scale').select_option('1')
            click(page, '#atlas')
            for selector, count in [('#copy-atlas', 3), ('#copy-solar', 4)]:
                click(page, selector)
                assert len(h.get('/api/state')['physics']['bodies']) == count
                click(page, '#atlas')
            assert not result['page_errors'], result['page_errors']
            for name in ['gravity-sessions', 'particle-checkpoints', 'layer-checkpoints', 'solar-zone-checkpoints']:
                for source_file in (APP.parent / name).rglob('*.json'):
                    if '_work' in source_file.parts:
                        continue
                    target = folder / 'stored-archives' / name / source_file.relative_to(APP.parent / name)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_file, target)
                    assert sha(target) == sha(source_file)
                    result['archives'].append(dict(path=target.relative_to(ROOT).as_posix(), sha256=sha(target), original=source_file.relative_to(ROOT).as_posix()))
            assert all(sha(ROOT / n) == seal for n, seal in sources.items())
            assert all(sha(ROOT / n) == seal for n, seal in protected.items())
            passed('Exact final16 restore,new token,guards,15 contributions,legacy3/4 and isolated archives')
            result.update(accepted=True, completed=True)
    except Exception:
        result['failure'] = traceback.format_exc()
    finally:
        try:
            for name in ['solar-zone', 'particles', 'layers', 'spatial']:
                state = module(name)
                if state['active'] or state.get('recovery_required'):
                    request = dict(command='leave')
                    if name == 'solar-zone':
                        request['guard'] = SolarClient.guard(state['worker'])
                    elif name in ['layers', 'spatial']:
                        request['guard'] = state['guard']
                    post('/api/' + name + '/command', request)
            if h.get('/api/state')['mode'] == 'experiment':
                command('atlas')
            if original_id:
                restored = post('/api/navigation/restore', dict(id=original_id))['navigation']
                post('/api/navigation/delete', dict(id=original_id))
                assert restored['et'] == result['original_navigation']['et']
                assert h.get('/api/navigation/favorites')['views'] == result['original_favorites']
                with Page() as page:
                    page.wait_for_function('appState?.mode==="atlas"&&navigationState&&!pending')
                    page.locator('#ui-scale').select_option(previous_scale)
                    page.evaluate('selectTarget(' + json.dumps(restored['target']) + ',true)')
                result['owner_view_restored'] = True
            assert all(sha(ROOT / n) == seal for n, seal in protected.items())
        except Exception:
            result['cleanup_failure'] = traceback.format_exc()
            result['accepted'] = False
        persist()
    print(json.dumps(dict(accepted=result['accepted'], steps=len(result['steps']), selections=len(result['selections']),
                          captures=len(result['captures']), failure=result.get('failure', '').splitlines()[-1:],
                          cleanup_failure=result.get('cleanup_failure', '').splitlines()[-1:])), flush=True)
    return 0 if result['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
