"""I real CEF source operations, genuine legacy view and real partial-save IO."""
from pathlib import Path
from copy import deepcopy
import argparse
import hashlib
import json
import math
import shutil
import subprocess
import time
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1];H=ROOT/'output/c212-em-viewport-product'
parser=argparse.ArgumentParser();parser.add_argument('--label',default='initial');args=parser.parse_args()
assert args.label.isalnum()
dest=ROOT/f'evidence/em-viewport-cloud-ui-{args.label}-check.json';assert not dest.exists()
session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
assert session.get('emViewportCandidate') and Path(session['serverScript']).resolve()==(H/'app/server.py').resolve()
storage=H/'c212-em-cloud-worker/product';owner=(ROOT/'user/sessions/latest.json').read_bytes()
report={'completed':False,'checks':[],'JS_errors':[]}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def idle(p):p.wait_for_function('state&&state.paused&&!pending&&!native.error&&native.confirmation?.metadata.time_s===state.time_s&&native.confirmation.metadata.system_id===state.system_id',timeout=30000)
def snap(p):return p.evaluate('JSON.parse(JSON.stringify(state))')
def panel(p,name):
    if p.evaluate('cloudPanel')!=name:p.locator('[data-cloud-panel="'+name+'"]').click()
def click(p,name):
    parent=p.evaluate('document.getElementById('+json.dumps(name)+').closest("[data-workspace-panel]")?.dataset.workspacePanel||null')
    if parent:panel(p,parent)
    p.locator('#'+name).click();idle(p)
def fill(p,values):p.evaluate('Object.entries('+json.dumps(values)+').forEach(([k,v])=>document.getElementById(k).value=String(v))')
def cmd(p,name,values={}):return p.evaluate('command('+json.dumps(name)+','+json.dumps(values)+')')
def invariant(a,b):
    for k in ('phase_sha256','time_s','dt_s','controls','count'):assert a[k]==b[k],k
def refused(p,name,values):
    before=snap(p)
    r=p.evaluate('(async()=>{const r=await fetch("/api/em-cloud/command",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({command:'+json.dumps(name)+',...guard(),...'+json.dumps(values)+'})});return {status:r.status,body:await r.json()};})()')
    assert r['status']==400,r
    p.evaluate('refresh(true)');after=snap(p)
    for k in ('phase_sha256','time_s','model','revision','edit_token'):assert before[k]==after[k],k
    return r['body']['error']
