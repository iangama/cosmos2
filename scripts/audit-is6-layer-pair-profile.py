"""Independent K2 audit of scientific inputs, native readbacks and raw resources."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import struct
import sys
import traceback
import zipfile

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'output/is6-spatial-product0.18.5/app'
sys.path[:0] = [str(ROOT / 'output/is6-layer-coordination-staging'), str(APP)]
import is6_layer_contract as contract
import body_field_scene
from is6_pair_profile_support import LIMITS, WINDOWS, COMBINATIONS, frame_statistics, percentile, audit_gpu
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def same_context(a, b):
    assert a['flags'] == b['flags']
    assert a['camera'].keys() == b['camera'].keys()
    for key, value in a['camera'].items():
        if key == 'Up':
            assert all(abs(x-y) <= 1e-12 for x, y in zip(value, b['camera'][key], strict=True))
        else:
            assert value == b['camera'][key], key


def readback(value, visible, row, data):
    spatial, magnetic = value['spatial'], value['magnetic']
    assert spatial['exists'] and spatial['draw'] is visible['spatial']
    assert spatial['center'] == data['artifact']['binding']['center_render_m']
    assert spatial['scale'] == row['spatial_scene']['normalization_unit_m']
    assert Path(spatial['file']).name == 'wire.speck'
    assert sha(Path(spatial['file'])) == row['spatial_scene']['wire_sha256']
    assert sha(Path(spatial['file']).with_name('wire.names')) == row['spatial_scene']['names_sha256']
    assert row['spatial_scene']['artifact_sha256'] == contract.artifact.digest(data['artifact'])
    geometry = row['magnetic_scene']['geometry']
    render = row['magnetic_scene']['render']
    assert geometry == body_field_scene.build(data['reading']) | {'representation': 'vector'}
    expected = body_field_scene.product(geometry['body_to_render'], geometry['point_model_m'])
    assert magnetic['expected_relative_m'] == expected
    assert max(abs(x-y) for x, y in zip(magnetic['center_local'], geometry['center_render_m'], strict=True)) <= .001
    assert max(abs(x-y) for x, y in zip(magnetic['point_local'], expected, strict=True)) <= .001
    limits = [math.ulp(x)+math.ulp(y)+.001 for x, y in zip(magnetic['point_world'], magnetic['center_world'], strict=True)]
    assert limits == magnetic['world_difference_limits_m']
    relative = [x-y for x, y in zip(magnetic['point_world'], magnetic['center_world'], strict=True)]
    assert relative == magnetic['point_relative_m']
    assert all(abs(x-y) <= limit for x, y, limit in zip(relative, expected, limits, strict=True))
    meshes = render['meshes']
    assert len(meshes) == len(magnetic['draw']) == len(magnetic['transforms']) == 3
    bound = max(m['conservative_display_position_error_bound_m'] for m in meshes)
    assert bound == magnetic['display_position_error_bound_m']
    graphic_limits = [math.ulp(x)+math.ulp(y)+bound for x, y in zip(magnetic['display_point_world'], magnetic['center_world'], strict=True)]
    graphic_relative = [x-y for x, y in zip(magnetic['display_point_world'], magnetic['center_world'], strict=True)]
    assert graphic_limits == magnetic['display_world_difference_limits_m']
    assert graphic_relative == magnetic['display_point_relative_m']
    assert all(abs(x-y) <= limit for x, y, limit in zip(graphic_relative, expected, graphic_limits, strict=True))
    for m, (name, flag) in zip(meshes, magnetic['draw'].items(), strict=True):
        assert flag is visible['magnetic']
        # Native dictionaries may sort keys, so bind transforms by the stored node set.
        assert name in magnetic['transforms']
    for m in meshes:
        n = next(n for n, t in magnetic['transforms'].items() if t['file'] == m['file'])
        assert magnetic['draw'][n] is visible['magnetic']
        angles = [struct.unpack('f', struct.pack('f', a))[0] for a in m['rotation_euler_rad']]
        assert magnetic['transforms'][n] == dict(scale=m['scale_m'], file=m['file'], rotation=angles)
        assert sha(Path(m['file'])) == m['file_sha256'] and sha(Path(m['names_file'])) == m['names_sha256']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('Invalid label')
    source = ROOT / ('evidence/is6-pair-profile-' + args.label + '.json')
    out = ROOT / ('evidence/is6-pair-profile-audit-' + args.label + '.json')
    if out.exists():
        raise FileExistsError('Preserve audit evidence')
    r = json.loads(source.read_text())
    result = dict(accepted=False, profile=source.relative_to(ROOT).as_posix(), profile_sha256=sha(source),
                  auditor_sha256=sha(Path(__file__)), runs=[])
    try:
        assert r['completed'] and not r.get('failure') and not r.get('cleanup_failure') and not r['page_errors']
        assert r['warmup_s'] == 30 and r['window_s'] == 60 and r['limits_before_execution'] == LIMITS
        assert [(row['body'], row['kind']) for row in r['runs']] == WINDOWS
        assert len(r['inputs_before_execution']) == len(r['scene_files_before_execution']) == 4
        assert r['session']['serverScript'].replace('\\', '/').endswith('/output/is6-spatial-product0.18.5/app/server.py')
        archive = ROOT / ('output/is6-pair-profile-' + args.label + '/executed-sources-and-inputs.zip')
        assert sha(archive) == r['archive_sha256']
        expected = dict(r['source_sha256'])
        for item in r['inputs_before_execution']:
            expected[item['path']] = item['sha256']
        for item in r['scene_files_before_execution']:
            expected.update(item['sha256'])
        with zipfile.ZipFile(archive) as z:
            assert len(z.namelist()) == len(set(z.namelist())) and set(z.namelist()) == set(expected)
            assert all(hashlib.sha256(z.read(p)).hexdigest() == seal for p, seal in expected.items())
        assert all(sha(ROOT / p) == seal for p, seal in expected.items())
        assert sha(ROOT / '.runtime-is4-stream/bin/OpenSpace.exe') == r['engine_sha256']
        ram_peak = gpu_peak = commands = 0
        for index, (row, item) in enumerate(zip(r['runs'], r['inputs_before_execution'], strict=True), 1):
            assert row['run'] == item['run'] == index and row['input'] == item
            data = json.loads((ROOT / item['path']).read_text())
            assert (data['body'], data['kind']) == WINDOWS[index-1]
            run = contract.artifact.Run.restore(data['artifact'])
            phase = run.payload['phase']
            assert {k: phase[k] for k in r['source_phase']} == r['source_phase']
            assert data['artifact']['binding']['body_reference_id'] == 'sol:naif:' + row['body']
            assert data['artifact']['configuration'] == {**contract.artifact.DEFAULT_CONFIGURATION, 'outer_radius_boundary_units': 3.}
            assert contract.magnetic(phase, data['reading']) == data['reading']
            plan = contract.compose(phase, run.payload, data['reading'], dict(spatial=True, magnetic=True))
            assert plan == data['plan'] == row['plan']
            recipe = [dict(tick=tick, offset_s=tick*.5, visible=COMBINATIONS[tick % 4]) for tick in range(120)] if row['kind'] == 'visibility' else []
            assert data['recipe'] == recipe and len(row['commands']) == len(recipe) and not row['producer_errors']
            metrics = frame_statistics(row['capture'], row['wall_interval_s'])
            readback(row['initial'], dict(spatial=True, magnetic=True), row, data)
            for command, scheduled in zip(row['commands'], recipe, strict=True):
                assert command['tick'] == scheduled['tick'] and command['visible'] == scheduled['visible']
                assert abs(command['started_offset_s']-scheduled['offset_s']) < .5
                readback(command['readback'], scheduled['visible'], row, data)
            if recipe:
                times = [c['elapsed_s'] for c in row['commands']]
                ratio = sum(c['finished_offset_s'] <= 60 for c in row['commands'])/120
                assert ratio >= LIMITS['command_rate_min']
                assert percentile(times, .95) <= LIMITS['command_p95_s'] and max(times) <= LIMITS['command_max_s']
                metrics.update(command_completion_ratio=ratio, command_p95_s=percentile(times, .95), command_max_s=max(times))
                commands += len(recipe)
            readback(row['final'], dict(spatial=True, magnetic=True), row, data)
            assert len(row['samples']) == 4
            for checkpoint, sample in enumerate(row['samples']):
                assert abs(sample['offset_s']-checkpoint*20) < .5 and sample['paused']
                assert sample['source_phase'] == r['source_phase']
                same_context(row['context'], sample['context'])
                flags = sample['readback']
                actual = dict(spatial=flags['spatial']['draw'], magnetic=next(iter(flags['magnetic']['draw'].values())))
                assert actual in COMBINATIONS
                if row['kind'] == 'static':
                    assert actual == dict(spatial=True, magnetic=True)
                readback(flags, actual, row, data)
                ram = sample['ram']
                assert ram['sum_working_set_bytes'] == sum(p['working_set_bytes'] for p in ram['processes'])
                assert ram['sum_working_set_bytes'] <= LIMITS['RAM_bytes']
                ram_peak = max(ram_peak, ram['sum_working_set_bytes'])
            assert not any(row['nodes_after_cleanup'].values())
            same_context(r['base_context'], row['context_after_cleanup'])
            gpu_path = ROOT / row['gpu_report']
            assert sha(gpu_path) == row['gpu_sha256']
            gpu = json.loads(gpu_path.read_text(encoding='utf-8-sig'))
            peak = audit_gpu(gpu, r['session'], r['engine_sha256'], row)
            gpu_peak = max(gpu_peak, peak)
            result['runs'].append(dict(run=index, body=row['body'], kind=row['kind'], GPU_peak_GiB=peak/2**30, **metrics))
        assert commands == 240 and sha(ROOT / 'user/sessions/latest.json') == r['owner_sha256']
        result.update(accepted=True, commands=commands, RAM_peak_GiB=ram_peak/2**30, GPU_peak_GiB=gpu_peak/2**30,
                      scope=r['scope'])
    except Exception:
        result['failure'] = traceback.format_exc()
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return 0 if result['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
