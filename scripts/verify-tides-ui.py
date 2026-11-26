"""Native CEF material preset/form, shared maps, heat/history and exact archives."""
from pathlib import Path
import copy,hashlib,json,shutil,subprocess,time,urllib.request
from cef_page import Page
ROOT=Path(__file__).resolve().parents[1];BASE='http://127.0.0.1:4700'
pointer=ROOT/'user/sessions/latest.json';saved=pointer.read_bytes() if pointer.exists() else None
created=[];errors=[]
def get(path):return json.load(urllib.request.urlopen(BASE+'/api/'+path,timeout=35))
def post(body,path='command'):
    return json.load(urllib.request.urlopen(urllib.request.Request(BASE+'/api/'+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'}),timeout=35))
def physics():return get('state')['physics']
def guard(p):return {k:p[k] for k in ('system_id','edit_token','revision')}|{'expected_time':p['time'],'frame':p['contract']['frame']}
def phase(p):return {k:p[k] for k in ('time','revision','system_id','edit_token','conservation','gravity_effects','material_tides','instruments','instrument_history','bodies')}
def idle(page):page.wait_for_function('!pending',timeout=35000);time.sleep(.07)
def refresh(page):page.evaluate('updateState()');idle(page)
def fill(page,key,value):page.evaluate('document.getElementById('+json.dumps(key)+').value='+json.dumps(str(value)))
def archive(page,name):
    fill(page,'branch-name',name);page.locator('#branch-create').click();idle(page)
    identifier=physics()['branches']['active_id'];assert identifier;created.append(identifier);return identifier
atlas=get('atlas/state')
existing={p.name:hashlib.sha256((p/'branch.json').read_bytes()).hexdigest() for p in (ROOT/'user/sessions/branches').glob('*') if p.is_dir() and (p/'branch.json').exists()}
try:
    with Page() as page:
        page.on('pageerror',lambda error:errors.append(str(error)));page.goto(BASE+'/');page.wait_for_function('appState!==null');page.locator('#ui-scale').select_option('1')
        post({'command':'enter'});post({'command':'reset','count':32});refresh(page)
        assert physics()['scientific_generation']['model_version']=='3.10.0'
        page.evaluate('document.getElementById("tides-panel").open=true')
        page.locator('#tide-new-pair').click();idle(page)
        p=physics();assert p['material_tides'] and len(p['bodies'])==2 and p['revision']==1
        source=p['material_tides']['body'];companion=p['material_tides']['companion'];cfg=p['material_tides']['parameters']
        assert 'Calor acumulado' in page.locator('#tide-status').inner_text()
        assert 'MARÉ MATERIAL' in page.locator('#lab-model-tag').inner_text()
        assert p['conservation']['angular_momentum_error_normalized']==0.
        for i in range(2):
            p=physics();post({'command':'configure_instruments',**guard(p),'instruments_revision':p['instruments']['revision'],'operation':'create','definition':{'name':'Material '+str(i),'mode':'follow','body_id':companion,'offset_m':[i*1e5,0.,0.],'exclude_followed_source':True}})
        p=physics();post({'command':'configure_history',**guard(p),'instruments_revision':p['instruments']['revision'],'history_revision':p['instrument_history']['revision'],'recording':True,'cadence_wall_s':.25})
        post({'command':'resume'});refresh(page);page.wait_for_function('appState.physics.instrument_history.sample_count>=8')
        post({'command':'pause'});refresh(page);p=physics()
        assert p['material_tides']['dissipated_heat_J']>0 and p['energy_error']<1e-9
        assert page.evaluate('document.getElementById("apply-tide").disabled')
        cfgmap=copy.deepcopy(p['field_layers']['settings']);cfgmap.update(center_mode='follow',body_id=source,shell_radius_m=2e7,shell_count=48,cut_half_width_m=5e6,cut_offset_m=2e7,cut_orientation_deg=[0.,0.,0.],cut_resolution=17)
        post({'command':'configure_fields',**guard(p),'fields_revision':p['field_layers']['revision'],'settings':cfgmap})
        p=physics();post({'command':'sample_fields',**guard(p),'fields_revision':p['field_layers']['revision']});refresh(page)
        assert get('state')['fields_preview']['sample_count']==337
        reading=get('instruments/history');assert reading['sample_count']>=8
        frozen=phase(physics());page.locator('#save').click();idle(page)
        assert page.locator('#notice').inner_text()=='Sessão salva em user/sessions.'
        manifest=json.loads(pointer.read_text());assert manifest['material_tides'] and manifest['contract']['integrator']=='BS joint orbit/spin/heat'
        assert 'tide' in manifest['instrument_history']['samples'][0]['reading']['source_snapshot_si'][0]
        assert phase(physics())==frozen
        page.evaluate('document.getElementById("simulation-branches").open=true')
        a=archive(page,'QA material ativo')
        page.locator('#prepare-tide').click();idle(page);page.locator('#tide-active').set_checked(False)
        page.locator('#apply-tide').click();idle(page);assert physics()['material_tides'] is None
        b=archive(page,'QA material desativado')
        page.locator('#branch-first').select_option(a);page.locator('#branch-second').select_option(b)
        page.wait_for_function('!document.getElementById("branch-compare").disabled');page.locator('#branch-compare').click();idle(page)
        page.wait_for_function('branchComparison?.material_definition_changed===true')
        assert 'Modelos materiais distintos' in page.locator('#branch-comparison-status').inner_text()
        page.locator('#branch-first').select_option(a);page.locator('#branch-load').click();idle(page)
        restored=physics()
        assert restored['bodies']==frozen['bodies'] and restored['material_tides']==frozen['material_tides'] and restored['conservation']==frozen['conservation'] and restored['instrument_history']==frozen['instrument_history']
        page.locator('#load').click();idle(page);assert physics()['material_tides']==frozen['material_tides']
        # Real form activation on the opposite identity, including SI fields.
        page.locator('#prepare-tide').click();idle(page);page.locator('#tide-active').set_checked(False);page.locator('#apply-tide').click();idle(page)
        page.locator('#tide-body').select_option(companion);page.locator('#prepare-tide').click();idle(page);page.locator('#tide-active').set_checked(True)
        for key,parameter in [('tide-radius','radius_m'),('tide-love','love_k2'),('tide-lag','time_lag_s'),('tide-inertia','inertia_kg_m2'),('tide-provenance','provenance')]:fill(page,key,cfg[parameter])
        for i,v in enumerate(cfg['spin_rad_s']):fill(page,'tide-spin-'+str(i),v)
        page.locator('#apply-tide').click();idle(page);assert physics()['material_tides']['body']==companion
        page.locator('#load').click();idle(page);page.locator('#tide-body').select_option(source)
        page.locator('#prepare-tide').click();idle(page)
        page.locator('#lab-home').click();time.sleep(.4)
        page.evaluate('document.getElementById("tides-panel").scrollIntoView({block:"start"})')
        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name','cosmos2-tides-material.png'],check=True,capture_output=True)
        # A three-body Atlas copy remains monopolar until an explicitly valid
        # model is selected. Epoch/provenance remain those of the Atlas.
        post({'command':'atlas'});post({'utc':atlas['epoch']['utc']},'atlas/experiment');refresh(page)
        assert physics()['material_tides'] is None and page.evaluate('document.getElementById("prepare-tide").disabled')
        assert get('atlas/state')['epoch']==atlas['epoch']
finally:
    try:post({'command':'atlas'})
    finally:
        if saved is None:pointer.unlink(missing_ok=True)
        else:pointer.write_bytes(saved)
        target=ROOT/'output/c211-tides-native-fixtures';target.mkdir(exist_ok=True)
        for identifier in created:
            folder=ROOT/'user/sessions/branches'/identifier.split(':')[1]
            if folder.exists():shutil.move(str(folder),str(target/folder.name))
assert not errors,errors
assert (pointer.read_bytes() if pointer.exists() else None)==saved
assert all(hashlib.sha256((ROOT/'user/sessions/branches'/name/'branch.json').read_bytes()).hexdigest()==sha for name,sha in existing.items())
report={'status':'installed3_10_native_material_verified','synthetic_preset_and_opposite_source_SI_form':True,'native_map_samples':337,'history_samples':reading['sample_count'],'save_load_and_branch_phase_spin_heat_reference_exact':True,'material_vs_point_branch_hypotheses_labeled':True,'stale_form_blocked':True,'three_body_Atlas_material_disabled':True,'owner_pointer_and_branch_files_preserved':True,'atlas_epoch_preserved':True,'page_errors':errors,'catalog_refresh_required':True,'scope':'Bounded two-body equilibrium tide; no surface displacement/thermal radius/J2 coupling/full C2-11 acceptance'}
(ROOT/'evidence/tides-ui-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
