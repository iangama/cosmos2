"""Inspect reaction-network rates and species probes through actual DOM controls."""
from pathlib import Path
import argparse
import json
import math
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=4701);args=parser.parse_args()
errors=[];checks=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
    page=browser.new_page(viewport={'width':1600,'height':1080})
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(f'http://127.0.0.1:{args.port}/forces.html')
    page.wait_for_function("document.getElementById('force-status').textContent.startsWith('Cálculo concluído')")
    for stage in ('stellar','cno'):
        page.locator(f'[data-scenario="{stage}"]').click();page.wait_for_function('!pending')
        fingerprint=page.evaluate('response.configuration_sha256')
        page.locator('#network-view').select_option('reactions')
        assert page.evaluate('isNetworkView()')
        assert page.evaluate('response.configuration_sha256')==fingerprint
        species=page.evaluate('response.result.network.species')
        assert page.locator('[data-nucleus]').count()==len(species)
        page.locator('#time-index').fill('0')
        first=page.locator('[data-channel-rate]').all_text_contents()
        page.locator('[data-nucleus="p"]').click()
        assert 'Densidade numérica' in page.locator('#probe').inner_text()
        page.locator('#time-index').fill('240')
        last=page.locator('[data-channel-rate]').all_text_contents()
        assert first!=last
        assert page.evaluate('response.configuration_sha256')==fingerprint
        actual=page.evaluate('response.result')
        assert all(math.isclose(x,actual['network']['final_event_rates_m3_s'][item['key']],rel_tol=1e-14)
                   for x,item in zip(actual['network']['event_rates_m3_s'][-1],actual['reactions']))
        nucleus=page.evaluate('projectedArrows[1]')
        canvas=page.locator('#science-view').bounding_box()
        page.mouse.click(canvas['x']+nucleus['x'],canvas['y']+nucleus['y'])
        assert page.evaluate('selectedNucleus')==nucleus['nucleus']
        assert 'Fração mássica' in page.locator('#probe').inner_text()
        page.locator('[data-force="weak"][data-control="visible"]').set_checked(False);page.wait_for_function('!pending')
        assert page.evaluate('response.result')==actual
        page.locator('[data-force="weak"][data-control="acting"]').set_checked(False);page.wait_for_function('!pending')
        assert page.evaluate('response.result.network.neutrino_count_m3[240]')==0
        assert page.evaluate('projectedArrows.length')==(6 if stage=='cno' else 4)
        page.locator('[data-force="weak"][data-control="visible"]').set_checked(True);page.wait_for_function('!pending')
        page.locator('[data-force="weak"][data-control="acting"]').set_checked(True);page.wait_for_function('!pending')
        page.locator('#science-view').scroll_into_view_if_needed()
        page.screenshot(path=str(ROOT/f'evidence/forces-ui-{stage}-network.png'),full_page=True)
        page.set_viewport_size({'width':720,'height':900})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.locator('#network-view').select_option('curves')
        assert page.locator('[data-nucleus]').count()==0
        page.set_viewport_size({'width':1600,'height':1080})
        checks.append({'stage':stage,'rates_follow_time':True,'node_and_button_probes':True,
                       'view_preserves_physics':True,'weak_reference_separate':True})
    assert not errors,errors
    browser.close()
report={'browser':'native Windows Edge headless','networks':checks,'page_errors':errors,
        'narrow_no_horizontal_overflow':True,'scope':'UI/HTTP, network diagram is not spatial nuclear structure'}
(ROOT/'evidence/networks-ui-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
