"""Real CEF journey through G particle editing, SI reading and panel access."""
from pathlib import Path
from copy import deepcopy
import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
import urllib.error
import urllib.request
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1];G=ROOT/'output/c212-em-integration-product'
sys.path.insert(0,str(G/'em'))
from em_experiment import Experiment
parser=argparse.ArgumentParser();parser.add_argument('--label',default='initial');args=parser.parse_args()
assert args.label.isalnum() and len(args.label)<=16
destination=ROOT/f'evidence/em-integration-native-ui-{args.label}-check.json';assert not destination.exists()
session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'))
assert session.get('emIntegrationCandidate') and Path(session['serverScript']).resolve()==(G/'app/server.py').resolve()
owner=(ROOT/'user/sessions/latest.json').read_bytes()
report={'completed':False,'checks':[],'JS_errors':[],'source_sha256':{}}
def current():return json.load(urllib.request.urlopen('http://127.0.0.1:4700/api/em/state',timeout=10))['state']
def idle(page):page.wait_for_function('state&&state.paused&&!pending&&nativeState?.confirmation?.state==="accepted"&&!nativeState.error&&nativeState.confirmation.metadata.time_s===state.time_s',timeout=30000)
def snap(page):return page.evaluate('JSON.parse(JSON.stringify(state))')
def panel(page,name):
    if page.evaluate('workspacePanel')!=name:
        page.locator('[data-panel="'+name+'"]').click()
        page.wait_for_function('workspacePanel==='+json.dumps(name))
def click(page,name):
    parent=page.evaluate('document.getElementById('+json.dumps(name)+')?.closest("[data-workspace-panel]")?.dataset.workspacePanel||null')
    if parent:panel(page,parent)
    page.locator('#'+name).click();idle(page)
def fill(page,values):
    page.evaluate('Object.entries('+json.dumps(values)+').forEach(([key,value])=>document.getElementById(key).value=String(value))')
def load(page,name):
    panel(page,'experience');page.locator('#preset').select_option(name);click(page,'load-preset')
def measure(page):
    click(page,'measure-particle');return page.evaluate('JSON.parse(JSON.stringify(particleMeasurement))')
def equal_force(s,reading):
    p=s['experiment'];r=reading['particle'];x=r['position_m'];v=r['velocity_m_s'];q=r['charge_C']
    if p['mode']=='test_particle':
        e=list(p['model']['uniform_E_V_m']);b=list(p['model']['uniform_B_T']);sources=p['model']['sources'];acting=p['controls']
    else:
        ids=p['system']['ids'];e=[0.,0.,0.];b=[0.,0.,0.];sources=[{'id':sid,'position_m':pos,'charge_C':charge,'magnetic_moment_A_m2':[0,0,0]} for sid,pos,charge in zip(ids,p['phase']['position_m'],p['system']['charge_C']) if sid!=r['id']];acting={'electric_acting':p['controls']['acting'],'magnetic_acting':False}
    constants=json.loads((G/'em/constants.json').read_bytes());ke=1/(4*math.pi*constants['vacuum_electric_permittivity_F_m']['value']);mu=constants['vacuum_magnetic_permeability_N_A2']['value']/(4*math.pi)
    for source in sources:
        d=[a-c for a,c in zip(x,source['position_m'])];radius=math.hypot(*d);moment=source['magnetic_moment_A_m2'];along=math.fsum(a*c for a,c in zip(d,moment))
        for k in range(3):e[k]+=ke*source['charge_C']*d[k]/radius**3;b[k]+=mu*(3*d[k]*along/radius**5-moment[k]/radius**3)
    cross=[v[(k+1)%3]*b[(k+2)%3]-v[(k+2)%3]*b[(k+1)%3] for k in range(3)]
    fe=[q*c*acting['electric_acting'] for c in e];fb=[q*c*acting['magnetic_acting'] for c in cross]
    scale=max(math.hypot(*fe)+math.hypot(*fb),1e-100)
    for key,expected in (('electric_force_N',fe),('magnetic_force_N',fb),('force_N',[a+c for a,c in zip(fe,fb)])):
        assert math.dist(reading['force'][key],expected)<=3e-12*scale,(key,reading['force'][key],expected)
    assert reading['time_s']==s['time_s'] and reading['source_snapshot']==p

