"""Ten evaluated parents and actual native controls for partial decay widths."""
from pathlib import Path
import argparse
import json
import math
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
from forces import evaluate

parser = argparse.ArgumentParser();parser.add_argument('--native', action='store_true');args = parser.parse_args()
base = 'http://127.0.0.1:' + ('4700' if args.native else '4701')
save_path = ROOT / 'user/forces/latest.json'
original = save_path.read_bytes() if save_path.exists() else None
errors = []


def get(path):
    return json.load(urllib.request.urlopen(base + path, timeout=20))


def settled(page):
    page.wait_for_function('response&&response.result.decays&&!pending')
    assert 'Cálculo concluído' in page.locator('#force-status').inner_text(), page.locator('#force-status').inner_text()


def choose(page, case):
    page.locator('[name="parent_case"]').select_option(case)
    settled(page)
    assert page.evaluate('config.parameters.parent_case') == case


def apply(page, key, value):
    page.evaluate('document.querySelector(' + json.dumps('[name="' + key + '"]') + ').value=' + json.dumps(str(value)))
    page.locator('#calculate').click();settled(page)


def instant(page, value):
    page.evaluate('document.getElementById("time-index").value=' + json.dumps(str(value)) + ';document.getElementById("time-index").dispatchEvent(new Event("input"));')


def capture(page, label, selector='#science-view'):
    page.evaluate('document.querySelector(' + json.dumps(selector) + ').scrollIntoView({block:"center"})')
    if args.native:
        subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                        str(ROOT / 'scripts/capture-window.ps1'), '-Name', f'cosmos2-native-decays-{label}.png'],
                       check=True, capture_output=True)
    else:
        page.screenshot(path=str(ROOT / f'evidence/decays-ui-{label}.png'), full_page=True)


