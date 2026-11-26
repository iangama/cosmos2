"""Native CEF orbital presets/forms, capture, original points and archive curves."""
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
def guard(p):return {k:p[k] for k in ('system_id','edit_token','revision')}|{'expected_time':p['time'],'frame':p['contract']['frame'],'orbital_revision':p['orbital_instruments']['revision']}
def physical(p):return {k:copy.deepcopy(p[k]) for k in ('time','revision','system_id','edit_token','conservation','bodies')}
def idle(page):page.wait_for_function('!pending',timeout=35000);time.sleep(.07)
def refresh(page):page.evaluate('updateState()');idle(page)
def archive(page,name):
    page.evaluate('document.getElementById("branch-name").value='+json.dumps(name));page.locator('#branch-create').click();idle(page)
    identifier=physics()['branches']['active_id'];assert identifier;created.append(identifier);return identifier
def capture(name):subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name',name],check=True,capture_output=True)
atlas=get('atlas/state')
existing={p.name:hashlib.sha256((p/'branch.json').read_bytes()).hexdigest() for p in (ROOT/'user/sessions/branches').glob('*') if p.is_dir() and (p/'branch.json').exists()}
try:
    with Page() as page:
        page.on('pageerror',lambda error:errors.append(str(error)));page.goto(BASE+'/');page.wait_for_function('appState!==null');page.locator('#ui-scale').select_option('1')
        post({'command':'enter'});post({'command':'reset','count':32});refresh(page)
        assert physics()['scientific_generation']['model_version']=='3.11.0'
        page.evaluate('document.getElementById("orbital-panel").open=true')
        page.locator('#orbital-new-resonant').click();idle(page)
        page.wait_for_function('appState.physics.orbital_instruments.definition!==null&&appState.physics.bodies.length===3')
        p=physics();assert p['revision']==0 and not p['interventions'] and p['origin_kind']=='user_system' and len(p['bodies'])==3
        original=physical(p);definition=copy.deepcopy(p['orbital_instruments']['definition'])
        page.locator('#orbital-sample').click();idle(page)
        assert 'Período externo / interno: 2.000000000' in page.locator('#orbital-reading').inner_text()
        assert physical(physics())==original
        page.locator('#orbital-cadence').select_option('0.25');idle(page)
        page.locator('#orbital-toggle').click();idle(page)
        assert physics()['orbital_instruments']['recording'] and not physics()['instruments']['probes']
        post({'command':'rate','value':10});post({'command':'resume'});refresh(page)
        page.wait_for_function('appState.physics.orbital_instruments.sample_count>=10')
        post({'command':'pause'});refresh(page)
        page.wait_for_function('orbitalData?.samples.length>=6&&orbitalPoints.length>=6')
        assert page.evaluate('document.getElementById("orbital-apply").disabled')
        frozen=physical(physics());page.locator('#orbital-chart').click();idle(page)
        # Select an actual rendered sample using the same canvas coordinates.
        chosen=page.evaluate('(() => {const c=document.getElementById("orbital-chart");c.scrollIntoView({block:"center"});const r=c.getBoundingClientRect(),p=orbitalPoints[Math.floor(orbitalPoints.length/2)],z=Number(getComputedStyle(document.body).zoom)||1;return {x:(r.left+p.x*r.width/c.width)*z,y:(r.top+p.y*r.height/c.height)*z,sequence:p.sequence};})()')
        for kind in ('mousePressed','mouseReleased'):page.call('Input.dispatchMouseEvent',{'type':kind,'x':chosen['x'],'y':chosen['y'],'button':'left','clickCount':1})
        idle(page);assert 'Amostra #'+str(chosen['sequence']) in page.locator('#orbital-point-reading').inner_text()
        assert physical(physics())==frozen
        page.locator('#orbital-export').click();idle(page)
        exported=page.locator('#notice').inner_text();assert exported.startswith('Exportado: ')
        exported_data=json.loads(Path(exported.removeprefix('Exportado: ')).read_text())
        assert exported_data['orbital_instruments']['samples'][0]['reading']['selected_phase_si']
        page.locator('#save').click();idle(page);assert physical(physics())==frozen
        manifest=json.loads(pointer.read_text());assert manifest['orbital_instruments']['samples']
        saved_orbital=copy.deepcopy(physics()['orbital_instruments'])
        page.evaluate('document.getElementById("simulation-branches").open=true')
        first=archive(page,'QA orbital 2:1')
        page.evaluate('document.getElementById("orbital-definition").open=true')
        page.locator('#orbital-prepare').click();idle(page);page.locator('#orbital-j').select_option('3')
        before=physical(physics());page.locator('#orbital-apply').click();idle(page)
        assert physical(physics())==before and physics()['orbital_instruments']['definition']['j']==3
        post({'command':'resume'});time.sleep(.7);post({'command':'pause'});refresh(page)
        second=archive(page,'QA orbital definição 3:2')
        page.locator('#branch-first').select_option(first);page.locator('#branch-second').select_option(second)
        page.locator('#branch-compare').click();idle(page)
        page.wait_for_function('branchComparison?.orbital_definition_changed===true')
        assert not page.evaluate('branchComparison.same_physical_instant')
        page.locator('#branch-quantity').select_option('orbital_theta_inner')
        assert 'Definições orbitais distintas' in page.locator('#branch-comparison-status').inner_text()
        assert 'θ interno' in page.locator('#branch-chart-legend').inner_text()
        page.evaluate('document.getElementById("branch-chart").scrollIntoView({block:"center"})');capture('cosmos2-resonance-branches.png')
        page.locator('#branch-first').select_option(first);page.locator('#branch-load').click();idle(page)
        p=physics();assert p['time']==frozen['time'] and p['bodies']==frozen['bodies'] and p['conservation']==frozen['conservation'] and p['orbital_instruments']==saved_orbital
        page.locator('#load').click();idle(page)
        p=physics();assert p['bodies']==frozen['bodies'] and p['orbital_instruments']==saved_orbital
        page.locator('#lab-home').click();time.sleep(.25)
        page.evaluate('document.getElementById("orbital-definition").open=false;document.getElementById("orbital-chart").scrollIntoView({block:"center"})')
        capture('cosmos2-resonance-angles.png')
        # Control preset and rejected duplicate-source form, with no phase edit.
        page.locator('#orbital-new-control').click();idle(page);page.locator('#orbital-sample').click();idle(page)
        assert 'Período externo / interno: 1.800000000' in page.locator('#orbital-reading').inner_text()
        p=physics();control=physical(p);d=p['orbital_instruments']['definition']
        page.evaluate('document.getElementById("orbital-definition").open=true')
        page.locator('#orbital-prepare').click();idle(page);page.locator('#orbital-inner').select_option(d['outer_id']);page.locator('#orbital-apply').click();idle(page)
        assert 'três identidades' in page.locator('#notice').inner_text() and physical(physics())==control
        page.locator('#orbital-inner').select_option(d['inner_id'])
        page.evaluate('document.getElementById("orbital-normal-2").value="-1"');page.locator('#orbital-apply').click();idle(page)
        page.locator('#orbital-sample').click();idle(page)
        assert 'Fora do domínio orbital' in page.locator('#orbital-reading').inner_text() and physical(physics())==control
