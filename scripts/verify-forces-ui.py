"""Exercise the actual local scientific UI in native Windows Edge."""
from pathlib import Path
import argparse
import json
import sys
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--port',type=int,default=4701)
args=parser.parse_args()
errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
    page=browser.new_page(viewport={'width':1600,'height':1080},device_scale_factor=1)
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(f'http://127.0.0.1:{args.port}/forces.html')
    page.wait_for_function("document.getElementById('force-status').textContent.startsWith('Cálculo concluído')")
    checks=[]
    for scenario in ('gravity','electromagnetic','strong','weak'):
        page.locator(f'[data-scenario="{scenario}"]').click()
        page.wait_for_function('!pending')
        for acting in (False,True):
            for visible in (False,True):
                a=page.locator(f'[data-force="{scenario}"][data-control="acting"]')
                v=page.locator(f'[data-force="{scenario}"][data-control="visible"]')
                a.set_checked(acting)
                page.wait_for_function('!pending')
                v.set_checked(visible)
                page.wait_for_function('!pending')
                state=page.evaluate('({config:config,result:response.result,counterfactual:response.counterfactual})')
                assert state['config']['controls'][scenario]['acting']==acting
                assert state['config']['controls'][scenario]['visible']==visible
                assert state['counterfactual'] == (not acting)
                assert state['result']['measurements'][1]['value']==0 if not acting else state['result']['measurements'][1]['value']>0
                checks.append({'scenario':scenario,'acting':acting,'visible':visible})
        page.screenshot(path=str(ROOT/'evidence'/f'forces-ui-{scenario}.png'),full_page=True)
    page.locator('[data-scenario="electromagnetic"]').click();page.wait_for_function('!pending')
    page.locator('[name="E_Vm"]').fill('1');page.locator('#calculate').click();page.wait_for_function('!pending')
    effect_checks=[]
    for electric,magnetic in ((False,False),(False,True),(True,False),(True,True)):
        page.locator('[data-effect="electric_acceleration"]').set_checked(electric);page.wait_for_function('!pending')
        page.locator('[data-effect="magnetic_deflection"]').set_checked(magnetic);page.wait_for_function('!pending')
        fields=page.evaluate('response.result.applied_fields')
        assert fields=={'E_Vm':int(electric),'B_T':.001*int(magnetic)}
        effect_checks.append(fields)
    page.locator('[data-scenario="weak"]').click();page.wait_for_function('!pending')
    species_checks={}
    for species in ('n','t','c14','be7'):
        page.locator('[name="species"]').select_option(species)
        page.locator('#calculate').click();page.wait_for_function('!pending')
        state=page.evaluate('response.result.reference')
        assert state['parent']==species
        species_checks[species]=state['half_life_s']
    assert page.locator('[data-effect="electron_capture"]').count()==1
    assert page.locator('[data-effect="beta_decay"]').count()==0
    page.locator('[data-effect="electron_capture"]').set_checked(False);page.wait_for_function('!pending')
    assert page.evaluate('response.result.measurements[3].value')==0
    assert page.evaluate('response.result.reference.products')==['li7','nu_e']
    page.locator('[data-effect="electron_capture"]').set_checked(True);page.wait_for_function('!pending')
    page.screenshot(path=str(ROOT/'evidence/forces-ui-weak-carbon14.png'),full_page=True)
    page.locator('[data-scenario="stellar"]').click();page.wait_for_function('!pending')
    assert page.evaluate('response.result.network.channels.pp') is True
    stellar_reference=page.evaluate('response.result.reference')
    page.locator('[data-effect="pp_fusion"]').set_checked(False);page.wait_for_function('!pending')
    assert page.evaluate('response.result.network.neutrino_count_m3[240]')==0
    assert page.evaluate('response.result.network.energy_available_J_m3[240]')==0
    assert page.evaluate('response.result.reference')==stellar_reference
    page.locator('[data-effect="pp_fusion"]').set_checked(True);page.wait_for_function('!pending')
    page.locator('[data-effect="stellar_radiative_capture"]').set_checked(False);page.wait_for_function('!pending')
    assert page.evaluate('response.result.network.channels.dp') is False
    assert page.evaluate('response.result.network.channels.pp') is True
    assert page.evaluate('response.result.network.mass_fractions[240][1]')>0
    page.locator('[data-effect="stellar_radiative_capture"]').set_checked(True);page.wait_for_function('!pending')
    page.screenshot(path=str(ROOT/'evidence/forces-ui-stellar.png'),full_page=True)
    before_hash=page.evaluate('response.configuration_sha256')
    page.locator('#chart-axis').select_option('linear')
    assert before_hash==page.evaluate('response.configuration_sha256')
    page.locator('#chart-axis').select_option('log')
    assert before_hash==page.evaluate('response.configuration_sha256')
    # Check user-entered values really change computed data.
    page.locator('[data-scenario="strong"]').click();page.wait_for_function('!pending')
    before=page.evaluate('response.result.reference.rate_cm3_mol_s')
    page.locator('[name="temperature_K"]').fill('30000000')
    page.locator('#calculate').click();page.wait_for_function('!pending')
    after=page.evaluate('response.result.reference.rate_cm3_mol_s')
    assert before != after
    # Arrow click reads a calculated vector, and orbit controls change view only.
    page.locator('[data-scenario="gravity"]').click();page.wait_for_function('!pending')
    before_hash=page.evaluate('response.configuration_sha256')
    box=page.locator('#science-view').bounding_box()
    page.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2)
    page.mouse.down();page.mouse.move(box['x']+box['width']/2+80,box['y']+box['height']/2+35);page.mouse.up()
    assert before_hash==page.evaluate('response.configuration_sha256')
    arrow=page.evaluate('projectedArrows[10]')
    page.mouse.click(box['x']+arrow['x'],box['y']+arrow['y'])
    assert 'Campo de referência' in page.locator('#probe').inner_text()
    # Verify responsive layout and absence of horizontal clipping.
    page.set_viewport_size({'width':720,'height':900})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path=str(ROOT/'evidence/forces-ui-narrow.png'),full_page=True)
    assert not errors,errors
    browser.close()
report={'platform':sys.platform,'browser':'native Windows Edge headless','control_checks':checks,
        'separate_electric_magnetic_effects':effect_checks,'weak_species_half_lives_s':species_checks,
        'stellar_pp_off_no_neutrinos_or_energy':True,'stellar_em_capture_off_accumulates_deuterium':True,
        'chart_axis_does_not_change_science':True,'electron_capture_distinct_from_beta':True,
        'temperature_changes_rate':True,'probe_reads_vector':True,'camera_does_not_change_physics':True,
        'narrow_no_horizontal_overflow':True,'page_errors':errors,
        'scope':'UI and HTTP checks; does not certify OpenSpace CEF or all force models'}
(ROOT/'evidence/forces-ui-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='control_checks'},indent=2))
