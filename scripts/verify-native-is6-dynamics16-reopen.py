"""Restore the saved sixteen-center phase through CEF after the whole app has reopened."""
import argparse
import hashlib
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path
import sys
import traceback

from cef_page_v2 import Page

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is6-dynamics16-product0.26.2/app';sys.path.insert(0,str(APP))
from session import Session
h=SourceFileLoader('dynamics16_reopen_helpers',str(ROOT/'scripts/benchmark-body-points-native.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);parser.add_argument('--profile-label',required=True);args=parser.parse_args()
    assert args.label and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
    out=ROOT/f'evidence/is6-dynamics16-reopen-{args.label}.json';assert not out.exists()
    profile_path=ROOT/f'evidence/is6-dynamics16-profile-{args.profile_label}.json';profile=json.loads(profile_path.read_text())
    audit=ROOT/f'evidence/is6-dynamics16-profile-audit-v2-{args.profile_label}.json';assert json.loads(audit.read_text())['accepted']
    current=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
    assert current['app']!=profile['session']['app'] and Path(current['serverScript']).resolve()==APP/'server.py'
    storage=APP.parent/'gravity-sessions';pointer=storage/'latest.json';pointer_before=sha(pointer)
    expected=Session(ROOT/f'output/is6-dynamics16-reopen-{args.label}/read-only-model');expected.load(storage);expected_state=expected.state()
    assert len(expected_state['bodies'])==16 and expected_state['dynamics16']
    record=dict(accepted=False,completed=False,script_sha256=sha(Path(__file__)),profile_sha256=sha(profile_path),
        checkpoint_pointer_sha256=pointer_before,previous_app=profile['session']['app'],new_app=current['app'])
    def persist():out.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    view_id=None;persist()
    try:
        assert h.get('/api/state')['mode']=='atlas'
        before=h.get('/api/navigation/favorites')['views'];saved=h.post('/api/navigation/save',dict(name='Reabertura16 temporária'))['navigation']['views']
        view_id=next(r['id'] for r in saved if r['id'] not in {b['id'] for b in before})
        with Page() as page:
            page.wait_for_function('appState?.mode==="atlas"&&!pending')
            page.locator('#experiment').click();page.wait_for_function('appState?.mode==="experiment"&&!pending',timeout=70000)
            page.locator('#load').click();page.wait_for_function('appState?.mode==="experiment"&&appState.physics.bodies.length===16&&!pending',timeout=70000)
            live=h.get('/api/state')['physics']
            assert live['paused'] and live['time']==expected.sim.t and live['revision']==expected.revision
            assert live['bodies']==expected_state['bodies'] and live['atlas_initial']==expected.atlas_initial
            assert live['dynamics16']==expected_state['dynamics16'] and live['restoration']['status']=='same_generation'
            record['maximum_position_error_m']=h.test.positions(live)
            record['readings']=[]
            page.evaluate('$("solar-panel").open=true')
            for ref in ['sol:naif:399','sol:naif:599','sol:naif:606']:
                body=next(b for b in live['bodies'] if b['reference_id']==ref)
                page.locator('#solar-body').select_option(body['id']);page.locator('#solar-sample').click()
                page.wait_for_function('!pending&&solarReading?.body_id==='+json.dumps(body['id']),timeout=70000)
                read=page.evaluate('solarReading');assert len(read['sources'])==15 and read['edit_token']==live['edit_token']
                record['readings'].append(dict(body=ref,sources=15))
            record['exact_phase_reopened']=True
        record.update(accepted=True,completed=True)
    except Exception:record['failure']=traceback.format_exc()
    finally:
        try:
            if h.get('/api/state')['mode']=='experiment':h.post('/api/command',dict(command='atlas'))
            if view_id:
                restored=h.post('/api/navigation/restore',dict(id=view_id))['navigation'];h.post('/api/navigation/delete',dict(id=view_id))
                with Page() as page:page.evaluate('selectTarget('+json.dumps(restored['target'])+',true)')
            assert h.get('/api/navigation/favorites')['views']==before and sha(pointer)==pointer_before
            assert h.native('return openspace.hasSceneGraphNode("LabRoot")') is False
            record.update(checkpoint_unmodified=True,owner_view_restored=True,scene_cleaned=True,owner_app_kept_open=True)
        except Exception:record['cleanup_failure']=traceback.format_exc();record['accepted']=False
        persist()
    print(json.dumps(record,ensure_ascii=False),flush=True)
    return 0 if record['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
