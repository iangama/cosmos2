"""Two explicit phases around a normal candidate shutdown and fresh boot."""
from pathlib import Path
import hashlib
import json
import sys
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1];V04='--v04' in sys.argv;CANDIDATE=ROOT/('output/c212-em-v04-product' if V04 else 'output/c212-em-product');STORAGE=CANDIDATE/'c212-em-worker/product'
sys.path.insert(0,str(CANDIDATE/'em'));sys.path.insert(0,str(CANDIDATE/'app'))
from em_experiment import Experiment,canonical
from em_native import normalize
expected_path=ROOT/('output/c212-em-v04-restart-expected.json' if V04 else 'output/c212-em-restart-expected.json');checkpoint=STORAGE/'ui-phase.json';adjunct=STORAGE/'ui-phase.view.json'
owner=ROOT/'user/sessions/latest.json';original=owner.read_bytes()
if '--prepare' in sys.argv:
    ex=Experiment.load(checkpoint);view=json.loads(adjunct.read_bytes())['payload']
    assert view['checkpoint_sha256']==hashlib.sha256(checkpoint.read_bytes()).hexdigest()
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
        assert page.evaluate('map===null&&fieldLines===null'),'Derived frozen layers must not be mislabeled as newly computed'
        assert not errors,errors;assert owner.read_bytes()==original
        report={'status':'candidate_EM_science_history_selection_visual_and_native_view_survive_normal_restart',
                'checkpoint_sha256':expected['checkpoint_sha256'],'native_view_adjunct_sha256':expected['adjunct_sha256'],
                'exact_science_and_editor_after_fresh_boot':True,'stale_maps_and_lines_cleared':True,'javascript_errors':errors,
                'owner_pointer_preserved':True,'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (CANDIDATE/'app/em_laboratory.py',CANDIDATE/'app/em_native.py',Path(__file__))},
                'scope':'Separate EM checkpoint/native view in candidate storage. No owner/gravitational Session conversion; full camera pose roundtrip also has an independent native resilience receipt.'}
        (ROOT/('evidence/em-v04-restart-check.json' if V04 else 'evidence/em-restart-check.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    finally:
        page.call('Page.navigate',{'url':previous});page.wait_for_function('location.href==='+json.dumps(previous)+'&&document.readyState==="complete"')
