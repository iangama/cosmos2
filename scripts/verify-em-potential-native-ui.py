"""Real CEF/native equipotentials, independent SI assets, guards and persistence."""
from pathlib import Path
import argparse
from copy import deepcopy
import hashlib
import itertools
import json
import math
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
import numpy as np
from cef_page import Page
from websockets.sync.client import connect

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--topic-cleanup',action='store_true');args=parser.parse_args()
CANDIDATE=ROOT/('output/c212-em-cloud-native-product' if args.topic_cleanup else 'output/c212-em-potential-product');STORAGE=CANDIDATE/'c212-em-worker/product'
destination=ROOT/('evidence/em-potential-topic-cleanup-native-ui-check.json' if args.topic_cleanup else 'evidence/em-potential-native-ui-check.json')
if args.topic_cleanup:assert not destination.exists()
session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
assert Path(session['serverScript']).resolve()==(CANDIDATE/'app/server.py').resolve()
runtime_receipt=json.loads((ROOT/('evidence/built-runtime-topic-cleanup.json' if args.topic_cleanup else 'evidence/built-runtime-cloud.json')).read_bytes())
assert hashlib.sha256((Path(session['runtime'])/'bin/OpenSpace.exe').read_bytes()).hexdigest()==runtime_receipt['engine_sha256']
sys.path.insert(0,str(CANDIDATE/'app'));from em_native import normalize
owner=ROOT/'user/sessions/latest.json';original=owner.read_bytes();baseline=json.loads((ROOT/'evidence/c212-em-candidate-baseline.json').read_bytes())
errors=[];cases=[];geometry_checks=[];refusals=[];acting_combinations=[]
def get():return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/em/state',timeout=10))
def guard():
    s=get()['state'];return {k:s[k] for k in ('system_id','edit_token','revision','frame')}|{'expected_time_s':s['time_s']}
def command(name,error=False,**values):
    request=urllib.request.Request('http://127.0.0.1:4700/api/em/command',data=json.dumps({'command':name,**values},allow_nan=False).encode(),headers={'Content-Type':'application/json'})
    try:
        result=json.load(urllib.request.urlopen(request,timeout=20))
        assert not error,('Unexpected acceptance',result);return result
    except urllib.error.HTTPError as e:
        if not error:raise
        assert e.code==400;return json.load(e)
def core():
    s=get()['state'];return {k:s[k] for k in ('experiment','editor','revision','time_s')}
def matter():
    value=core();value['editor'].pop('visual');return value
ws=connect('ws://127.0.0.1:4682',open_timeout=3,close_timeout=.2,ping_interval=None,max_size=4*1024*1024);topic=0
ws.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
def native(code):
    global topic
    topic+=1;ws.send(json.dumps({'topic':topic,'type':'luascript','payload':{'script':code,'return':True}}));reply=json.loads(ws.recv(timeout=10));assert reply.get('topic')==topic
    return normalize(reply['payload']['1'])
def enabled(render):
    code='local values={};'
    for m in render['meshes']:code+='values['+json.dumps(m['node'])+']=openspace.propertyValue('+json.dumps('Scene.'+m['node']+'.Renderable.Enabled')+');'
    return native(code+'return {values=values}')['values']