finally:
    try:post({'command':'atlas'})
    finally:
        if saved is None:pointer.unlink(missing_ok=True)
        else:pointer.write_bytes(saved)
        target=ROOT/'output/c211-resonance-native-fixtures';target.mkdir(exist_ok=True)
        for identifier in created:
            folder=ROOT/'user/sessions/branches'/identifier.split(':')[1]
            if folder.exists():shutil.move(str(folder),str(target/folder.name))
assert not errors,errors
assert (pointer.read_bytes() if pointer.exists() else None)==saved
assert get('atlas/state')['epoch']==atlas['epoch']
assert all(hashlib.sha256((ROOT/'user/sessions/branches'/name/'branch.json').read_bytes()).hexdigest()==sha for name,sha in existing.items())
report={'status':'installed3_11_native_orbital_instruments_verified','synthetic_2to1_and_1p8_controls':True,'capture_without_gravity_probes':True,'original_rendered_sample_query_and_SI_export':True,'configuration_and_queries_preserve_phase_and_reference':True,'save_load_branch_phase_history_exact':True,'orbital_branch_graph_preserves_different_times_and_definitions':True,'stale_duplicate_and_invalid_plane_forms_safe':True,'owner_pointer_branch_files_and_atlas_epoch_preserved':True,'page_errors':errors,'catalog_refresh_required':True,'scope':'Finite osculating-angle instruments; no added force/automatic resonance classifier/permanent capture claim; performance separate'}
(ROOT/'evidence/resonance-ui-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
