"""Consolidate bounded offline evidence and preserve private test artifacts without promotion."""
from pathlib import Path
import argparse
import datetime as dt
import hashlib
import json
import os
import shutil

import psutil

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / 'output/original-flow-hotfix-staging-v2'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('Invalid label')
    out = ROOT / ('evidence/original-flow-hotfix-review-' + args.label + '.json')
    folder = ROOT / ('output/original-flow-hotfix-review-' + args.label)
    assert not out.exists() and not folder.exists(), 'Preserve review evidence'
    folder.mkdir()
    names = ['evidence/original-panels-ui-offline-20261120e-before.json',
             'evidence/original-panels-ui-offline-20261120f-candidate.json',
             'evidence/original-panels-ui-offline-20261120g-zoom.json',
             'evidence/original-flow-hotfix-http-20261120a.json']
    proofs = {}
    for name in names:
        value = json.loads((ROOT / name).read_text())
        assert value['accepted'] and value['completed'] and not value['native_user_flow_accepted']
        assert all(sha(ROOT / path) == digest for path, digest in value['source_sha256'].items()), name
        proofs[name] = dict(sha256=sha(ROOT / name), checks=len(value['checks']),
                           passed=value.get('passed'), failed=value.get('failed'),
                           expected_existing_defects=value.get('expected_existing_defects', False))
    baseline = json.loads((ROOT / names[0]).read_text())
    candidate = json.loads((ROOT / names[1]).read_text())
    assert baseline['failed'] == 16 and candidate['passed'] == 22 and candidate['failed'] == 0
    assert not json.loads((ROOT / names[2]).read_text())['failed']
    original = ROOT / 'output/is6-expanded-journey-product0.27.0/app/ui'
    parent = ROOT / 'output/original-forces-hotfix-staging/app/ui'
    panel_identity = {name: sha(original / name) for name in
                      ['index.html', 'is6-spatial.js', 'is6-layers.js', 'is6-spatial.css', 'is6-layers.css', 'navigation.js']}
    assert all(sha(parent / name) == digest for name, digest in panel_identity.items())
    preparation = json.loads((CANDIDATE / 'preparation.json').read_text())
    assert len(preparation['scientific_python_unchanged']) == 137
    assert all(sha(CANDIDATE / 'app' / name) == digest
               for name, digest in preparation['scientific_python_unchanged'].items())
    repair = json.loads((ROOT / 'evidence/original-forces-dependency-repair-20261114a.json').read_text())
    assert repair['added'] == 96 and repair['source_code_unchanged']
    assert all(sha(ROOT / row['destination']) == row['sha256'] for row in repair['planned'])
    private = []
    for file in sorted((CANDIDATE / 'user').rglob('*.json')):
        relative = file.relative_to(CANDIDATE / 'user')
        destination = folder / 'private-science-records' / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, destination)
        assert sha(destination) == sha(file)
        private.append(dict(source=file.relative_to(ROOT).as_posix(),
                            preserved=destination.relative_to(ROOT).as_posix(), sha256=sha(file)))
    assert private
    processes = []
    own = {os.getpid(), os.getppid()}
    for process in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
        try:
            value = process.info
            if value['pid'] in own:
                continue
            command = ' '.join(value['cmdline'] or []).replace('\\', '/').lower()
            exe = (value['exe'] or '').replace('\\', '/').lower()
            if ('cosmos2/' in exe and (value['name'] or '').lower() == 'openspace.exe'
                    or 'cosmos2/' in command and '/app/server.py' in command):
                processes.append(value)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    assert not any('original-flow-hotfix' in ' '.join(row['cmdline'] or []) for row in processes), 'An isolated HTTP server is still running'
    result = dict(accepted=True, completed=True, recorded_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                  candidate=CANDIDATE.relative_to(ROOT).as_posix(), installed=False, promoted=False,
                  native_user_flow_accepted=False, manual_test_completion_indicated=False,
                  scope='Offline correction review only. Final integrated panel remains unimplemented. Owner workflow requires the original launcher and buttons after manual-test completion is indicated.',
                  baseline_panel_identity_with_original_027=panel_identity,
                  reproduced_existing_failures=[row['name'] for row in baseline['checks'] if not row['passed']],
                  candidate_checks=22, actual_scale_layout_checks=4, http_checks=14,
                  scientific_python_unchanged=137, previous_dependency_repairs_rechecked=96,
                  preparation_sha256=sha(CANDIDATE / 'preparation.json'), proofs=proofs,
                  private_test_records=private, observed_app_server_processes=processes,
                  stale_session_metadata_note='output/session.json records the previous launch; absent processes do not indicate that the owner ended manual testing.',
                  superseded_test_notes=[
                      '20261120a-before / b-candidate: isDisabled on fieldset is not an effective-control check; preserved, superseded by v3.',
                      '20261120c-before / d-candidate: generic panel wait selected another fieldset; preserved, superseded by v3.',
                      'v3 large-ui screenshots check that class only. Actual CSS zoom and the original ui-scale handler were separately checked in 20261120g-zoom.'],
                  review_script_sha256=sha(Path(__file__)))
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps(dict(accepted=True, candidate_checks=22, actual_scale_layout_checks=4, http_checks=14,
                          scientific_python_unchanged=137, private_records=len(private),
                          observed_app_server_processes=len(processes), native_user_flow_accepted=False)))


if __name__ == '__main__':
    main()
