"""J's actual acting/layer controls preserve frozen-core futures and SI readings.

Run after formal captures, never concurrently with a performance measurement.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys
from cef_page import Page
from websockets.sync.client import connect

ROOT=Path(__file__).resolve().parents[1]
J=ROOT/'output/c212-em-viewport-product'
G=ROOT/'output/c212-em-integration-product'
sys.path[:0]=[str(G/'app'),str(G/'em')]
from em_experiment import Experiment
from em_measurements import measure

parser=argparse.ArgumentParser();parser.add_argument('--label',default='release1')
args=parser.parse_args();assert args.label.isalnum()
DEST=ROOT/f'evidence/em-viewport-acting-layers-{args.label}-check.json';assert not DEST.exists()
session=json.loads((ROOT/'output/session.json').read_text(encoding='utf-8-sig'));assert session['emViewportCandidate']
owner=(ROOT/'user/sessions/latest.json').read_bytes()
saved={p:p.read_bytes() for p in (J/'c212-em-worker/product').glob('ui-phase*') if p.is_file()}
report={'completed':False,'checks':[],'JS_errors':[]}


def idle(page):
    page.wait_for_function('state&&state.paused&&!pending&&!nativeState.error&&nativeState.confirmation?.metadata.time_s===state.time_s',timeout=30000)


def panel(page,name):
    if page.evaluate('workspacePanel')!=name:page.locator('[data-panel="'+name+'"]').click()


def click(page,name,tool=None):
    if tool:panel(page,tool)
    page.locator('#'+name).click();idle(page)


def flags(nodes):
    code='local flags={};'+''.join('flags['+json.dumps(node)+']=openspace.propertyValue('+json.dumps('Scene.'+node+'.Renderable.Enabled')+');' for node in nodes)+'return {flags=flags}'
    with connect('ws://127.0.0.1:4682',open_timeout=3,close_timeout=.2,ping_interval=None) as ws:
        ws.send(json.dumps({'type':'apiHandshake','apiVersion':{'major':1,'minor':0,'patch':0}}))
        ws.send(json.dumps({'topic':1,'type':'luascript','payload':{'return':True,'script':code}}))
        return json.loads(ws.recv(timeout=5))['payload']['1']['flags']


try:
    with Page() as page:
        page.on('pageerror',lambda error:report['JS_errors'].append(error))
        page.goto('http://127.0.0.1:4700/');page.wait_for_function('typeof appState!=="undefined"&&appState')
        page.locator('#em-lab').click();idle(page);page.locator('#interface-scale').select_option('1')
        scenarios=(('electric','electric','electric'),('helix','magnetic','magnetic'),
                   ('crossed','electric','electric'),('crossed','magnetic','magnetic'),
                   ('dipole','magnetic','magnetic'),('coulomb','electric','electric'),
                   ('electric','electric','potential'),('coulomb','electric','potential'))
        for preset,term,layer in scenarios:
            outcomes={}
            for acting in (False,True):
                for visible in (False,True):
                    panel(page,'experience');page.locator('#preset').select_option(preset);click(page,'load-preset')
                    page.locator('#acting-'+('e' if term=='electric' else 'b')).set_checked(acting);idle(page)
                    click(page,'measure-potential' if layer=='potential' else 'measure','layers')
                    page.locator('#visible-'+('potential' if layer=='potential' else 'e' if layer=='electric' else 'b')).set_checked(visible);idle(page)
                    snapshot=page.evaluate('JSON.parse(JSON.stringify(state))')
                    reference=Experiment.from_payload(snapshot['experiment']);reference.advance(32)
                    nodes=page.evaluate('[...(nativeState.'+('potential.render' if layer=='potential' else 'map')+'.meshes||[])].filter(m=>'+('true' if layer=='potential' else 'm.quantity==='+json.dumps(layer))+').map(m=>m.node)')
                    assert nodes,(preset,term,layer)
                    enabled=flags(nodes);assert enabled and all(value is visible for value in enabled.values())
                    page.evaluate('command("advance",{...guard(),steps:32})');idle(page)
                    actual=page.evaluate('JSON.parse(JSON.stringify(state))')
                    assert actual['experiment']==json.loads(json.dumps(reference.payload()))
                    click(page,'measure-particle','readings')
                    reading=page.evaluate('particleMeasurement');expected=measure(actual)
                    assert reading['force']==expected['force'] and reading['energy']==expected['energy']
                    assert reading['time_s']==actual['time_s']
                    if layer=='potential':
                        assert 'CONGELADO' in page.locator('#potential-legend').inner_text()
                    outcomes[(acting,visible)]=actual['experiment']['phase']
                    report['checks'].append({'preset':preset,'term':term,'layer':layer,'acting':acting,'visible':visible,
                                             'native_layer_flags_confirmed':True,'future32_exact_against_frozen_G':True,
                                             'force_and_energy_match_frozen_instrument':True,'time_s':actual['time_s']})
            for acting in (False,True):assert outcomes[(acting,False)]==outcomes[(acting,True)]
            assert outcomes[(False,False)]!=outcomes[(True,False)]
        page.evaluate('command("load",{...guard(),file:"ui-phase"})');idle(page)
        page.locator('#native-return').click();page.wait_for_function('location.pathname==="/"')
        assert not report['JS_errors'] and owner==(ROOT/'user/sessions/latest.json').read_bytes()
        assert all(path.read_bytes()==data for path,data in saved.items())
        report.update(completed=True,saved_files_and_owner_preserved=True,
                      scope='32actual acting/layer combinations across five presets and potential. Native enabled flags independently queried; visibility preserves32step exact futures, acting changes phase, SI readings use the validated frozen G instrument. No new scientific-domain or performance acceptance.')
finally:
    paths=[Path(__file__),G/'app/em_measurements.py',*[p for p in (J/'app').rglob('*') if p.is_file() and '__pycache__' not in p.parts]]
    report['source_sha256']={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    DEST.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'completed':report['completed'],'combinations':len(report['checks'])}),flush=True)
