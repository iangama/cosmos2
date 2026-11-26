"""Actual UI controls for CNO species, individual channels and evaluated data."""
from pathlib import Path
import argparse
import json
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=4701);args=parser.parse_args()
errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
    page=browser.new_page(viewport={'width':1600,'height':1080})
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(f'http://127.0.0.1:{args.port}/forces.html')
    page.wait_for_function("document.getElementById('force-status').textContent.startsWith('Cálculo concluído')")
    page.locator('[data-scenario="cno"]').click();page.wait_for_function('!pending')
    assert page.evaluate('response.result.network.name')=='CNO-I'
    assert page.locator('[data-curve]').count()==8
    reference=page.evaluate('response.result.reference')
    fingerprint=page.evaluate('response.configuration_sha256')
    page.locator('[data-curve="3"]').set_checked(True)
    assert page.evaluate('response.configuration_sha256')==fingerprint
    page.locator('[data-force="weak"][data-control="acting"]').set_checked(False);page.wait_for_function('!pending')
    assert page.evaluate('response.result.network.neutrino_count_m3[240]')==0
    assert page.evaluate('response.result.network.energy_deposited_J_m3[240]')>0
    assert page.evaluate('response.result.reference')==reference
    page.locator('[data-force="weak"][data-control="acting"]').set_checked(True);page.wait_for_function('!pending')
    page.locator('[data-effect="cno_radiative_capture"]').set_checked(False);page.wait_for_function('!pending')
    assert page.evaluate('response.result.network.energy_available_J_m3[240]')==0
    page.locator('[data-effect="cno_radiative_capture"]').set_checked(True);page.wait_for_function('!pending')
    page.locator('[data-effect="cno_o15_beta"]').set_checked(False);page.wait_for_function('!pending')
    assert page.evaluate('response.result.network.neutrinos_by_parent_m3.o15[240]')==0
    assert page.evaluate('response.result.network.mass_fractions[240][6]')>0
    page.locator('[data-effect="cno_o15_beta"]').set_checked(True);page.wait_for_function('!pending')
    assert page.evaluate('response.result.reference.half_lives_s.o15')==122.266
    page.locator('[name="decay_evaluation"]').select_option('reaclib_wc12');page.locator('#calculate').click();page.wait_for_function('!pending')
    assert abs(page.evaluate('response.result.reference.half_lives_s.o15')-122)<.001
    page.locator('[name="decay_evaluation"]').select_option('nubase2020');page.locator('#calculate').click();page.wait_for_function('!pending')
    page.screenshot(path=str(ROOT/'evidence/forces-ui-cno.png'),full_page=True)
    page.set_viewport_size({'width':720,'height':900})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors,errors
    browser.close()
report={'browser':'native Windows Edge headless','weak_off_no_neutrinos_with_initial_capture_energy':True,
        'radiative_capture_off_stops_seeded_cycle':True,'o15_channel_independent':True,
        'evaluation_choice_changes_decay_rate':True,'curve_visibility_does_not_change_physics':True,
        'eight_species_available':True,'narrow_no_horizontal_overflow':True,'page_errors':errors,
        'scope':'UI and scientific HTTP result checks; full CEF/GN acceptance separate'}
(ROOT/'evidence/cno-ui-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
