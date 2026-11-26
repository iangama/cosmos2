"""Offline refusals for the new residency protocol using preserved native inputs; no GPU measurement."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import traceback
import zipfile

import expanded_residency_contract as contract

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    assert args.label and len(args.label) <= 24 and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
    out = ROOT / f'evidence/is6-expanded-residency-offline-{args.label}.json'
    folder = ROOT / f'output/is6-expanded-residency-offline-{args.label}'
    assert not out.exists() and not folder.exists()
    profile_path = ROOT / 'evidence/is6-dynamics16-profile-20261112a.json'
    profile = json.loads(profile_path.read_text())
    assert profile['completed'] and profile['processes'] and set(profile['processes'].values()) == {0}
    gpu_path = ROOT / profile['runs'][0]['gpu_report']
    gpu = json.loads(gpu_path.read_text())
    assert gpu['valid'] and gpu['schema'] == 4
    native_path = ROOT / 'evidence/is6-expanded-journey-native-20261113a.json'
    native = json.loads(native_path.read_text())
    assert native['accepted'] and native['completed']
    files = [Path(__file__), Path(contract.__file__), ROOT / 'scripts/gpu_pdh_audit_dynamics16_base.py',
             ROOT / 'scripts/expanded_residency_processes.py', ROOT / 'scripts/collect_expanded_residency.py',
             ROOT / 'IS-6-PERCURSO-AMPLIADO16-RESIDENCIA-CONTRATO.md',
             ROOT / 'IS-6-PERCURSO-AMPLIADO16-RESIDENCIA-IDENTIDADE.md', profile_path, gpu_path, native_path]
    sources = {p.relative_to(ROOT).as_posix(): sha(p) for p in files}
    folder.mkdir()
    with zipfile.ZipFile(folder / 'executed-sources-and-fixtures.zip', 'x', zipfile.ZIP_DEFLATED) as archive:
        for name in sources:
            archive.write(ROOT / name, name)
    result = dict(accepted=False, completed=False, source_sha256=sources, refusals=[], checks=[],
                  scope='Pure offline schema5 scenario, lifecycle and raw-byte refusal tests. Old native measurements are fixtures only; no new PDH/GPU, scene or performance acceptance.')
    def refuse(name, call):
        try:
            call()
        except (ValueError, TypeError, KeyError, AssertionError) as error:
            result['refusals'].append(dict(name=name, error=str(error)))
        else:
            raise AssertionError('Invalid fixture accepted: ' + name)
    try:
        row = copy.deepcopy(gpu['samples'][0])
        row.update(inventory_before=dict(owned=gpu['inventory_before']), inventory_after=dict(owned=gpu['inventory_after']),
                   configured_counter_paths=gpu['configured_counter_paths'], counter_paths_after=gpu['counter_paths_after'],
                   counter_metadata=gpu['counter_metadata'], owned_without_exposed_gpu_counter=gpu['owned_without_exposed_gpu_counter'],
                   ram=profile['runs'][0]['samples'][0]['ram'])
        baseline = contract.gpu_row(row, gpu['session'])
        assert baseline['GPU_bytes'] == row['product_dedicated_plus_shared_sum_bytes']
        edits = [
            ('raw-formatted-bytes', lambda r: r['raw_counter_samples'][0].update(raw_first_value=r['raw_counter_samples'][0]['raw_first_value'] + 1)),
            ('invalid-status', lambda r: r['raw_counter_samples'][0].update(raw_status=0x800007D5)),
            ('scaled-double-type', lambda r: r['raw_counter_samples'][0].update(raw_type=0x10410400)),
            ('boolean-gpu-bytes', lambda r: r['raw_counter_samples'][0].update(raw_first_value=True)),
            ('UTC-query-outside-call', lambda r: r.update(call_started_utc='2027-01-01T00:00:00+00:00')),
            ('duplicate-GPU-path', lambda r: r['configured_counter_paths'].append(r['configured_counter_paths'][0])),
            ('missing-GPU-path', lambda r: r['counter_paths_after'].pop()),
            ('wrong-metadata-object', lambda r: r['counter_metadata'][r['configured_counter_paths'][0]].update(object='CPU')),
            ('RAM-sum', lambda r: r['ram'].update(sum_working_set_bytes=r['ram']['sum_working_set_bytes'] + 1)),
            ('boolean-RAM', lambda r: r['ram']['processes'][0].update(working_set_bytes=True)),
            ('RAM-reused-PID', lambda r: r['ram']['processes'][0].update(created_filetime=r['ram']['processes'][0]['created_filetime'] + 1)),
            ('native-identity-mutation', lambda r: r['inventory_after']['owned'][0].update(executable='another-runtime.exe')),
            ('unexposed-GPU-zero', lambda r: r.update(owned_without_exposed_gpu_counter=[])),
        ]
        for name, edit in edits:
            bad = copy.deepcopy(row)
            edit(bad)
            refuse(name, lambda: contract.gpu_row(bad, gpu['session']))
        result['checks'].append('Preserved raw native GPU/RAM fixture accepted;13 corruptions refused')
        phase = copy.deepcopy(native['checkpoint16'])
        modules = {name: dict(active=False, busy=False, error=None, recovery_required=False, guard={}, artifact=None, scene=None)
                   for name in ['spatial', 'layers', 'particles', 'solar-zone']}
        normalized = contract.scenario(dict(mode='experiment', engine_connected=True, physics=phase), modules)
        recipe = contract.WINDOWS[1]
        assert contract.admit_scenario(normalized, recipe) == contract.digest(normalized)
        for name, edit in [
                ('orbital-time', lambda r: r['physics'].update(time=r['physics']['time'] + .01)),
                ('orbital-position', lambda r: r['physics']['bodies'][0]['position'].__setitem__(0, 100.)),
                ('old-token', lambda r: r['physics'].update(edit_token='0' * 32)),
                ('sixteen-EM-coupling', lambda r: r['physics']['dynamics16'].update(electromagnetic_coupling=True)),
                ('sixteen-boolean-coupling', lambda r: r['physics']['dynamics16'].update(electromagnetic_coupling=0)),
                ('scene-dispute', lambda r: r['modules']['layers'].update(active=True)),
                ('unconfirmed-renderer', lambda r: r.update(renderer_confirmed=False))]:
            bad = copy.deepcopy(normalized)
            edit(bad)
            refuse(name, lambda: contract.admit_scenario(bad, recipe, normalized))
        navigation = dict(et=1., navigation=dict(Anchor='Earth'), camera=dict(position_render_m=[0., 0., 0.]))
        atlas = contract.scenario(dict(mode='atlas', engine_connected=False, physics=None), modules, navigation)
        contract.admit_scenario(atlas, contract.WINDOWS[0])
        bad = copy.deepcopy(atlas)
        bad['physics'] = normalized['physics']
        refuse('orbital-phase-disguised-as-Atlas', lambda: contract.admit_scenario(bad, contract.WINDOWS[0]))
        result['checks'].append('True Atlas and frozen16 fixtures accepted;8 physical/domain mutations refused')
        observations = [copy.deepcopy(row) for _ in range(4)]
        identities = row['inventory_after']['owned']
        records = [dict(identity=identity, first_sample=0, last_sample=3, exit=None) for identity in identities]
        parent = next(identity for identity in identities if identity['pid'] == gpu['session']['server'])
        child = copy.deepcopy(parent)
        child.update(pid=max(identity['pid'] for identity in identities) + 1000, parent=parent['pid'],
                     created_filetime=parent['created_filetime'] + 10000, started_unix=parent['started_unix'] + .001,
                     scope_root=False, parent_created_filetime=parent['created_filetime'])
        for observation in observations[1:3]:
            observation['inventory_after']['owned'].append(child)
        records.append(dict(identity=child, first_sample=1, last_sample=2,
                            exit=dict(code=0, exited_filetime=child['created_filetime'] + 10000, observed_sample=3)))
        assert contract.ledger(records, observations, gpu['session'])['observed_exits'] == 1
        for name, edit in [
                ('abnormal-child-exit', lambda r: r[-1]['exit'].update(code=1)),
                ('missing-exit-proof', lambda r: r[-1].update(exit=None)),
                ('exit-before-creation', lambda r: r[-1]['exit'].update(exited_filetime=parent['created_filetime'])),
                ('late-exit-witness', lambda r: r[-1]['exit'].update(observed_sample=4)),
                ('reused-process-record', lambda r: r.append(copy.deepcopy(r[-1])))]:
            bad = copy.deepcopy(records)
            edit(bad)
            refuse(name, lambda: contract.ledger(bad, observations, gpu['session']))
        result['checks'].append('Worker birth/exit fixture accepted;5 lifecycle corruptions refused')
        capture = copy.deepcopy(profile['runs'][0]['capture'])
        contract.frames(capture, profile['runs'][0]['wall_interval_s'], steady=True)
        bad = copy.deepcopy(capture)
        if isinstance(bad['samples_s'], dict):
            bad['samples_s']['2'] = .11
        else:
            bad['samples_s'][1] = .11
        refuse('stable-frame-stall', lambda: contract.frames(bad, 60., steady=True))
        bad = copy.deepcopy(capture)
        bad['capacity_reached'] = True
        refuse('truncated-frame-buffer', lambda: contract.frames(bad, 60., steady=True))
        transition = dict(width=1920, height=1080, invalid_samples=0, capacity_reached=False, samples_s=[.013, 1.25, .014])
        metrics = contract.frames(transition, 1.277, steady=False)
        assert metrics['frames'] == 3 and metrics['excluded_initial_intervals'] == 0 and metrics['over_100ms'] == 1 and metrics['maximum_ms'] == 1250
        result['checks'].append('Stable limits enforced; long transition stalls retained explicitly')
        assert all(sha(ROOT / name) == seal for name, seal in sources.items())
        result.update(accepted=True, completed=True)
    except Exception:
        result['failure'] = traceback.format_exc()
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps(dict(accepted=result['accepted'], checks=result['checks'], refusals=len(result['refusals']), failure=result.get('failure'))), flush=True)
    return 0 if result['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