try:
    with Page() as page:
        page.on('pageerror',lambda error:report['JS_errors'].append(error))
        page.goto('http://127.0.0.1:4700/');page.wait_for_function('typeof appState!=="undefined"&&appState')
        page.locator('#em-lab').click();idle(page)
        page.wait_for_function('typeof speciesReference!=="undefined"&&speciesReference')
        page.locator('#interface-scale').select_option('1')
        load(page,'helix');before=snap(page);panel(page,'editor')
        fill(page,{'particle-charge':-2,'particle-mass':3,'particle-x':.2,'particle-y':.3,'particle-z':-.1,
                   'particle-vx':1.5,'particle-vy':-.3,'particle-vz':.4})
        page.wait_for_function('document.getElementById("particle-mass").value==="3"')
        time.sleep(.35);assert page.evaluate('document.getElementById("particle-mass").value')=='3'
        assert snap(page)['experiment']==before['experiment']
        click(page,'apply-particle');edited=snap(page)
        assert edited['experiment']['particle']=={'charge_C':-2.,'mass_kg':3.}
        assert edited['experiment']['phase']=={'position_m':[.2,.3,-.1],'velocity_m_s':[1.5,-.3,.4],'time_s':0.}
        assert edited['revision']==before['revision']+1 and edited['editor']['particle_origin']=='user_model'
        delta=edited['editor']['interventions'][-1]['delta']
        assert math.isclose(delta['mechanical_energy_J'],3.75-.545,abs_tol=1e-14) and delta['total_charge_C']==-3
        expected=Experiment.from_payload(edited['experiment']);expected.advance()
        click(page,'one-step');assert snap(page)['experiment']==json.loads(json.dumps(expected.payload()))
        reading=measure(page);equal_force(snap(page),reading)
        click(page,'one-step');assert 'CONGELADA' in page.locator('#particle-measurement').inner_text()
        click(page,'export-particle')
        artifact=page.evaluate('particleMeasurementArtifact');raw=urllib.request.urlopen('http://127.0.0.1:4700'+artifact['url'],timeout=5).read()
        assert hashlib.sha256(raw).hexdigest()==artifact['sha256'] and json.loads(raw)==page.evaluate('particleMeasurement')
        report['checks'].append('User particle form keeps draft, commits one physical intervention, matches one core step and exports independently verified SI force.')

        for species,mass,charge,field in [('electron',9.1093837139e-31,-1.602176634e-19,1e-11),('proton',1.67262192595e-27,1.602176634e-19,1e-8)]:
            load(page,'helix');panel(page,'editor');page.evaluate('document.getElementById("background-editor").open=true')
            fill(page,{'background-bz':field});click(page,'apply-background')
            before=snap(page);page.locator('#particle-species').select_option(species)
            assert snap(page)['experiment']==before['experiment']
            click(page,'apply-particle');s=snap(page)
            assert s['experiment']['particle']=={'charge_C':charge,'mass_kg':mass}
            click(page,'one-step');equal_force(snap(page),measure(page))
            report['checks'].append(species+' reference fills form without mutation; explicit apply/step/read uses adopted CODATA SI values.')

        for name in ('electric','helix','crossed','dipole','coulomb'):
            load(page,name);click(page,'one-step');reading=measure(page);equal_force(snap(page),reading)
            assert page.evaluate('document.getElementById("test-particle-editor").hidden')==(name=='coulomb')
            report['checks'].append(name+' preset has measured electrical/magnetic force, energy and declared work reference.')
        load(page,'crossed');click(page,'measure')
        for term,control,visible in [('electric','acting-e','visible-e'),('magnetic','acting-b','visible-b')]:
            for acting in (False,True):
                panel(page,'experience');page.locator('#'+control).set_checked(acting);idle(page)
                for shown in (False,True):
                    before=snap(page);panel(page,'layers');page.locator('#'+visible).set_checked(shown);idle(page);after=snap(page)
                    assert after['experiment']==before['experiment'] and after['editor']['reference']==before['editor']['reference']
                    assert after['editor']['visual'][term+'_visible']==shown
                    reading=measure(page);equal_force(snap(page),reading)
                    report['checks'].append({'term':term,'acting':acting,'visible':shown,'visibility_preserves_physics':True})
        click(page,'save');saved=snap(page)
        click(page,'one-step');click(page,'restore');restored=snap(page)
        for key in ('experiment','editor','time_preferences'):assert restored[key]==saved[key]
        storage=G/'c212-em-worker/product'
        expected={'experiment':saved['experiment'],'editor':saved['editor'],'time_preferences':saved['time_preferences'],
                  'scientific_generation':saved['scientific_generation'],'execution_generation':saved['execution_generation'],
                  'files_sha256':{ending:hashlib.sha256((storage/('ui-phase'+ending)).read_bytes()).hexdigest() for ending in ('.json','.view.json','.timing.json')}}
        (ROOT/'output/em-integration-restart-expected.json').write_text(json.dumps(expected,indent=2)+'\n')
        report['checks'].append('Save, advance and restore preserve scientific phase, editor and numeric timing preferences; restart oracle saved.')

        layouts=[]
        for zoom in (1,1.5):
            page.locator('#interface-scale').select_option(str(zoom))
            for name in ('experience','editor','layers','readings'):
                panel(page,name)
                # CEF returns unzoomed element coordinates. Convert to the
                # physical viewport, as Page's mouse locator already does.
                value=page.evaluate('(() => {const p=document.querySelector("[data-workspace-panel]:not([hidden])"),a=document.querySelector("article").getBoundingClientRect(),t=document.getElementById("play").getBoundingClientRect(),z=Number(getComputedStyle(document.body).zoom)||1;return {panel:p.dataset.workspacePanel,panels:document.querySelectorAll("[data-workspace-panel]:not([hidden])").length,scene_fraction:a.width*z/innerWidth,element_coordinate_scale:z,overflow:document.documentElement.scrollWidth>innerWidth+1,pause_on_screen:t.top*z>=0&&t.bottom*z<=innerHeight,panel_scrollable:p.scrollHeight>p.clientHeight};})()')
                assert value['panels']==1 and value['scene_fraction']>=.65 and not value['overflow'] and value['pause_on_screen'],(zoom,value)
                layouts.append({'zoom':zoom,**value})
            page.evaluate('document.querySelectorAll("aside").forEach(p=>p.scrollTop=0)')
            subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name',f'cosmos2-em-integration-{args.label}-zoom{int(zoom*100)}.png'],check=True,capture_output=True)
        page.locator('#interface-scale').select_option('1')
        report['layouts']=layouts
        assert not report['JS_errors'],report['JS_errors']
        page.locator('#native-return').click();page.wait_for_function('location.pathname==="/"')
        assert (ROOT/'user/sessions/latest.json').read_bytes()==owner
        report.update(completed=True,owner_pointer_preserved=True,
            scope='G real CEF particle editor, five experiments, SI readings, acting/layers, same-process save and 100/150% layout. Zoom screenshots still require visual review. No fresh restart or formal G performance acceptance.')
finally:
    report['source_sha256']={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),*sorted((G/'app').rglob('*'))] if p.is_file() and '__pycache__' not in p.parts}
    destination.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'completed':report['completed'],'checks':len(report['checks']),'JS_errors':report['JS_errors']}),flush=True)