try:
    with Page() as p:
        p.on('pageerror',lambda e:report['JS_errors'].append(e));p.goto('http://127.0.0.1:4700/')
        p.wait_for_function('typeof appState!=="undefined"&&appState');p.locator('#em-cloud-lab').click();idle(p)
        p.locator('#interface-scale').select_option('1');panel(p,'experience')
        p.locator('#count').select_option('128');p.locator('#preset').select_option('helix');click(p,'load-preset')
        before=snap(p);panel(p,'sources')
        fill(p,{'field-source-id':'fonte-prova','field-source-x':8,'field-source-y':1,'field-source-z':-2,
                'field-source-charge':1e-12,'field-source-radius':.02,'field-moment-x':10000,'field-moment-y':-20000,'field-moment-z':30000})
        time.sleep(.4);assert snap(p)['model']==before['model'] and p.evaluate('$("field-source-x").value')=='8'
        click(p,'apply-field-source');created=snap(p);invariant(before,created)
        assert created['revision']==before['revision']+1 and p.evaluate('visual.selected_source_id')=='fonte-prova'
        assert created['model']['sources'][0]['charge_C']==1e-12
        click(p,'measure');assert p.evaluate('fieldMap.measurement.samples.length')==97
        panel(p,'sources');fill(p,{'field-source-charge':-2e-12});before=snap(p);click(p,'apply-field-source')
        invariant(before,snap(p));assert p.evaluate('fieldMap') is None
        reading=cmd(p,'probe',{'position_m':[3,2,1]})['result'];source=snap(p)['model']['sources'][0]
        constants=json.loads((H/'em-cloud/constants.json').read_bytes());ke=1/(4*math.pi*constants['vacuum_electric_permittivity_F_m']['value']);mu=constants['vacuum_magnetic_permeability_N_A2']['value']/(4*math.pi)
        d=[a-b for a,b in zip([3,2,1],source['position_m'])];r=math.hypot(*d);m=source['magnetic_moment_A_m2'];dot=math.fsum(a*b for a,b in zip(d,m))
        expectedE=[ke*source['charge_C']*v/r**3 for v in d];expectedB=[mu*(3*d[k]*dot/r**5-m[k]/r**3)+(1 if k==2 else 0) for k in range(3)]
        assert math.dist(reading['electric_field_V_m'],expectedE)<1e-15 and math.dist(reading['magnetic_field_T'],expectedB)<1e-15
        before=snap(p);click(p,'remove-field-source');invariant(before,snap(p));assert not snap(p)['model']['sources'] and p.evaluate('visual.selected_source_id') is None
        report['checks'].append('Real source form draft/create/edit/remove preserves phase and changes one revision; map invalidation and independent SI E/B passed.')

        sources=[{'id':'s'+str(i),'position_m':[8+float(i),1.,-2.],'charge_C':1e-12,'exclusion_radius_m':.02,'magnetic_moment_A_m2':[1e4,-2e4,3e4]} for i in range(128)]
        model={**snap(p)['model'],'sources':sources};before=snap(p);cmd(p,'set_model',{'model':model});invariant(before,snap(p));idle(p)
        p.locator('#field-source').select_option('s127');idle(p)
        assert p.evaluate('visual.selected_source_id')=='s127'
        click(p,'remove-field-source');assert len(snap(p)['model']['sources'])==127
        fill(p,{'field-source-id':'s127','field-source-x':135,'field-source-y':1,'field-source-z':-2});click(p,'apply-field-source')
        p.locator('#field-source').select_option('');idle(p);assert p.evaluate('$("apply-field-source").disabled')
        errors=[];model=snap(p)['model']
        for bad in [model['sources']+[sources[0]], [sources[0],sources[0]], [{**sources[0],'exclusion_radius_m':-1}],
                    [{**sources[0],'position_m':snap(p)['selected_particle']['position_m']}]]:
            errors.append(refused(p,'set_model',{'model':{**model,'sources':bad}}))
        for selected in ('missing',True,'x'*129):errors.append(refused(p,'set_visual',{'changes':{'selected_source_id':selected}}))
        report['refusals']=errors;report['checks'].append('128 source limit, visible selection/deletion/recreation, duplicate/exclusion/radius and invalid selection are atomic.')

        cmd(p,'set_visual',{'changes':{'selected_source_id':'s17','electric_visible':False}});cmd(p,'set_rate',{'value':.5})
        saved=cmd(p,'save',{'file':'ui-phase'});assert saved['persistence']['state']=='complete' and saved['persistence']['view_preferences_saved']
        assert sha(storage/'ui-phase.view.json')==saved['preferences_artifact']['sha256']
        expected=snap(p);view=p.evaluate('JSON.parse(JSON.stringify(visual))');click(p,'step');click(p,'restore')
        for k in ('phase_sha256','time_s','model','controls','dt_s','requested_model_s_per_wall_s','selected_particle'):assert snap(p)[k]==expected[k],k
        assert p.evaluate('visual')==view
        # Actual legacy output from G, copied read-only into H's own storage.
        legacy=sorted((ROOT/'output/c212-em-integration-product/c212-em-cloud-worker/product').glob('*.view.json'))[0]
        for ending in ('.json','.view.json'):
            original=legacy.with_name(legacy.name[:-10]+ending);shutil.copyfile(original,storage/('h-legacy'+ending))
        legacy_hash=sha(storage/'h-legacy.view.json');loaded=cmd(p,'load',{'file':'h-legacy'});idle(p)
        assert loaded['view_preferences_source_schema']==1 and p.evaluate('visual.selected_source_id') is None
        assert p.evaluate('$("count").value')==str(snap(p)['count'])
        assert sha(storage/'h-legacy.view.json')==legacy_hash
        assert 'nenhuma fonte' in p.locator('#status').inner_text()
        report['legacy_source']={'path':str(legacy.relative_to(ROOT)),'sha256':legacy_hash}
        report['checks'].append('Complete save flags/hash and same-process restore passed; genuine G schema1 loads explicitly with no selected source, without rewriting it.')

        cmd(p,'load',{'file':'ui-phase'});idle(p);assert p.evaluate('$("count").value')=='128';click(p,'step')
        # A real directory collision refuses only the view-file replace.
        view_path=storage/'ui-phase.view.json';backup=storage/'h-partial-view-backup.json'
        assert not backup.exists();view_path.rename(backup);view_path.mkdir()
        try:
            click(p,'save');message=p.locator('#status').inner_text()
            assert 'Fase salva; vista e preferências incompletas' in message,message
            assert p.evaluate('native.error') is None
            phase=json.loads((storage/'ui-phase.json').read_bytes());assert phase['phase']['time_s']==snap(p)['time_s']
            report['real_IO_partial_save']={'message':message,'scientific_checkpoint_sha256':sha(storage/'ui-phase.json'),'native_error':None}
        finally:
            view_path.rmdir();backup.rename(view_path)
        click(p,'save');assert 'preferências salvas' in p.locator('#status').inner_text()
        report['checks'].append('Real view-file IO refusal leaves a valid new scientific checkpoint, reports partial in the visible button flow and keeps native scene healthy; next save recovers.')
        layouts=[]
        for zoom in (1,1.5):
            p.locator('#interface-scale').select_option(str(zoom))
            for name in ('experience','sources','layers','readings'):
                panel(p,name)
                v=p.evaluate('(()=>{const z=Number(getComputedStyle(document.body).zoom)||1,a=document.querySelector("article").getBoundingClientRect(),b=$("play").getBoundingClientRect();return {panels:document.querySelectorAll("[data-workspace-panel]:not([hidden])").length,scene_fraction:a.width*z/innerWidth,overflow:document.documentElement.scrollWidth>innerWidth+1,pause_visible:b.top*z>=0&&b.bottom*z<=innerHeight};})()')
                assert v['panels']==1 and v['scene_fraction']>=.65 and not v['overflow'] and v['pause_visible'],(zoom,name,v)
                layouts.append({'zoom':zoom,'panel':name,**v})
            panel(p,'sources');p.evaluate('document.querySelectorAll("aside").forEach(a=>a.scrollTop=0)')
            subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name',f'cosmos2-em-viewport-cloud-{args.label}-zoom{int(zoom*100)}.png'],check=True,capture_output=True)
        p.locator('#interface-scale').select_option('1');report['layouts']=layouts
        report['checks'].append('All four panels keep scene >=65%, fixed pause and no horizontal overflow at100/150%; screenshots await visual review.')
        current=snap(p);cmd(p,'save',{'file':'ui-phase'})
        (ROOT/'output/em-viewport-cloud-restart-expected.json').write_text(json.dumps({'state':current,'visual':p.evaluate('visual'),'files_sha256':{suffix:sha(storage/('ui-phase'+suffix)) for suffix in ('.json','.view.json')}},indent=2)+'\n')
        p.locator('#return').click();p.wait_for_function('location.pathname==="/"');assert not report['JS_errors'],report['JS_errors']
        assert (ROOT/'user/sessions/latest.json').read_bytes()==owner
        report.update(completed=True,owner_pointer_preserved=True,scope='I real CEF source editing, guarded refusals, actual legacy and IO; screenshots and normal restart/performance require separate acceptance.')
finally:
    report['source_sha256']={str(f.relative_to(ROOT)).replace('\\','/'):sha(f) for f in [Path(__file__),*sorted((H/'app').rglob('*'))] if f.is_file() and '__pycache__' not in f.parts}
    dest.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'completed':report['completed'],'checks':len(report['checks']),'JS_errors':report['JS_errors']}),flush=True)