def audit_mesh(layer,render,uniform=False):
    assert render['metadata']==layer['geometry']['metadata'] and render['layer_id']==layer['layer_id']
    maximum=voltage_error=0.;vertices=0
    for mesh in render['meshes']:
        file=Path(mesh['file']);raw=file.read_bytes();assert hashlib.sha256(raw).hexdigest()==mesh['file_sha256']
        rows=raw.decode().splitlines();paths=[]
        for i,row in enumerate(rows):
            if row.startswith('mesh '):
                count=int(rows[i+2]);assert count>=2;paths.append(np.array([[float(v) for v in r.split()] for r in rows[i+3:i+3+count]],dtype=np.float32).astype(float))
        assert len(paths)==mesh['curve_count']==len(mesh['curve_segment_indices']) and sum(map(len,paths))==mesh['vertex_count'];vertices+=mesh['vertex_count']
        assert sorted(i for ids in mesh['curve_segment_indices'] for i in ids)==sorted(mesh['segment_indices'])
        node=mesh['node'];actual=native('return {enabled=openspace.propertyValue('+json.dumps('Scene.'+node+'.Renderable.Enabled')+'),scale=openspace.propertyValue('+json.dumps('Scene.'+node+'.Scale.Scale')+'),position=openspace.propertyValue('+json.dumps('Scene.'+node+'.Translation.Position')+')}')
        assert actual['enabled'] is True and actual['scale']==mesh['local_unit_model_m']*1e9 and actual['position']==[v*1e9 for v in mesh['center_model_m']]
        error=0.
        for path,indices in zip(paths,mesh['curve_segment_indices']):
            si=path*(actual['scale']/1e9)+np.array(actual['position'])/1e9
            assert len(path)==len(indices)+1 and np.all(si[:,2]==layer['geometry']['grid']['z_m'])
            for j,index in enumerate(indices):
                segment=layer['geometry']['segments'][index];expected=np.array(segment['points_m']);pair=si[j:j+2]
                error=max(error,min(float(np.max(abs(pair-expected))),float(np.max(abs(pair[::-1]-expected)))))
                if uniform:
                    E=layer['source_snapshot']['model']['uniform_E_V_m']
                    voltage_error=max(voltage_error,max(abs(-math.fsum(a*b for a,b in zip(E,p))-segment['level_V']) for p in (*segment['points_m'],tuple(expected.mean(axis=0)))))
        assert error<=3e-7*mesh['local_unit_model_m']+1e-12;maximum=max(maximum,error)
    if uniform:assert voltage_error<1e-12
    geometry_checks.append({'sample_count':len(layer['measurement']['samples']),'levels':len(render['levels_V']),'segments':render['segment_count'],'vertices':vertices,'independent_native_transform_and_SM_SI_error_m':maximum,'uniform_potential_residual_V':voltage_error if uniform else None})
def missing(nodes):
    code='local missing=true;'
    for name in nodes:code+='missing=missing and not openspace.hasSceneGraphNode('+json.dumps(name)+');'
    return native(code+'return {missing=missing}')['missing']