def exercise(page):
    page.on('pageerror', lambda error: errors.append(str(error)))
    before, physics = get('/api/atlas/state'), get('/api/state')['physics']
    page.goto(base + '/forces.html#decays');settled(page)
    cases = []
    for case in ('n','t','c14','be7','n13','o15','f18','na22','sr90','y90'):
        choose(page, case)
        r = page.evaluate('response.result')
        assert page.locator('[data-decay-branch]').count() == len(r['decays']['channel_order'])
        assert page.locator('#decay-populations tbody tr').count() == len(r['decays']['node_ids'])
        assert math.isclose(r['decays']['population_fractions'][60][0], .5, rel_tol=1e-12)
        assert page.evaluate('!document.querySelector(\'[data-parameter="initial_daughter_fraction"]\').hidden') == (case == 'sr90')
        instant(page, 0)
        assert '0' in page.locator('#decay-readings').inner_text()
        instant(page, 60)
        assert '5.00000e+5' in page.locator('#decay-populations tbody tr:nth-child(1)').inner_text()
        instant(page, 240)
        snapshot = page.evaluate('response.result')
        identity = page.evaluate('response.physics_sha256')
        page.locator('[data-force="weak"][data-control="visible"]').set_checked(False);settled(page)
        assert page.evaluate('response.result') == snapshot
        assert page.evaluate('response.physics_sha256') == identity
        page.locator('[data-force="weak"][data-control="visible"]').set_checked(True);settled(page)
        cases.append(case)
    choose(page, 'f18')
    source = page.evaluate('response.result.reference')
    page.locator('[data-effect="decay_f18_beta_plus_0"]').set_checked(False);settled(page)
    assert page.evaluate('response.result.decays.positron_count[240]') == 0
    assert page.evaluate('response.result.decays.captured_electron_count[240]') > 0
    assert page.evaluate('response.result.decays.population_fractions[240][0]') > .9
    assert page.evaluate('response.result.reference') == source
    capture(page, 'f18-ec-only')
    page.locator('[data-force="weak"][data-control="acting"]').set_checked(False);settled(page)
    assert page.evaluate('response.result.decays.populations[240][0]') == 1e6
    assert page.evaluate('response.result.decays.energy_available_J[240]') == 0
    page.locator('[data-force="weak"][data-control="acting"]').set_checked(True);settled(page)
    page.locator('[data-effect="decay_f18_beta_plus_0"]').set_checked(True);settled(page)
    choose(page, 'na22')
    assert '99,996%' in page.locator('[data-decay-parent="na22"]').inner_text()
    assert '90.57' in page.locator('[data-decay-parent="na22"]').inner_text()
    page.locator('[data-decay-branch="na22_beta_plus_0"] summary').click()
    assert 'campo original' in page.locator('[data-decay-branch="na22_beta_plus_0"] details').inner_text()
    capture(page, 'na22-branches', '[data-decay-branch]')
    choose(page, 'n')
    assert page.evaluate('response.result.reference.parents.n.half_life_s') == 613.9
    assert page.evaluate('response.result.reference.parents.n.NUBASE2020_comparison.half_life_s') == 609.8
    choose(page, 'sr90')
    identity = page.evaluate('response.physics_sha256')
    page.locator('#chart-axis').select_option('log')
    assert page.evaluate('response.physics_sha256') == identity
    capture(page, 'sr-y-long')
    page.locator('#chart-axis').select_option('linear')
    apply(page, 'initial_daughter_fraction', .4)
    apply(page, 'duration_half_lives', .001)
    assert page.evaluate('response.result.decays.populations[0][1]') == 400000
    assert page.evaluate('response.result.decays.populations[240][2]') > 0
    capture(page, 'sr-y-transient')
    daughter_keys = page.evaluate('response.result.reference.parents.y90.channels')
    for key in daughter_keys:
        page.locator('[data-effect="decay_' + key + '"]').set_checked(False);settled(page)
    assert page.evaluate('response.result.decays.populations[240][1]') > 400000
    assert page.evaluate('response.result.decays.populations[240][2]') == 0
    assert page.evaluate('response.result.reference.full_evolution.populations[240][2]') > 0
    capture(page, 'sr-y-held', '#decay-populations')
    page.locator('#save-forces').click()
    page.wait_for_function('document.getElementById("force-status").textContent.startsWith("Condições, controles")')
    saved = page.evaluate('config')
    choose(page, 'c14')
    page.locator('#load-forces').click()
    page.wait_for_function('!pending&&!document.getElementById("restoration-note").hidden')
    assert page.evaluate('config') == saved
    assert page.evaluate('document.getElementById("restoration-note").dataset.state') == 'same_generation'
    page.locator('#export-forces').click()
    page.wait_for_function('!pending&&lastForcesExport')
    exported = page.evaluate('lastForcesExport')
    disk = json.loads(Path(exported['export_file']).read_text(encoding='utf-8'))
    assert {k: v for k, v in disk.items() if k != 'export_file'} == evaluate(disk['configuration'])
    identity = page.evaluate('response.physics_sha256')
    invalid = page.evaluate('fetch("/api/forces/evaluate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({scenario:"decays",parameters:{initial_daughter_fraction:2}})}).then(async r=>({status:r.status,body:await r.json()}))')
    assert invalid['status'] == 400 and invalid['body']['ok'] is False
    assert page.evaluate('response.physics_sha256') == identity
    if not args.native:
        page.set_viewport_size({'width': 720, 'height': 900})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        capture(page, '720')
        page.locator('#science-view').screenshot(path=str(ROOT / 'evidence/decays-ui-720-chart.png'))
    assert get('/api/atlas/state')['bodies'] == before['bodies']
    assert get('/api/atlas/state')['epoch'] == before['epoch']
    assert get('/api/state')['physics'] == physics
    page.goto(base + '/')
    assert not errors, errors
    return cases, exported['export_file']


try:
    if args.native:
        from cef_page import Page
        with Page() as page: cases, export_file = exercise(page)
    else:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='msedge', headless=True)
            cases, export_file = exercise(browser.new_page(viewport={'width': 1600, 'height': 1080}))
            browser.close()
finally:
    if original is None: save_path.unlink(missing_ok=True)
    else: save_path.write_bytes(original)
report = {'ok': True, 'browser': 'native CEF' if args.native else 'Windows Edge', 'cases': cases,
          'source_evaluations_and_normalization_visible': True, 'partial_width_gate_not_renormalized': True,
          'EC_counts_separate_from_positrons': True, 'Sr_Y_feeding_and_initial_daughter': True,
          'daughter_held_accumulates_and_reference_preserved': True, 'timeline_population_activity_leptons_energy': True,
          'view_preserves_physical_identity': True, 'source_scene_and_worker_preserved': True,
          'generation_save_load_and_actual_export': export_file, 'user_save_restored': True,
          'invalid_request_preserves_result': True, 'page_errors': errors,
          'overflow_720': None if args.native else False}
name = 'native-decays-check.json' if args.native else 'decays-ui-check.json'
(ROOT / 'evidence' / name).write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
