"""Small real-window admission gate before the full sixteen-center native journey."""
import argparse
import hashlib
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path
import time
import traceback
import urllib.error
import urllib.request
from cef_page_v2 import Page

ROOT=Path(__file__).resolve().parents[1]
h=SourceFileLoader('dynamics16_admission_helpers',str(ROOT/'scripts/benchmark-body-points-native.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True);parser.add_argument('--version',required=True)
    args=parser.parse_args();assert args.version in ('0.26.0','0.26.1')
    assert args.label and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
    out=ROOT/f'evidence/is6-dynamics16-native-admission-{args.label}.json'
    assert not out.exists(),'Preserve admission evidence'
    app=ROOT/f'output/is6-dynamics16-product{args.version}/app'
    result=dict(completed=False,accepted=False,version=args.version,source_sha256={n:sha(app/n) for n in ['server.py','laboratory.py','worker.py','dynamics16_runtime.py','ui/solar.js']},script_sha256=sha(Path(__file__)))
    def persist():out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    persist();view_id=None
    try:
        session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
        assert Path(session['serverScript']).resolve()==app/'server.py'
        assert h.get('/api/state')['mode']=='atlas'
        favorites=h.get('/api/navigation/favorites')['views']
        views=h.post('/api/navigation/save',dict(name='Admissão16 temporária'))['navigation']['views']
        view_id=next(v['id'] for v in views if v['id'] not in {f['id'] for f in favorites})
        with Page() as page:
            page.wait_for_function('appState?.mode==="atlas"&&atlasState&&!pending&&!atlasPending')
            page.locator('#copy-sixteen').click()
            page.wait_for_function('!pending&&appState?.mode==="experiment"&&appState.physics.bodies.length===16',timeout=70000)
            physics=h.get('/api/state')['physics'];assert physics['paused'] and physics['time']==0
            result['native_creation']=dict(bodies=len(physics['bodies']),kind=physics['atlas_initial']['kind'],position_error_m=h.test.positions(physics))
            body=physics['bodies'][-1]
            payload=dict(command='dynamics16_reading',**h.test.guard(physics),body_id=body['id'])
            request=urllib.request.Request('http://127.0.0.1:4700/api/command',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
            try:
                with urllib.request.urlopen(request,timeout=30) as response:status=response.status;reading=json.load(response)
            except urllib.error.HTTPError as error:status=error.code;reading=json.load(error)
            result['real_laboratory_dispatch']=dict(status=status,response=reading)
            assert status==200 and len(reading['ack']['result']['sources'])==15,reading
            result.update(completed=True,accepted=True)
    except Exception:result['failure']=traceback.format_exc()
    finally:
        try:
            if h.get('/api/state')['mode']=='experiment':h.post('/api/command',dict(command='atlas'))
            if view_id:
                h.post('/api/navigation/restore',dict(id=view_id));h.post('/api/navigation/delete',dict(id=view_id))
                result['view_restored']=True
        except Exception:result['cleanup_failure']=traceback.format_exc();result['accepted']=False
        persist()
    print(json.dumps({k:result.get(k) for k in ['accepted','native_creation','failure','cleanup_failure']}),flush=True)
    return 0 if result['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
