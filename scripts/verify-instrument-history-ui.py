"""Installed native CEF journey: compare, record, select, export and restore."""
from pathlib import Path
import copy
import hashlib
import json
import subprocess
import time
import urllib.error
import urllib.request

import numpy as np
from cef_page import Page
from websockets.sync.client import connect

ROOT=Path(__file__).resolve().parents[1]
BASE='http://127.0.0.1:4700'
latest=ROOT/'user/sessions/latest.json'
saved=latest.read_bytes() if latest.exists() else None
errors,cases=[],[]

def get(path):
    return json.load(urllib.request.urlopen(BASE+'/api/'+path,timeout=20))

def post(body,path='command'):
    req=urllib.request.Request(BASE+'/api/'+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    return json.load(urllib.request.urlopen(req,timeout=25))

def physical(p):
    return {k:copy.deepcopy(p[k]) for k in ('bodies','time','revision','conservation','system_id','edit_token','scientific_generation','numerical_policy')}

def idle(page,condition='true'):
    page.wait_for_function('!pending&&('+condition+')');time.sleep(.06)

def fill(page,key,value):
    page.evaluate('document.getElementById('+json.dumps(key)+').value='+json.dumps(str(value)))

socket=connect('ws://127.0.0.1:4682',open_timeout=5,close_timeout=.2,ping_interval=None)
socket.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
serial=0
def lua(code):
    global serial
    serial+=1
    socket.send(json.dumps({'topic':serial,'type':'luascript','payload':{'script':code,'return':True}}))
    result=json.loads(socket.recv(timeout=15))
    assert result.get('topic')==serial and '1' in result.get('payload',{}),result
    return result['payload']['1']

def rejected(body):
    try:post(body)
    except urllib.error.HTTPError as error:
        assert error.code==400
        return json.load(error)['error']
    raise AssertionError('Old history request accepted')

atlas=get('atlas/state')
try:
    with Page() as page:
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(BASE+'/');page.wait_for_function('appState!==null')
        page.locator('#ui-scale').select_option('1')
        for kind in ('fixture','atlas'):
            post({'command':'atlas'})
            if kind=='atlas':post({'utc':atlas['epoch']['utc']},'atlas/experiment')
            else:post({'command':'enter'});post({'command':'reset','count':32})
            post({'command':'rate','value':1})
            page.evaluate('updateState()');idle(page,'appState.physics?.instrument_history!==undefined')
            p=get('state')['physics'];assert p['scientific_generation']['model_version']in ('3.7.0','3.8.0')
            baseline=physical(p)
            if not page.evaluate('document.getElementById("gravity-instruments").open'):
                page.locator('#gravity-instruments summary').click()
            for index in range(3):
                page.locator('#instrument-selection').select_option('')
                page.locator('#prepare-instrument').click();idle(page)
                fill(page,'instrument-name','Histórico '+str(index+1))
                if index==2:
                    page.locator('#instrument-mode').select_option('follow')
                    page.locator('#instrument-body').select_option(p['bodies'][-1]['id'])
                    page.locator('#instrument-exclude').set_checked(True)
                    coordinates=[1e6,-2e6,3e6]
                else:
                    page.locator('#instrument-mode').select_option('fixed')
                    coordinates=[1.7e10+index*1e6,-9e9,3e9]
                for k,v in enumerate(coordinates):fill(page,'instrument-coordinate-'+str(k),v)
                page.locator('#apply-instrument').click()
                idle(page,'appState.physics.instruments.probes.length==='+str(index+1))
            page.locator('#measure-instruments').click();idle(page,'appState.instruments_preview?.readings.length===3')
            assert physical(get('state')['physics'])==baseline
            reading=get('state')['instruments_preview'];ids=[r['id'] for r in reading['readings']]
            if not page.evaluate('document.getElementById("instrument-history").open'):
                page.locator('#instrument-history summary').click()
            page.locator('#compare-probe-a').select_option(ids[0]);page.locator('#compare-probe-b').select_option(ids[1])
            page.locator('#compare-probes').click();idle(page,'appState.instrument_comparison!==null')
            comparison=get('state')['instrument_comparison']
            assert comparison['distance_m']==1e6 and comparison['same_included_sources']
            first,second=reading['readings'][:2]
            assert comparison['delta_acceleration_m_s2']==[b-a for a,b in zip(first['acceleration_m_s2'],second['acceleration_m_s2'])]
            assert np.allclose(np.linalg.eigvalsh(first['tidal_tensor_s_2']),comparison['first_tidal_eigenvalues_s_2'],rtol=1e-14,atol=0)
            page.locator('#compare-probe-b').select_option(ids[2]);page.locator('#compare-probes').click();idle(page)
            mismatch=get('state')['instrument_comparison']
            assert not mismatch['same_included_sources'] and mismatch['linear_tidal_prediction_m_s2'] is None
            assert 'fontes diferentes' in page.locator('#probe-comparison-reading').inner_text()
            page.locator('#compare-probe-b').select_option(ids[1])
            page.locator('#compare-probes').click();idle(page)
            page.locator('#history-cadence').select_option('0.25');idle(page,'appState.physics.instrument_history.cadence_wall_s===.25')
            page.locator('#history-toggle').click();idle(page,'appState.physics.instrument_history.recording')
            assert physical(get('state')['physics'])==baseline
            page.locator('#play').click();idle(page,'!appState.physics.paused')
            page.wait_for_function('appState.physics.instrument_history.sample_count>=8',timeout=15000)
            page.locator('#play').click();idle(page,'appState.physics.paused')
            frozen=get('state')['physics'];data=get('instruments/history')
            assert len(data['samples'])>=8
            assert all(a['time_s']<b['time_s'] for a,b in zip(data['samples'],data['samples'][1:]))
            page.wait_for_function('historyData?.next_sequence===appState.physics.instrument_history.next_sequence')
            page.locator('#history-quantity').select_option('potential_J_kg')
            page.locator('#history-scale').select_option('log')
            assert page.evaluate('historyPlotPoints.length')==0
            page.locator('#history-scale').select_option('linear')
            page.locator('#history-quantity').select_option('tidal_xx_s_2')
            assert page.evaluate('historyPlotPoints.length')==2*len(data['samples'])
            assert 'diferença em relação' in page.locator('#history-chart-legend').inner_text()
            # Use native mouse events on an actual archived graph point.
            sequence=data['samples'][2]['sequence']
            point=page.evaluate('(() => {const c=document.getElementById("history-chart");c.scrollIntoView({block:"center"});const r=c.getBoundingClientRect(),p=historyPlotPoints.find(p=>p.sequence==='+str(sequence)+'),z=Number(getComputedStyle(document.body).zoom)||1;return {x:(r.left+p.x*r.width/c.width)*z,y:(r.top+p.y*r.height/c.height)*z};})()')
            for event in ('mousePressed','mouseReleased'):
                page.call('Input.dispatchMouseEvent',{'type':event,**point,'button':'left','clickCount':1})
            idle(page,'document.getElementById("history-point-reading").textContent.includes("#'+str(sequence)+' ")')
            selected=post({'command':'history_point','system_id':frozen['system_id'],'edit_token':frozen['edit_token'],'sequence':sequence})['ack']['result']
            historic=get('state')['instruments_preview']
            assert historic['time']==selected['reading']['time']<frozen['time']
            assert physical(get('state')['physics'])==physical(frozen)
            page.wait_for_function('document.getElementById("instruments-status").textContent.includes("CONGELADA")')
            difference=0.
            for row in historic['render']['readings']:
                value=lua('return openspace.propertyValue('+json.dumps('Scene.'+row['scene_node']+'.Translation.Position')+')')
                if isinstance(value,dict):value=[value[str(k)] for k in (1,2,3)]
                difference=max(difference,max(abs(a-b) for a,b in zip(value,row['position_render_m'])))
            assert difference<.01
            assert selected['reading']['time']*frozen['physical_scale']['time_unit_s']==data['samples'][2]['time_s']
            page.locator('#history-export').click();idle(page)
            page.wait_for_function('document.getElementById("notice").textContent.startsWith("Exportado:")')
            export_path=Path(page.locator('#notice').inner_text().removeprefix('Exportado: '))
            exported=json.loads(export_path.read_text(encoding='utf8'))
            assert exported['history']['samples'][2]==selected and exported['history']['next_sequence']==data['next_sequence']
            page.locator('#save').click();idle(page)
            manifest=json.loads(latest.read_text());history=copy.deepcopy(manifest['instrument_history'])
            definitions=copy.deepcopy(frozen['instruments'])
            page.locator('#play').click();idle(page,'!appState.physics.paused');time.sleep(.4)
            page.locator('#play').click();idle(page,'appState.physics.paused')
            page.locator('#load').click();idle(page)
            restored=get('state')['physics']
            assert restored['bodies']==frozen['bodies'] and restored['time']==frozen['time'] and restored['conservation']==frozen['conservation']
            assert restored['instruments']==definitions and get('instruments/history')==data
            assert json.loads(latest.read_text())['instrument_history']==history
            rejected({'command':'history_point','system_id':frozen['system_id'],'edit_token':frozen['edit_token'],'sequence':sequence})
            restored_before=physical(restored)
            page.wait_for_function('historyData?.next_sequence===appState.physics.instrument_history.next_sequence')
            page.evaluate('document.getElementById("history-chart").scrollIntoView({block:"center"})');time.sleep(.3)
            subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts/capture-window.ps1'),'-Name','cosmos2-history-'+kind+'.png'],check=True,capture_output=True)
            page.locator('#history-clear').click();idle(page,'appState.physics.instrument_history.sample_count===0')
            cleared=get('state')['physics']
            assert physical(cleared)==restored_before and cleared['instruments']==definitions
            rejected({'command':'history_point','system_id':cleared['system_id'],'edit_token':cleared['edit_token'],'sequence':sequence})
            assert physical(get('state')['physics'])==restored_before
            cases.append({'kind':kind,'samples':len(data['samples']),'cadence_wall_s':.25,'same_instant_comparison_and_eigenvalues':True,
                'different_exclusions_disable_linear_T_prediction':True,'native_graph_click_original_sample_and_stale_mark':True,
                'native_marker_max_component_difference_m':difference,'negative_potential_log_gaps_explicit':True,
                'configure_select_clear_and_export_preserve_physics':True,'checkpoint_history_definitions_phase_and_reference_exact':True,
                'old_identity_and_removed_sequence_rejected':True,'full_export_has_original_SI_sources':True})
finally:
    try:post({'command':'atlas'})
    finally:
        socket.close()
        if saved is None:latest.unlink(missing_ok=True)
        else:latest.write_bytes(saved)
assert get('atlas/state')['epoch']==atlas['epoch'] and not errors
assert (latest.read_bytes() if latest.exists() else None)==saved
report={'status':'installed_native_history_verified','generation':p['scientific_generation']['model_version'],'browser':'native CEF','cases':cases,'page_errors':errors,
    'owner_checkpoint_pointer_sha256':hashlib.sha256(saved).hexdigest() if saved else None,'owner_checkpoint_pointer_restored':True,
    'atlas_epoch_preserved':True,'scope':'Partial C2-11 comparison and bounded history slice; branches/J2/material tides/resonances/256/10k remain'}
(ROOT/('evidence/instrument-history-ui-'+p['scientific_generation']['model_version']+'-check.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
