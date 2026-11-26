"""Restore the same archived16/4 instruments in a new native process without rewriting checkpoints."""
import argparse
import copy
import hashlib
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path
import shutil
import time
import traceback
import zipfile

from PIL import Image
from cef_page_v2 import Page

ROOT = Path(__file__).resolve().parents[1]
base = SourceFileLoader('expanded_reopen_base', str(ROOT / 'scripts/verify-native-is6-expanded-journey.py')).load_module()
h, APP, sha = base.h, base.APP, base.sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    parser.add_argument('--seed-label', required=True)
    args = parser.parse_args()
    for label in [args.label, args.seed_label]:
        assert label and len(label) <= 24 and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label)
    folder = ROOT / f'output/is6-expanded-journey-reopen-{args.label}'
    out = ROOT / f'evidence/is6-expanded-journey-reopen-{args.label}.json'
    assert not folder.exists() and not out.exists()
    seed_path = ROOT / f'evidence/is6-expanded-journey-native-{args.seed_label}.json'
    lifecycle_path = ROOT / f'evidence/is6-expanded-journey-native-host-recovery-{args.seed_label}.json'
    seed, lifecycle = json.loads(seed_path.read_text()), json.loads(lifecycle_path.read_text())
    assert seed['accepted'] and seed['completed'] and lifecycle['accepted'] and lifecycle['completed']
    assert len(lifecycle['processes']) == 4 and set(lifecycle['processes'].values()) == {0}
    session = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
    assert session['app'] != seed['session']['app'] and Path(session['serverScript']).resolve() == APP / 'server.py'
    sources = dict(seed['source_sha256'])
    for path in [Path(__file__), seed_path, lifecycle_path, ROOT / 'scripts/run-is6-expanded-reopen.py']:
        sources[path.relative_to(ROOT).as_posix()] = sha(path)
    stored = {row['original']: row['sha256'] for row in seed['archives']}
    assert all(sha(ROOT / name) == seal for name, seal in {**sources, **stored}.items())
    folder.mkdir()
    with zipfile.ZipFile(folder / 'executed-sources-and-records.zip', 'x', zipfile.ZIP_DEFLATED) as archive:
        for name in {**sources, **stored}:
            archive.write(ROOT / name, name)
    result = dict(accepted=False, completed=False, session=session, source_sha256=sources,
                  archive_sha256=sha(folder / 'executed-sources-and-records.zip'), stored_sha256=stored,
                  protected_sha256=seed['protected_sha256'], steps=[], captures=[], cleanups=[], refusals=[], page_errors=[],
                  scope='New native process, archived16 and one restored live4 phase across archived layers, particles and nuclear zone; stored files stay byte-identical. Visual review and own residency remain separate.')
    original_id = None
    def persist():
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')
    def passed(name):
        result['steps'].append(name)
        persist()
        print(json.dumps(dict(progress=name), ensure_ascii=False), flush=True)
    def state(name):
        return h.get('/api/' + name + '/state')
    def click(page, selector, timeout=70000):
        page.evaluate('(()=>{const e=document.querySelector(' + json.dumps(selector) + ');if(e?.closest("#lab-panel")&&getComputedStyle($("lab-panel")).display==="none"&&document.body.classList.contains("details-open"))$("panel-toggle").click();for(let p=e?.parentElement;p;p=p.parentElement)if(p.tagName==="DETAILS")p.open=true;})()')
        page.wait_for_function('document.querySelector(' + json.dumps(selector) + ')&&!document.querySelector(' + json.dumps(selector) + ').matches(":disabled")', timeout=timeout)
        page.locator(selector).click()
        page.wait_for_function('!pending&&!layerInstrument.pending&&!layerInstrument.snapshot?.busy&&!particlePending&&!solarZonePending', timeout=timeout)
    def same_phase():
        assert base.physical(h.get('/api/state')['physics']) == common4
    def cleanup(nodes, before):
        absent = h.native('local r={};for _,n in ipairs(' + base.lua(list(dict.fromkeys(nodes))) + ') do r[n]=openspace.hasSceneGraphNode(n) end;return r')
        assert not any(absent.values())
        after = base.context(live4)
        base.same_context(before, after)
        same_phase()
        result['cleanups'].append(dict(nodes=absent, before=before, after=after))
    def refused(name, path, payload):
        phase = base.physical(h.get('/api/state')['physics'])
        context = base.context(h.get('/api/state')['physics'])
        answer = base.post(path, payload, expected=400)
        assert answer['ok'] is False and base.physical(h.get('/api/state')['physics']) == phase
        base.same_context(context, base.context(h.get('/api/state')['physics']))
        result['refusals'].append(dict(name=name, error=answer['error']))
        persist()
    def capture(page, name, scale, focus):
        page.locator('#ui-scale').select_option(scale)
        page.evaluate('(()=>{const e=document.getElementById(' + json.dumps(focus) + ');if(e.closest("#lab-panel")&&document.body.classList.contains("details-open"))$("panel-toggle").click();for(let p=e.parentElement;p;p=p.parentElement)if(p.tagName==="DETAILS")p.open=true;e.scrollIntoView({block:"start"});})()')
        time.sleep(.5)
        previous = set((ROOT / 'user/screenshots').rglob('*.png'))
        h.native('openspace.takeScreenshot();return {requested=true}')
        deadline = time.monotonic() + 20
        while True:
            fresh = set((ROOT / 'user/screenshots').rglob('*.png')) - previous
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
                raise TimeoutError('Native PNG incomplete')
            time.sleep(.1)
        target = folder / (str(len(result['captures']) + 1).zfill(2) + '-' + name + '-' + str(int(float(scale) * 100)) + '.png')
        shutil.copy2(source, target)
        assert sha(source) == sha(target)
        result['captures'].append(dict(path=target.relative_to(ROOT).as_posix(), sha256=sha(target), native_original=source.relative_to(ROOT).as_posix(), name=name, scale=scale, method='Unedited original OpenSpace framebuffer'))
        persist()
    def particle_ready(page):
        page.wait_for_function('particleState.active&&!particlePending&&particleState.worker.paused&&!particleState.view.pending_sequence&&particleState.worker.experiment.phase.time_s===particleState.view.confirmed_phase.time_s', timeout=30000)
        value = state('particles')
        assert not value['error']
        return value
    persist()
    try:
        with Page() as page:
            page.on('pageerror', lambda error: result['page_errors'].append(error))
            page.wait_for_function('appState?.mode==="atlas"&&layerInstrument.snapshot&&particleState&&solarZoneState&&!pending')
            result['original_navigation'] = h.get('/api/navigation/state')
            result['original_favorites'] = h.get('/api/navigation/favorites')['views']
            favorites = h.post('/api/navigation/save', dict(name='Retorno após reabertura ampliada'))['navigation']['views']
            original_id = next(v['id'] for v in favorites if v['id'] not in {a['id'] for a in result['original_favorites']})
            click(page, '#copy-solar')
            click(page, '#load')
            restored16 = h.get('/api/state')['physics']
            saved16 = seed['checkpoint16']
            for key in ['bodies', 'time', 'revision', 'atlas_initial', 'dynamics16', 'interventions']:
                assert restored16[key] == saved16[key], key
            assert restored16['edit_token'] != saved16['edit_token']
            result['geometry16'] = base.geometry(restored16)
            page.locator('#solar-body').select_option(restored16['bodies'][-1]['id'])
            click(page, '#solar-view-body')
            click(page, '#solar-sample')
            assert len(page.evaluate('solarReading')['sources']) == 15
            for scale in ['1', '1.5']:
                capture(page, 'checkpoint16-new-process', scale, 'solar-body')
            page.locator('#ui-scale').select_option('1')
            page.locator('#branch-first').select_option(seed['four_branch'])
            click(page, '#branch-load')
            live4 = copy.deepcopy(h.get('/api/state')['physics'])
            assert len(live4['bodies']) == 4 and live4['paused']
            for key in ['bodies', 'time', 'revision', 'atlas_initial', 'interventions']:
                assert live4[key] == seed['common_source_phase4'][key]
            assert live4['edit_token'] != seed['common_source_phase4']['edit_token']
            common4 = base.physical(live4)
            result['common_live_phase4'] = live4
            passed('New process exact16 and archived4 branch with renewed edit identities')
            for naif in ['399', '599']:
                checkpoint = seed['instrument_checkpoints'][naif]
                before = base.context(live4)
                click(page, '#open-layers')
                click(page, '#layers-load-saved')
                old_guard = state('layers')['guard']
                page.locator('#layers-branches').select_option(checkpoint['layer_branch'])
                click(page, '#layers-branch-load')
                layer = state('layers')
                assert layer['active'] and layer['artifact']['archived'] and layer['artifact']['sha256'] == checkpoint['layer_sha256']
                scientific = h.post('/api/layers/command', dict(command='get_artifact', guard=layer['guard']))['result']['scientific']
                assert scientific == checkpoint['layer_scientific']
                assert layer['artifact']['live_source_guard'] == base.contract.artifact.body.guard(live4)
                drawing = base.body_field_scene.build(scientific['magnetic'])
                expected_point = base.body_field_scene.product(drawing['body_to_render'], drawing['point_model_m'])
                native_point = h.native('return openspace.propertyValue("Scene.' + layer['scene']['magnetic_frame'] + '_probe.Translation.Position")')
                assert max(abs(x - y) for x, y in zip(native_point, expected_point, strict=True)) <= .001
                refused('Old layer guard ' + naif, '/api/layers/command', dict(command='get_artifact', guard=old_guard))
                for scale in ['1', '1.5']:
                    capture(page, 'archived-layers-' + naif, scale, 'layers-spatial-reading')
                page.locator('#ui-scale').select_option('1')
                scene = state('layers')['scene']
                click(page, '#layers-leave')
                cleanup([scene['spatial_frame'], scene['spatial_wire'], scene['spatial_frame'].replace('SpatialFrame_', 'SpatialFocus_'), scene['magnetic_frame'], *scene['magnetic_nodes'], *[scene['magnetic_frame'] + s for s in ['_basis', '_probe', '_display_probe']]], before)
                click(page, '#layers-panel-close')
                before = base.context(live4)
                click(page, '#particle-load-saved')
                particle = particle_ready(page)
                stale_guard = base.ParticleClient.guard(particle['worker'])
                page.locator('#particle-branch-select').select_option(checkpoint['particle_branch'])
                click(page, '#particle-branch-load')
                particle = particle_ready(page)
                assert particle['worker']['experiment']['phase'] == checkpoint['particle_phase']
                refused('Old particle guard ' + naif, '/api/particles/command', dict(command='sample', guard=stale_guard))
                for scale in ['1', '1.5']:
                    capture(page, 'archived-particle-' + naif, scale, 'particle-title')
                page.locator('#ui-scale').select_option('1')
                nodes = state('particles')['view']['native_nodes']
                click(page, '#particle-leave')
                cleanup(list(nodes.values()), before)
                same_phase()
                passed('Archived layer and particle ' + naif + ' restore/guards/native cleanup on same live4')
            before = base.context(live4)
            click(page, '#zone-load-saved', timeout=750000)
            page.wait_for_function('solarZoneState.active&&!solarZonePending&&!solarZoneState.busy&&!solarZoneCurvePending&&solarZoneCurveId===solarZoneState.worker.artifact_id', timeout=750000)
            zone = state('solar-zone')
            for key in ['artifact_id', 'artifact_sha256', 'sample', 'source']:
                assert zone['worker'][key] == seed['solar_checkpoint'][key], key
            assert zone['worker']['configuration']['acting']['weak']
            for scale in ['1', '1.5']:
                capture(page, 'archived-nuclear18', scale, 'zone-probe')
            page.locator('#ui-scale').select_option('1')
            nodes = state('solar-zone')['scene']
            click(page, '#zone-leave')
            cleanup([nodes['node'], nodes['label_node']], before)
            passed('Archived nuclear18 exact artifact/sample/source; live4 preserved')
            click(page, '#load')
            final16 = h.get('/api/state')['physics']
            for key in ['bodies', 'time', 'revision', 'atlas_initial', 'dynamics16', 'interventions']:
                assert final16[key] == saved16[key], key
            refused('Old live4 guard after16 restore', '/api/command', dict(command='solar_reading', **base.guard(live4), body_id=live4['bodies'][1]['id']))
            page.locator('#solar-body').select_option(final16['bodies'][-1]['id'])
            click(page, '#solar-view-body')
            click(page, '#solar-sample')
            assert len(page.evaluate('solarReading')['sources']) == 15
            for scale in ['1', '1.5']:
                capture(page, 'final16-after-reopened-instruments', scale, 'solar-body')
            click(page, '#atlas')
            assert all(sha(ROOT / name) == seal for name, seal in {**sources, **stored, **result['protected_sha256']}.items())
            assert not result['page_errors']
            result.update(accepted=True, completed=True, stored_unchanged=True)
            passed('Return16 exact; original checkpoints/branches/exports byte-identical')
    except Exception:
        result['failure'] = traceback.format_exc()
    finally:
        try:
            for name in ['solar-zone', 'particles', 'layers', 'spatial']:
                current = state(name)
                if current['active'] or current.get('recovery_required'):
                    request = dict(command='leave')
                    if name == 'solar-zone':
                        request['guard'] = base.SolarClient.guard(current['worker'])
                    elif name in ['layers', 'spatial']:
                        request['guard'] = current['guard']
                    base.post('/api/' + name + '/command', request)
            if h.get('/api/state')['mode'] == 'experiment':
                h.post('/api/command', dict(command='atlas'))
            if original_id:
                restored = h.post('/api/navigation/restore', dict(id=original_id))['navigation']
                h.post('/api/navigation/delete', dict(id=original_id))
                assert restored['et'] == result['original_navigation']['et']
                assert h.get('/api/navigation/favorites')['views'] == result['original_favorites']
                with Page() as page:
                    page.locator('#ui-scale').select_option('1')
                    page.evaluate('selectTarget(' + json.dumps(restored['target']) + ',true)')
                result['owner_view_restored'] = True
        except Exception:
            result['cleanup_failure'] = traceback.format_exc()
            result['accepted'] = False
        persist()
    print(json.dumps(dict(accepted=result['accepted'], captures=len(result['captures']), steps=result['steps'], failure=result.get('failure'), cleanup_failure=result.get('cleanup_failure'))), flush=True)
    return 0 if result['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