try:
    with Page() as page:
        previous=page.evaluate('location.href');page.on('pageerror',lambda e:errors.append(e));page.goto('http://127.0.0.1:4700/')
        page.wait_for_function('typeof appState!=="undefined"&&appState!==null');page.locator('#em-lab').click()
        page.wait_for_function('location.pathname==="/em.html"&&nativeState?.confirmation?.state==="accepted"&&!pending',timeout=30000)
        def idle(expr='true'):page.wait_for_function('!pending&&('+expr+')',timeout=30000)
        def preset(name):
            old=page.evaluate('state.system_id');page.locator('#preset').select_option(name);page.locator('#load-preset').click();idle('state.system_id!=='+json.dumps(old))
        def measure():
            page.locator('#measure-potential').click();idle('potentialLayer!==null');return page.evaluate('potentialLayer'),get()['native']['potential']['render']
        preset('electric');before=core();physical_reference=matter();layer,render=measure();assert core()==before and render['sample_count']==1089 and not get()['native']['potential']['error']
        audit_mesh(layer,render,uniform=True);assert page.evaluate('document.getElementById("potential-legend").textContent.includes("percentis10 e90")')
        # E/B and potential visibility are independent, and none edits matter.
        page.locator('#measure').click();idle('map!==null')
        for e,b in itertools.product((False,True),repeat=2):
            page.locator('#visible-e').set_checked(e);idle();page.locator('#visible-b').set_checked(b);idle()
            assert all(enabled(render).values())
            assert matter()==physical_reference
        page.locator('#visible-potential').set_checked(False);idle('!nativeState.potential.settings.visible');assert not any(enabled(render).values()) and core()==before
        page.locator('#visible-potential').set_checked(True);idle('nativeState.potential.settings.visible');assert all(enabled(render).values())
        cases.append('uniform E analytic contours,1089 actual samples, native SM/transforms and independent E/B/potential visibility')
        # Four combinations of acting E and potential visibility. The field
        # reference is measured from the same sources even with force disabled.
        reference_samples=layer['measurement']['samples']
        for acting in (False,True):
            page.locator('#acting-e').set_checked(acting);idle('state.experiment.controls.electric_acting==='+str(acting).lower())
            phase=page.evaluate('state.experiment.phase');layer,render=measure()
            assert layer['measurement']['samples']==reference_samples and page.evaluate('state.experiment.phase')==phase
            for visible in (False,True):
                page.locator('#visible-potential').set_checked(visible);idle('nativeState.potential.settings.visible==='+str(visible).lower())
                assert all(v is visible for v in enabled(render).values()) and page.evaluate('state.experiment.controls.electric_acting') is acting
                acting_combinations.append({'electric_acting':acting,'potential_visible':visible,'reference_field_preserved':True})
        cases.append('all four acting E/potential visibility combinations preserve source reference and keep physical and visual controls independent')
        phase0=get()['state'];ref=phase0['editor']['reference'];history=phase0['editor']['interventions']
        page.locator('#play').click();idle('!state.paused');page.wait_for_function('state.time_s>'+str(phase0['time_s']+.01))
        page.locator('#visible-potential').set_checked(False);idle('!nativeState.potential.settings.visible&&!state.paused')
        assert get()['state']['editor']['reference']==ref and get()['state']['editor']['interventions']==history
        command('sample_potential',error=True,**guard());assert get()['native']['potential']['render']['layer_id']==render['layer_id']
        page.wait_for_function('document.getElementById("potential-state").textContent.includes("CONGELADO")')
        page.locator('#play').click();idle('state.paused');cases.append('running potential visibility keeps evolution/reference/history; frozen time retained and running sample refused')
        before=core();cfg=get()['native']['potential']['settings']
        for key,value in (('edit_token','other'),('revision',True),('frame','OTHER'),('expected_time_s',get()['state']['time_s']+1)):
            command('configure_potential',error=True,**(guard()|{key:value}),changes={'visible':True});assert core()==before and get()['native']['potential']['settings']==cfg;refusals.append(key)
        for changes in ({'visible':1},{'count_axis':65.},{'count_axis':129},{'levels_V':[1,1]},{'levels_V':[]}):
            command('configure_potential',error=True,**guard(),changes=changes);assert core()==before and get()['native']['potential']['settings']==cfg;refusals.append(str(changes))
        oldnodes=[m['node'] for m in render['meshes']];preset('coulomb');assert missing(oldnodes) and get()['native']['potential']['render'] is None
        layer,render=measure();audit_mesh(layer,render);assert render['segment_count']>100
        # Compare every valid Coulomb sample against a separate scalar sum.
        constants=json.loads((CANDIDATE/'em/constants.json').read_bytes());ke=1/(4*math.pi*constants['vacuum_electric_permittivity_F_m']['value'])
        ex=layer['source_snapshot'];xs=ex['phase']['position_m'];qs=ex['system']['charge_C'];max_sample_error=0.
        def potential(p,source=ex):return math.fsum(ke*q/math.dist(p,x) for q,x in zip(source['system']['charge_C'],source['phase']['position_m']))
        for sample in layer['measurement']['samples']:
            if sample['valid']:
                target=potential(sample['position_m']);error=abs(sample['electric_potential_V']-target)/max(abs(target),1.);max_sample_error=max(max_sample_error,error)
        assert max_sample_error<1e-10
        page.locator('#visible-e').set_checked(False);idle();page.locator('#visible-b').set_checked(False);idle()
        page.evaluate('document.querySelector("main>aside").scrollTop=0;document.querySelector("article").scrollTop=0')
        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name','cosmos2-em-potential-topic-cleanup-native.png' if args.topic_cleanup else 'cosmos2-em-potential-native.png'],check=True,capture_output=True)
        page.locator('#native-toggle').click();assert page.evaluate('!nativeMode')
        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name','cosmos2-em-potential-topic-cleanup-canvas.png' if args.topic_cleanup else 'cosmos2-em-potential-canvas.png'],check=True,capture_output=True)
        page.locator('#native-toggle').click()
        t0=layer['geometry']['metadata']['time_s'];page.locator('#play').click();idle('!state.paused');page.wait_for_function('state.time_s>'+str(t0+.1))
        page.locator('#play').click();idle('state.paused');page.locator('#probe-potential').click();idle()
        assert 'congelado' in page.locator('#reading').inner_text()
        frozen=command('probe_potential',layer_id=layer['layer_id'],position_m=[3.,2.,1.])['result'];current=command('probe',**guard(),position_m=[3.,2.,1.])['result']
        assert frozen['metadata']['time_s']==t0 and math.isclose(frozen['sample']['electric_potential_V'],potential([3,2,1]),rel_tol=1e-12)
        assert abs(current['electric_potential_V']-frozen['sample']['electric_potential_V'])>1e-9*max(1,abs(frozen['sample']['electric_potential_V']))
        page.locator('#measure').click();idle('map!==null');page.locator('#export-layers').click();idle('lastLayersExport!==null')
        exported=page.evaluate('lastLayersExport');artifact=page.evaluate('lastLayersArtifact');raw=urllib.request.urlopen('http://127.0.0.1:4700'+artifact['url']).read()
        assert hashlib.sha256(raw).hexdigest()==artifact['sha256'] and json.loads(raw)==exported and exported['schema']==2
        assert exported['layers']['electric_potential']['geometry']['metadata']['time_s']==t0 and exported['layers']['field_map']['measurement']['time_s']>t0
        cases.append('Coulomb samples vs independent SI sum; frozen-source probe differs from current model; export retains distinct source times')
        # Actual form controls, then separately sealed visual schema2 roundtrip.
        page.locator('#potential-panel details summary').click();page.locator('#potential-count').select_option('17');page.locator('#potential-auto').set_checked(False)
        page.evaluate('document.getElementById("potential-levels").focus();document.getElementById("potential-levels").value=""');page.call('Input.insertText',{'text':'-100000; 0; 100000'})
        page.locator('#potential-form button').click();idle('nativeState.potential.settings.count_axis===17');assert 'Preferências alteradas' in page.locator('#potential-state').inner_text()
        page.locator('#visible-potential').set_checked(False);idle('!nativeState.potential.settings.visible');settings=deepcopy(get()['native']['potential']['settings'])
        page.locator('#save').click();idle();checkpoint=STORAGE/'ui-phase.json';adjunct=STORAGE/'ui-phase.view.json';saved_core=core();saved_raw=adjunct.read_bytes();saved=json.loads(saved_raw)
        assert saved['payload']['view']['schema']==2 and saved['payload']['view']['potential']==settings
        command('configure_potential',**guard(),changes={'count_axis':65,'levels_V':None,'visible':True})
        page.wait_for_function('nativeState.potential.settings.count_axis===65');token=get()['state']['edit_token'];page.locator('#restore').click();idle('state.edit_token!=='+json.dumps(token))
        assert core()==saved_core and get()['native']['potential']['settings']==settings and get()['native']['potential']['render'] is None
        assert page.evaluate('potentialLayer===null') and adjunct.read_bytes()==saved_raw
        # Resealed invalid visual configuration must be refused before loading physics.
        for key,value in (('count_axis',129),('visible','yes'),('levels_V',[2.,1.])):
            bad=json.loads(saved_raw);bad['payload']['view']['potential'][key]=value;bad['sha256']=hashlib.sha256(json.dumps(bad['payload'],sort_keys=True,allow_nan=False,separators=(',',':')).encode()).hexdigest();adjunct.write_text(json.dumps(bad))
            token=get()['state']['edit_token'];command('load',error=True,**guard(),file='ui-phase');assert core()==saved_core and get()['state']['edit_token']==token;refusals.append('resealed view '+key)
        adjunct.write_bytes(saved_raw)
        base=ROOT/'output/c212-em-v04-product/c212-em-worker/product';shutil.copyfile(base/'ui-phase.json',STORAGE/'legacy-view1.json');shutil.copyfile(base/'ui-phase.view.json',STORAGE/'legacy-view1.view.json')
        legacy_bytes=(STORAGE/'legacy-view1.view.json').read_bytes();ack=command('load',**guard(),file='legacy-view1')
        assert ack['native_view_source_schema']==1 and get()['native']['potential']['settings']=={'visible':False,'count_axis':33,'levels_V':None} and (STORAGE/'legacy-view1.view.json').read_bytes()==legacy_bytes
        cases.append('visual schema2 preferences/form/save/restore exact; resealed invalid settings refused; legacy view1 explicit default settings without core migration')
        # Constant scalar potential in a magnetic model is not absence of B.
        page.wait_for_function('state.edit_token==='+json.dumps(get()['state']['edit_token']));preset('dipole');layer,render=measure()
        assert render['valid_samples']>0 and render['sample_range_V']==[0.,0.] and render['segment_count']==0 and not render['meshes']
        page.locator('#visible-potential').set_checked(False);idle();page.locator('#visible-potential').set_checked(True);idle()
        assert get()['native']['potential']['error'] is None and 'constante' in page.locator('#potential-state').inner_text()
        cases.append('constant potential in B dipole has no fabricated contours and empty-mesh visibility succeeds')
        page.locator('#native-return').click();page.wait_for_function('location.pathname==="/"&&typeof appState!=="undefined"&&appState!==null',timeout=30000)
        assert not get()['native']['active'] and get()['native']['potential']['render'] is None
        assert not errors,errors
        for name,digest in baseline['installed_app_sha256'].items():assert hashlib.sha256((ROOT/'app'/name).read_bytes()).hexdigest()==digest,name
        assert owner.read_bytes()==original
        report={'status':'candidate_electric_equipotential_native_CEF_geometry_controls_frozen_probe_export_and_visual_persistence_verified',
                'engine_sha256':runtime_receipt['engine_sha256'],
                'cases':cases,'acting_visibility_combinations':acting_combinations,'geometry':geometry_checks,'Coulomb_valid_sample_max_relative_error_vs_independent_sum':max_sample_error,
                'export_bytes':len(raw),'export_sha256':artifact['sha256'],'refused_without_physical_mutation':refusals,
                'javascript_errors':errors,'installed_product_files_preserved':82,'owner_pointer_preserved':True,
                'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (CANDIDATE/'app/em_native.py',CANDIDATE/'app/em_laboratory.py',*CANDIDATE.glob('app/em_potential*.py'),CANDIDATE/'app/em_slice.py',CANDIDATE/'app/ui/em.html',*CANDIDATE.glob('app/ui/em/*'),Path(__file__))},
                'scope':'Native/CEF potential layer in separate candidate, no installed promotion, full resource/frame profile or10k EM acceptance. Same scientific kernel0.4; visual adjunct2 is separately versioned.'}
        destination.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='source_sha256'},indent=2))
except Exception as error:
    failure={'status':'potential_native_CEF_journey_interrupted_no_acceptance','error':type(error).__name__+': '+str(error),'cases_completed':cases,'javascript_errors':errors}
    (ROOT/'evidence'/('em-potential-native-ui-failure-'+uuid.uuid4().hex+'.json')).write_text(json.dumps(failure,indent=2)+'\n');raise
finally:
    ws.close()
    if 'saved_raw' in locals() and 'adjunct' in locals():adjunct.write_bytes(saved_raw)
    try:
        with Page() as page:page.call('Page.navigate',{'url':'http://127.0.0.1:4700/'})
    finally:assert owner.read_bytes()==original
