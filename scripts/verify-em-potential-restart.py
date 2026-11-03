"""Two explicit phases around a normal candidate shutdown and fresh boot."""
from pathlib import Path
import hashlib
import json
import sys
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1];V04=True;TOPIC_CLEANUP='--topic-cleanup' in sys.argv;CANDIDATE=ROOT/('output/c212-em-cloud-native-product' if TOPIC_CLEANUP else ('output/c212-em-potential-product' if V04 else 'output/c212-em-product'));STORAGE=CANDIDATE/'c212-em-worker/product'
sys.path.insert(0,str(CANDIDATE/'em'));sys.path.insert(0,str(CANDIDATE/'app'))
from em_experiment import Experiment,canonical
from em_native import normalize
expected_path=ROOT/('output/c212-em-potential-topic-cleanup-restart-expected.json' if TOPIC_CLEANUP else ('output/c212-em-potential-restart-expected.json' if V04 else 'output/c212-em-restart-expected.json'));checkpoint=STORAGE/'ui-phase.json';adjunct=STORAGE/'ui-phase.view.json'
session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
assert Path(session['serverScript']).resolve()==(CANDIDATE/'app/server.py').resolve()
if TOPIC_CLEANUP:
    runtime_receipt=json.loads((ROOT/'evidence/built-runtime-topic-cleanup.json').read_bytes())
    assert hashlib.sha256((Path(session['runtime'])/'bin/OpenSpace.exe').read_bytes()).hexdigest()==runtime_receipt['engine_sha256']
owner=ROOT/'user/sessions/latest.json';original=owner.read_bytes()
if '--prepare' in sys.argv:
    ex=Experiment.load(checkpoint);view=json.loads(adjunct.read_bytes())['payload']
    assert view['checkpoint_sha256']==hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    assert view['view']['schema']==2
    expected={'science':ex.payload(),'editor':ex.editor,'view':view['view'],'checkpoint_sha256':view['checkpoint_sha256'],
              'adjunct_sha256':hashlib.sha256(adjunct.read_bytes()).hexdigest(),'owner_sha256':hashlib.sha256(original).hexdigest()}
    expected_path.write_bytes(canonical(expected));print(json.dumps({'prepared_restart_reference':True,'checkpoint_sha256':expected['checkpoint_sha256']}));raise SystemExit(0)

expected=json.loads(expected_path.read_bytes());assert hashlib.sha256(original).hexdigest()==expected['owner_sha256'];errors=[]
with Page() as page:
    previous=page.evaluate('location.href');page.on('pageerror',lambda e:errors.append(e))
    try:
        page.locator('#em-lab').click();page.wait_for_function('location.pathname==="/em.html"&&nativeState?.confirmation?.state==="accepted"&&!pending',timeout=30000)
        token=page.evaluate('state.edit_token');page.locator('#restore').click();page.wait_for_function('!pending&&state.edit_token!=='+json.dumps(token),timeout=30000)
        assert page.evaluate('state.experiment')==expected['science'] and page.evaluate('state.editor')==expected['editor']
        assert hashlib.sha256(checkpoint.read_bytes()).hexdigest()==expected['checkpoint_sha256'] and hashlib.sha256(adjunct.read_bytes()).hexdigest()==expected['adjunct_sha256']
        assert page.evaluate('map===null&&fieldLines===null&&potentialLayer===null'),'Derived frozen layers must not be mislabeled as newly computed'
        assert page.evaluate('nativeState.potential.settings')==expected['view']['potential'] and page.evaluate('nativeState.potential.render===null')
        assert not errors,errors;assert owner.read_bytes()==original
        report={'status':'candidate_EM_potential_visual2_settings_and_science_survive_normal_restart',
                'checkpoint_sha256':expected['checkpoint_sha256'],'native_view_adjunct_sha256':expected['adjunct_sha256'],
                'exact_science_and_editor_after_fresh_boot':True,'stale_maps_lines_and_potential_cleared':True,'exact_potential_visual_settings':expected['view']['potential'],'javascript_errors':errors,
                'owner_pointer_preserved':True,'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (CANDIDATE/'app/em_laboratory.py',CANDIDATE/'app/em_native.py',Path(__file__))},
                'scope':'Separate EM checkpoint/native view in candidate storage. No owner/gravitational Session conversion; full camera pose roundtrip also has an independent native resilience receipt.'}
        if TOPIC_CLEANUP:report['engine_sha256']=runtime_receipt['engine_sha256']
        destination=ROOT/('evidence/em-potential-topic-cleanup-restart-check.json' if TOPIC_CLEANUP else ('evidence/em-potential-restart-check.json' if V04 else 'evidence/em-restart-check.json'))
        if TOPIC_CLEANUP:assert not destination.exists()
        destination.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    finally:
        page.call('Page.navigate',{'url':previous});page.wait_for_function('location.href==='+json.dumps(previous)+'&&document.readyState==="complete"')
