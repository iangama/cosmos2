"""Sequential four-force journeys share one frozen four-body source phase."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
import argparse
import copy
import hashlib
import json
import subprocess
import sys
import time
import traceback
import zipfile
from PIL import Image
from cef_page import Page

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is6-spatial-product0.18.3/app'
sys.path.insert(0,str(APP))
from is6_product_scene import artifact
h=SourceFileLoader('is6_joint_helpers',str(ROOT/'scripts/verify-native-solar-integration.py')).load_module()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    folder=ROOT/('output/is6-integrated-journey-'+args.label);receipt=ROOT/('evidence/is6-integrated-journey-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve journey')
    anchors=[ROOT/'evidence/is6-spatial-profile-audit-20261102c.json',ROOT/'evidence/is6-product-native-20261102f.json',ROOT/'evidence/is6-persistence-native-20261102b.json',ROOT/'evidence/is6-active-shutdown-20261102b.json',ROOT/'evidence/is6-product-service-20261102e.json']
    for p in anchors:assert json.loads(p.read_text())['accepted'],p
    manifest=json.loads((APP.parent/'build-manifest.json').read_text());hashes=dict(manifest['source_sha256'])
    hashes.update({(APP/n).relative_to(ROOT).as_posix():v for n,v in manifest['files_sha256'].items()})
    for p in [Path(__file__),APP.parent/'build-manifest.json',ROOT/'IS-6-PERCURSO-INTEGRADO-CONTRATO-PREVIO.md',ROOT/'scripts/cef_page.py',ROOT/'scripts/capture-window.ps1',ROOT/'scripts/verify-native-solar-integration.py',ROOT/'scripts/engine-command.py',*anchors]:hashes[p.relative_to(ROOT).as_posix()]=sha(p)
    assert all(sha(ROOT/n)==v for n,v in hashes.items());folder.mkdir()
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
    r=dict(accepted=False,completed=False,source_sha256=hashes,owner_sha256=sha(ROOT/'user/sessions/latest.json'),groups=[],captures=[],page_errors=[],refusals=[],exports=[],
           recipe_before_execution=dict(body_cases=[['399','proton'],['599','electron']],body_representation='vector',jovian_degree=13,particle_steps=4,particle_speeds_m_s=dict(proton=100000,electron=1000000),solar_knots=[120,121],solar_default='0.17.2 accepted prescribed-density N14 configuration',native_wait_s=30,solar_wait_s=750),
           scope='Sequential existing instruments on one paused source only; no simultaneous layers, composite checkpoint/migration, new physics, performance or promotion acceptance. Captures require visual review.')
    r['recipe_before_execution']['magnetic_points']={'399':dict(latitude=-23.55,longitude=-46.63,altitude=1.),'599':dict(radius=1.5*71492000.,latitude=0.,longitude=0.)}
    r['recipe_before_execution']['solar_configuration']=dict(parameters=dict(temperature_K=15e6,density_kg_m3=150000.,hydrogen_fraction=.34,catalyst_fraction=.01,catalyst_seed='n14',duration_s=31557600000.,volume_m3=1.),
        acting=dict(strong=True,weak=True,electromagnetic=True),channel_switches={k:True for k in ['pp','dp','he3he3','c12pg','n13beta','c13pg','n14pg','o15beta','n15pa','he3alpha','be7ec','li7pa','be7p','b8beta2a','n15pg','o16pg','f17beta','o17pa']},
        mode='prescribed_density',density_history=dict(kind='exponential',ratio=1.05),include_coulomb=True,include_screening=True)
    def persist():receipt.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def passed(name):r['groups'].append(name);persist();print(name,flush=True)
    def state(module):return h.get('/api/'+module+'/state')
    def same_phase():assert h.phase(h.get('/api/state')['physics'])==held
    def click(page,selector,timeout=30000):
        page.evaluate('(()=>{const e=document.querySelector('+json.dumps(selector)+');for(let p=e?.parentElement;p;p=p.parentElement)if(p.tagName==="DETAILS")p.open=true;})()')
        page.wait_for_function('document.querySelector('+json.dumps(selector)+')&&!document.querySelector('+json.dumps(selector)+').disabled',timeout=timeout)
        page.locator(selector).click()
        page.wait_for_function('!pending&&!spatialInstrument.pending&&!particlePending&&!solarZonePending',timeout=timeout)
    def spatial_ready(page):page.wait_for_function('!spatialInstrument.pending&&!spatialInstrument.snapshot.busy',timeout=30000)
    def particle_ready(page):
        page.wait_for_function('!particlePending&&particleState.active&&particleState.worker.paused&&!particleState.view.pending_sequence&&particleState.view.confirmed_phase.time_s===particleState.worker.experiment.phase.time_s',timeout=30000)
        s=state('particles');assert not s['error'],s['error'];return s
    def solar_ready(page):
        page.wait_for_function('solarZoneState.active&&!solarZonePending&&!solarZoneState.busy&&!solarZoneCurvePending&&solarZoneCurveId===solarZoneState.worker.artifact_id',timeout=750000)
        s=state('solar-zone');assert not s['error'],s['error'];return s
    def capture(page,name,scale='1',panel=None):
        page.locator('#ui-scale').select_option(scale)
        if panel:page.evaluate('(()=>{const e=document.getElementById('+json.dumps(panel)+');for(let p=e.parentElement;p;p=p.parentElement)if(p.tagName==="DETAILS")p.open=true;e.scrollIntoView({block:"start"});})()')
        time.sleep(.25);path=ROOT/('evidence/cosmos2-is6-journey-'+args.label+'-'+name+'.png')
        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name',path.name],check=True,capture_output=True)
        im=Image.open(path);assert im.size==(1920,1080);rgb=folder/path.name;im.convert('RGB').save(rgb)
        r['captures'].append(dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),RGB=rgb.relative_to(ROOT).as_posix(),RGB_sha256=sha(rgb)));persist()
    persist()
    try:
        with Page() as page:
            page.on('pageerror',lambda error:r['page_errors'].append(error));page.goto(h.BASE+'/')
            page.wait_for_function('appState&&atlasState&&spatialInstrument.snapshot&&particleState&&solarZoneState&&!pending')
            assert not any(state(name)['active'] for name in ['spatial','particles','solar-zone'])
            if h.get('/api/state')['mode']=='experiment':h.post('/api/command',dict(command='atlas'))
            page.wait_for_function('appState.mode==="atlas"&&!pending');page.locator('#ui-scale').select_option('1');click(page,'#copy-solar')
            page.wait_for_function('appState.physics?.bodies.length===4&&appState.physics.paused&&!pending',timeout=70000)
            phase=h.get('/api/state')['physics'];held=h.phase(copy.deepcopy(phase));r['common_source_phase']=phase;persist()
            for target,species in r['recipe_before_execution']['body_cases']:
                body=next(b for b in phase['bodies'] if b['reference_id']=='sol:naif:'+target)
                click(page,'#open-spatial');page.locator('#spatial-body').select_option(body['id']);click(page,'#spatial-create');spatial_ready(page)
                spatial=state('spatial');assert spatial['artifact']['source']['body_id']==body['id'];same_phase()
                refusal=h.post('/api/spatial/command',dict(command='_close'),400)
                assert 'interno' in refusal['error'] and state('spatial')['artifact']==spatial['artifact']
                r['refusals'].append('Public_internal_close_'+target)
                refusal=h.post('/api/solar-zone/command',dict(command='create',source_guard=artifact.body.guard(phase),configuration=r['recipe_before_execution']['solar_configuration']),400)
                assert 'malha' in refusal['error'] and state('spatial')['artifact']==spatial['artifact'] and not state('solar-zone')['active']
                r['refusals'].append('Solar_zone_while_spatial_'+target)
                for scale in ['1','1.5']:capture(page,'mesh-'+target+'-'+str(int(float(scale)*100)),scale,'spatial-title')
                click(page,'#spatial-leave');spatial_ready(page);click(page,'#spatial-panel-close');page.locator('#ui-scale').select_option('1')
                page.locator('#solar-body').select_option(body['id']);page.locator('#body-field-representation').select_option('vector')
                prefix='earth-field-' if target=='399' else 'jupiter-field-'
                for key,value in r['recipe_before_execution']['magnetic_points'][target].items():page.evaluate('document.getElementById('+json.dumps(prefix+key)+').value='+json.dumps(str(value)))
                if target=='599':page.locator('#jupiter-field-degree').select_option('13')
                click(page,'#body-field-show');page.wait_for_function('appState.body_field_preview?.reading.body_id==='+json.dumps(body['id']),timeout=30000)
                field=h.get('/api/state')['body_field_preview'];model=field['reading']['provenance']['model']
                assert model==('IGRF14' if target=='399' else 'JRM33 internal');same_phase()
                page.locator('#particle-species').select_option(species);page.evaluate('document.getElementById("particle-speed").value='+json.dumps(str(r['recipe_before_execution']['particle_speeds_m_s'][species])))
                click(page,'#particle-create');particle=particle_ready(page)
                refusal=h.post('/api/spatial/command',dict(command='create',guard=state('spatial')['guard'],source_guard=artifact.body.guard(phase),body_id=body['id'],configuration=artifact.DEFAULT_CONFIGURATION),400)
                assert 'partícula' in refusal['error'] and not state('spatial')['active']
                r['refusals'].append('Spatial_while_particle_'+target)
                for _ in range(4):click(page,'#particle-step');particle=particle_ready(page)
                checkpoint=copy.deepcopy(particle['worker']['experiment']['phase']);click(page,'#particle-save');click(page,'#particle-step');particle_ready(page);click(page,'#particle-load')
                assert particle_ready(page)['worker']['experiment']['phase']==checkpoint
                for scale in ['1','1.5']:capture(page,'particle-'+target+'-'+str(int(float(scale)*100)),scale,'particle-title')
                page.locator('#ui-scale').select_option('1');click(page,'#particle-leave');page.wait_for_function('!particleState.active');same_phase()
                click(page,'#body-field-clear');page.wait_for_function('!appState.body_field_preview&&!pending');same_phase()
                passed('Same_phase_spatial_'+target+'_magnetic_'+model+'_particle_save_load_and_close')
            assert page.evaluate('zoneConfiguration()')==r['recipe_before_execution']['solar_configuration']
            click(page,'#zone-create',750000);solar=solar_ready(page)
            assert solar['worker']['configuration']['acting']==dict(strong=True,weak=True,electromagnetic=True)
            refusal=h.post('/api/spatial/command',dict(command='create',guard=state('spatial')['guard'],source_guard=artifact.body.guard(phase),body_id=phase['bodies'][0]['id'],configuration=artifact.DEFAULT_CONFIGURATION),400)
            assert 'zona solar' in refusal['error'] and not state('spatial')['active']
            r['refusals'].append('Spatial_while_solar_zone')
            assert len(page.evaluate('zoneChannels'))==18;same_phase()
            page.evaluate('document.getElementById("zone-index").value="120";document.getElementById("zone-index").dispatchEvent(new Event("change",{bubbles:true}))');solar=solar_ready(page)
            page.wait_for_function('solarZoneState.worker.view.selected_index===120',timeout=30000);solar=state('solar-zone');saved_id=solar['worker']['artifact_id'];saved_sample=copy.deepcopy(solar['worker']['sample'])
            click(page,'#zone-save',750000);click(page,'#zone-step');solar_ready(page);click(page,'#zone-load',750000);solar=solar_ready(page)
            assert solar['worker']['artifact_id']==saved_id and solar['worker']['sample']==saved_sample
            page.evaluate('document.getElementById("zone-branch-name").value='+json.dumps('Jornada quatro forças · '+args.label));click(page,'#zone-branch-create');solar=solar_ready(page)
            click(page,'#zone-export');message=page.locator('#zone-file').inner_text();path=Path(message.removeprefix('Exportado: '));export=json.loads(path.read_text());assert export['run']['id']==saved_id and export['sample']==saved_sample
            r['exports'].append(dict(path=str(path),sha256=sha(path)))
            for scale in ['1','1.5']:capture(page,'nuclear-'+str(int(float(scale)*100)),scale,'zone-probe')
            page.locator('#ui-scale').select_option('1');before=solar['worker']['artifact_sha256'];page.locator('#zone-show-neutrinos').set_checked(False);solar=solar_ready(page)
            assert solar['worker']['artifact_sha256']==before and not solar['worker']['view']['visible']['neutrinos']
            page.evaluate('document.getElementById("zone-config-holder").open=true');page.locator('#zone-weak').set_checked(False);click(page,'#zone-recompute',750000);off=solar_ready(page)
            assert not off['worker']['configuration']['acting']['weak'] and off['worker']['artifact_id']!=saved_id;same_phase()
            click(page,'#zone-load',750000);solar=solar_ready(page);assert solar['worker']['configuration']['acting']['weak'] and solar['worker']['sample']==saved_sample
            click(page,'#zone-leave');page.wait_for_function('!solarZoneState.active');same_phase()
            passed('Same_phase_strong_weak_EM_zone_exact_checkpoint_export_independent_visual_control_and_weak_recompute_restore')
            assert not r['page_errors'] and sha(ROOT/'user/sessions/latest.json')==r['owner_sha256'] and all(sha(ROOT/n)==v for n,v in hashes.items())
            r.update(accepted=True,completed=True)
    except Exception:r['failure']=traceback.format_exc()
    finally:
        try:
            if state('solar-zone')['active']:
                s=state('solar-zone')['worker'];h.post('/api/solar-zone/command',dict(command='leave',guard={k:s[k] for k in ['worker_id','artifact_id','edit_token','revision']}))
            if state('particles')['active']:h.post('/api/particles/command',dict(command='leave'))
            s=state('spatial')
            if s['active']:h.post('/api/spatial/command',dict(command='leave',guard=s['guard']))
            if h.get('/api/state')['mode']=='experiment':h.post('/api/command',dict(command='atlas'))
            h.native('openspace.toggleShutdown();return {closing=true}')
        except Exception:r['cleanup_failure']=traceback.format_exc();r['accepted']=False
        persist()
    print(json.dumps(dict(accepted=r['accepted'],groups=r['groups'],captures=len(r['captures']),failure=None if not r.get('failure') else r['failure'].splitlines()[-1]),ensure_ascii=False),flush=True)
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
