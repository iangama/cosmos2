"""Offline coverage, provenance and native-trace refusals before any sustained profile."""
import argparse
import copy
import datetime as dt
import hashlib
import json
from pathlib import Path
import traceback
import zipfile

import expanded_residency_contract_v2 as c
import expanded_residency_audit as audit

ROOT = Path(__file__).resolve().parents[1]
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    assert args.label and len(args.label) <= 20 and all(ch in 'abcdefghijklmnopqrstuvwxyz0123456789-' for ch in args.label)
    folder = ROOT / f'output/is6-expanded-residency-audit-offline-{args.label}'
    out = ROOT / f'evidence/is6-expanded-residency-audit-offline-{args.label}.json'
    assert not folder.exists() and not out.exists()
    names = ['scripts/expanded_residency_audit.py', 'scripts/expanded_residency_contract_v2.py',
             'scripts/collect_expanded_residency_v2.py', 'scripts/profile-expanded-residency.py',
             'scripts/audit-expanded-residency.py', 'scripts/run-expanded-residency.py',
             'scripts/verify-expanded-residency-audit.py', 'IS-6-PERCURSO-AMPLIADO16-RESIDENCIA-REVISAO-B.md',
             'evidence/is6-expanded-journey-native-20261113a.json', 'evidence/is6-expanded-instruments-service-20261113c.json',
             'evidence/is6-dynamics16-profile-20261112a.json']
    sources = {name: sha(ROOT / name) for name in names}
    folder.mkdir()
    with zipfile.ZipFile(folder / 'executed-sources.zip', 'x', zipfile.ZIP_DEFLATED) as archive:
        for name in sources:
            archive.write(ROOT / name, name)
    answer = dict(accepted=False, completed=False, source_sha256=sources, checks=[], refusals=[],
                  scope='Synthetic offline boundary/coverage and preserved scientific/native fixtures; no new performance measurement.')

    def refuse(name, call):
        try:
            call()
        except (ValueError, KeyError, TypeError, AssertionError) as error:
            answer['refusals'].append(dict(name=name, error=str(error)))
        else:
            raise AssertionError('Invalid fixture accepted: ' + name)

    try:
        seed = json.loads((ROOT / names[-3]).read_text())
        service = json.loads((ROOT / names[-2]).read_text())
        phase = c.physical(seed['common_source_phase4'])
        phase['edit_token'] = 'offline-renewed'
        inactive = dict(active=False, busy=False, error=None, recovery_required=False)
        value = dict(mode='experiment', renderer_confirmed=True, physics=phase,
                     modules={name: copy.deepcopy(inactive) for name in ['spatial', 'layers', 'particles', 'solar-zone']})
        value['modules']['spatial'].update(active=True, artifact=dict(source=dict(reference_id='sol:naif:399'),
                            configuration=service['recipe_before_execution']['spatial_configuration']))
        recipe = c.WINDOWS[2]
        audit.provenance(value, recipe, seed, phase, service)
        answer['checks'].append('Actual simple-mesh reference_id schema and accepted spatial configuration')
        broken = copy.deepcopy(value)
        broken['modules']['spatial']['artifact']['source'] = dict(body_reference_id='sol:naif:399')
        refuse('mixed-spatial-and-pair-schema', lambda: audit.provenance(broken, recipe, seed, phase, service))
        broken2 = copy.deepcopy(value)
        broken2['modules']['spatial']['artifact']['configuration']['vertical_amplification'] += 1
        refuse('unsealed-mesh-configuration', lambda: audit.provenance(broken2, recipe, seed, phase, service))
        atlas = dict(mode='atlas', renderer_confirmed=True, physics=None, atlas_anchor='Earth',
                     atlas_epoch_et_tdb_s=seed['checkpoint16']['atlas_initial']['source']['epoch']['et_tdb_s'],
                     modules={name: copy.deepcopy(inactive) for name in value['modules']})
        audit.provenance(atlas, c.WINDOWS[0], seed, None, service)
        wrong = copy.deepcopy(atlas); wrong['atlas_anchor'] = 'Moon'
        refuse('Atlas-wrong-native-anchor', lambda: audit.provenance(wrong, c.WINDOWS[0], seed, None, service))
        refuse('archived-edit-token-reuse', lambda: audit.phase_equal(c.physical(seed['checkpoint16']), seed['checkpoint16']))
        changed = copy.deepcopy(phase); changed['bodies'][0]['mass'] *= 2
        refuse('changed-archived-mass', lambda: audit.phase_equal(changed, seed['common_source_phase4']))
        start = dt.datetime(2026, 11, 13, tzinfo=dt.timezone.utc)
        stamp = lambda seconds: (start + dt.timedelta(seconds=seconds)).isoformat()
        ctrl = dict(schema=1, id='offline-stable', kind='stable', window=recipe['name'], recipe=recipe, expected_scenario=value)
        rows = [dict(index=i, boundary=False, phase_before=ctrl, phase_after=ctrl, scenario=value,
                     started_utc=stamp(i), finished_utc=stamp(i + .02), inventory_before=dict(owned=[dict(pid=1)]),
                     configured_counter_paths=['fixture']) for i in range(70)]
        run = dict(recipe=recipe, stable_control=ctrl, capture_start_utc=stamp(2.05), capture_end_utc=stamp(62.05), wall_interval_s=60)
        assert [row['index'] for row in audit.coverage(rows, run)] == list(range(66))
        boundary = dict(copy.deepcopy(rows[0]), boundary=True, index=-1)
        assert [row['index'] for row in audit.coverage([boundary, *rows], run)] == list(range(66))
        answer['checks'].append('First66 complete samples; all boundary/excess records retained outside the selection')
        refuse('missing-postroll', lambda: audit.coverage(rows[:65], run))
        refuse('short-preroll', lambda: audit.coverage(rows, run | dict(capture_start_utc=stamp(1.5), capture_end_utc=stamp(61.5))))
        drift = copy.deepcopy(rows); drift[65]['configured_counter_paths'].append('late-path')
        refuse('path-churn-inside-stable66', lambda: audit.coverage(drift, run))
        drift = copy.deepcopy(rows); drift[65]['inventory_before']['owned'][0]['pid'] = 2
        refuse('population-churn-inside-stable66', lambda: audit.coverage(drift, run))
        profile = json.loads((ROOT / names[-1]).read_text())
        original = profile['runs'][0]
        audit.trace(original['trace'])
        c.frames(original['capture'], original['wall_interval_s'], steady=True)
        answer['checks'].append('Preserved real native frame/CPU trace accepted as an offline fixture')
        broken = copy.deepcopy(original['trace']); broken['truncated'] = True
        refuse('truncated-stage-trace', lambda: audit.trace(broken))
        broken = copy.deepcopy(original['trace']); next(iter(broken['stats'].values()))['count'] = True
        refuse('boolean-stage-count', lambda: audit.trace(broken))
        capture = dict(width=1920, height=1080, invalid_samples=0, capacity_reached=False, samples_s=[.01, 1.25, .01])
        accepted = c.frames(capture, 1.27, steady=False)
        assert accepted['over_100ms'] == 1 and accepted['frames'] == 3 and accepted['maximum_ms'] == 1250
        answer['checks'].append('All transition frames retained, including a1.25second stall')
        assert all(sha(ROOT / name) == seal for name, seal in sources.items())
        answer.update(accepted=True, completed=True)
    except Exception:
        answer['failure'] = traceback.format_exc()
    out.write_text(json.dumps(answer, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({key: value for key, value in answer.items() if key != 'source_sha256'}, ensure_ascii=False))
    return 0 if answer['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
