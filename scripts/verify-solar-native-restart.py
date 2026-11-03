"""Two-phase native scale and checkpoint check around a full normal restart."""
from pathlib import Path
import argparse
import json
import time
import traceback
import zipfile
from importlib.machinery import SourceFileLoader

ROOT = Path(__file__).resolve().parents[1]
native_test = SourceFileLoader('solar_native_test', str(ROOT / 'scripts/verify-native-solar-integration.py')).load_module()
get, click, sha = native_test.get, native_test.click, native_test.sha
Page, BASE = native_test.Page, native_test.BASE


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    parser.add_argument('--phase', required=True, choices=['prepare', 'verify'])
    args = parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('Invalid label.')
    folder = ROOT / ('output/is12-restart-' + args.label)
    receipt = ROOT / ('evidence/is12-restart-' + args.label + '.json')
    owner = ROOT / 'user/sessions/latest.json'
    checkpoint = ROOT / 'output/is12-solar-product/gravity-sessions/latest.json'
    if args.phase == 'prepare':
        if folder.exists() or receipt.exists():
            raise FileExistsError('Preserve previous restart evidence.')
        folder.mkdir()
        files = sorted(p for p in (ROOT / 'output/is12-solar-product/app').rglob('*')
                       if p.is_file() and '__pycache__' not in p.parts)
        files += [Path(__file__).resolve(), ROOT / 'scripts/verify-native-solar-integration.py']
        archive = folder / 'executed-sources.zip'
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
            for p in files:
                z.write(p, p.relative_to(ROOT).as_posix())
        report = {'schema': 1, 'source_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in files},
                  'source_archive_sha256': sha(archive), 'owner_pointer_sha256': sha(owner),
                  'session_before': json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig')),
                  'checks': {}, 'captures': [], 'prepared': False, 'completed': False, 'accepted': False,
                  'scope': 'Real native 100/150% controls and physics checkpoint after new engine/server processes. No camera persistence or performance acceptance.'}
    else:
        report = json.loads(receipt.read_text(encoding='utf-8'))
        assert report['prepared'] and not report['completed'] and 'failure' not in report

    def persist():
        receipt.write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')

    persist()
    try:
        assert sha(owner) == report['owner_pointer_sha256']
        errors = []
        with Page() as page:
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(BASE+'/')
            page.wait_for_function('appState!==null&&atlasState!==null&&!pending')
            if args.phase == 'prepare':
                assert get('/api/state')['physics']['atlas_initial']['kind'] == 'solar_four_physical_centers'
                click(page, '#play')
                page.wait_for_function('appState.physics.time>0&&!pending')
                time.sleep(.3)
                click(page, '#play')
                for scale in ['1', '1.5']:
                    page.locator('#ui-scale').select_option(scale)
                    if not page.evaluate('document.getElementById("solar-panel").open'):
                        click(page, '#solar-panel > summary')
                    earth = next(b for b in get('/api/state')['physics']['bodies'] if b['reference_id']=='sol:naif:399')
                    page.locator('#solar-body').select_option(earth['id'])
                    click(page, '#solar-sample')
                    page.wait_for_function('solarReading?.body_reference_id==="sol:naif:399"&&!pending')
                    click(page, '#solar-view-body')
                    assert page.locator('[data-solar-source]').count() == 3
                    assert page.evaluate('getComputedStyle(document.getElementById("solar-reading")).whiteSpace') == 'pre-line'
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                    report['captures'].append(native_test.capture(args.label, 'scale-'+str(int(float(scale)*100))))
                page.locator('#ui-scale').select_option('1')
                click(page, '#lab-earth-moon')
                report['captures'].append(native_test.capture(args.label, 'pair-centered'))
                click(page, '#save')
                expected = get('/api/state')['physics']
                expected_path = folder / 'saved-physics.json'
                expected_path.write_text(json.dumps(expected, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
                report['expected_sha256'] = sha(expected_path)
                report['checkpoint_sha256'] = sha(checkpoint)
                report['checks']['native_controls_100_150_and_reading'] = True
                report['prepared'] = True
            else:
                current = json.loads((ROOT / 'output/session.json').read_text(encoding='utf-8-sig'))
                assert current['solarIntegrationCandidate'] and current['app'] != report['session_before']['app']
                assert current['server'] != report['session_before']['server']
                assert current['storage'] == report['session_before']['storage']
                expected_path = folder / 'saved-physics.json'
                assert sha(expected_path) == report['expected_sha256']
                expected = json.loads(expected_path.read_text(encoding='utf-8'))
                assert sha(checkpoint) == report['checkpoint_sha256']
                click(page, '#experiment')
                click(page, '#load')
                page.wait_for_function('appState?.physics?.atlas_initial?.kind==="solar_four_physical_centers"&&!pending', timeout=70000)
                actual = get('/api/state')['physics']
                for key in ['bodies', 'atlas_initial', 'interventions', 'revision', 'time', 'scientific_generation']:
                    assert actual[key] == expected[key], key
                assert actual['paused'] and actual['restoration']['status'] == 'same_generation'
                assert sha(checkpoint) == report['checkpoint_sha256']
                report['checks']['native_restored_position_max_m'] = native_test.positions(actual)
                report['checks']['exact_physics_source_and_checkpoint_after_full_restart'] = True
                report['session_after'] = current
                report['captures'].append(native_test.capture(args.label, 'after-full-restart'))
                report['completed'] = report['accepted'] = True
        assert sha(owner) == report['owner_pointer_sha256']
        assert all(sha(ROOT / name) == value for name, value in report['source_sha256'].items())
        assert not errors, errors
        report['checks']['owner_pointer_preserved'] = True
        report['checks']['page_errors_'+args.phase] = errors
    except Exception:
        report['accepted'] = False
        report['failure'] = traceback.format_exc()
    finally:
        persist()
    print(json.dumps({'receipt': receipt.relative_to(ROOT).as_posix(), 'phase': args.phase,
                      'prepared': report['prepared'], 'accepted': report['accepted'], 'failure': report.get('failure')}))
    return 0 if 'failure' not in report else 1


if __name__ == '__main__':
    raise SystemExit(main())
