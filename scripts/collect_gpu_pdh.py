"""Frozen owned-process GPU byte gauges through Windows PDH, schema4."""
from pathlib import Path
import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import time
import traceback
import urllib.request
import uuid
import psutil
import windows_gpu_pdh as pdh
import gpu_pdh_audit as audit

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def get(path):
    with OPENER.open('http://127.0.0.1:4700'+path,timeout=3) as response:
        return json.load(response)


def scenario(expected_mode,expected_worker):
    state = get('/api/state')
    confirmed = state.get('engine_connected') is True
    if state['mode'] == 'atlas' and not confirmed:
        navigation = get('/api/navigation/state')
        confirmed = bool(navigation.get('navigation',{}).get('Anchor') and len(navigation.get('camera',{}).get('position_render_m',[])) == 3)
    if state['mode'] != expected_mode or not confirmed:
        raise ValueError('Renderer/scenario not confirmed')
    physics = state.get('physics') or {}
    if expected_worker == 'paused' and physics.get('paused') is not True:
        raise ValueError('Paused physics worker required')
    return dict(mode=state['mode'],renderer_confirmed=confirmed,paused=physics.get('paused'),
        fixture_count=physics.get('fixture_count'),revision=physics.get('revision'),
        requested_rate=physics.get('requested_rate'),physical_time=physics.get('time'))


def inventory(session):
    # Enumerate parent identities to discover descendants. Only owned entries
    # are exposed in the receipt; no names of unrelated processes are saved.
    entries = {}
    for process in psutil.process_iter(['pid','ppid']):
        try:
            entries[process.pid] = process.info['ppid']
        except (psutil.NoSuchProcess,psutil.AccessDenied):
            continue
    owned = {session['app'],session['server']}
    while True:
        next_owned = owned | {pid for pid,parent in entries.items() if parent in owned}
        if next_owned == owned:
            break
        owned = next_owned
    result = []
    for pid in sorted(owned):
        process = psutil.Process(pid)
        result.append(dict(pid=pid,parent=process.ppid(),name=process.name(),
                           started_unix=process.create_time(),executable=process.exe()))
    return result


def atomic_json(path,value):
    if path.exists():
        raise FileExistsError('Preserve GPU receipt')
    temporary = path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    raw = (json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf8')
    try:
        with temporary.open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if path.exists():
            raise FileExistsError('Preserve GPU receipt')
        os.replace(temporary,path)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label',required=True)
    parser.add_argument('--samples',type=int,default=3)
    parser.add_argument('--expected-mode',choices=['atlas','experiment'],required=True)
    parser.add_argument('--expected-worker',choices=['any','paused'],default='any')
    parser.add_argument('--signal-ready',action='store_true')
    args = parser.parse_args()
    if not args.label or len(args.label)>40 or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('Invalid label')
    if not 1 <= args.samples <= 120:
        parser.error('Invalid sample budget')
    out = ROOT / ('evidence/gpu-pdh-'+args.label+'.json')
    ready = ROOT / ('output/gpu-memory-ready-'+args.label+'.json')
    if out.exists() or args.signal_ready and ready.exists():
        raise FileExistsError('Preserve GPU evidence')
    sources = {path.relative_to(ROOT).as_posix():sha(path) for path in [Path(__file__),Path(pdh.__file__),Path(audit.__file__),pdh.CONTRACT]}
    report = dict(schema=4,label=args.label,valid=False,failure=None,generation=pdh.generation(),
        collector_sha256=sha(Path(__file__)),source_sha256=sources,requested_samples=args.samples,
        expected_mode=args.expected_mode,expected_worker=args.expected_worker,samples=[],
        method='Windows PDH ctypes; selected owned byte gauges',
        runtime=dict(python=sys.version,psutil=psutil.__version__,pointer_bits=8*pdh.c.sizeof(pdh.HANDLE)),
        scope='Windows WDDM memory sum per owned process. Shared allocations may be counted more than once. No zero assignment for unexposed processes; any invalid selected value or identity/path change refuses the whole collection.')
    try:
        session_path = ROOT / 'output/session.json'
        session = json.loads(session_path.read_text(encoding='utf-8-sig'))
        engine = psutil.Process(session['app'])
        executable = Path(engine.exe()).resolve()
        if not executable.is_relative_to(ROOT) or executable.name.lower() != 'openspace.exe':
            raise ValueError('Owned project engine required')
        report.update(session=session,engine_sha256=sha(executable),engine_started_unix=engine.create_time(),
                      scenario_before=scenario(args.expected_mode,args.expected_worker),
                      inventory_before=inventory(session))
        owned = {row['pid'] for row in report['inventory_before']}
        report['owned_processes'] = sorted(owned)
        with pdh.Query() as query:
            paths = query.discover(owned)
            if not any(row['pid'] == session['app'] and row['counter'] == 'dedicated usage' for row in paths.values()):
                raise ValueError('Engine dedicated GPU counter missing')
            query.select(paths)
            report['configured_counter_paths'] = sorted(paths)
            report['counter_metadata'] = query.metadata
            exposed = {row['pid'] for row in paths.values() if row['pid'] is not None}
            report['owned_gpu_processes'] = sorted(exposed)
            report['owned_without_exposed_gpu_counter'] = sorted(owned-exposed)
            began = time.monotonic()
            for index in range(args.samples):
                remaining = began+index-time.monotonic()
                if remaining > 0:
                    time.sleep(remaining)
                row = query.sample()
                row.update(monotonic_offset_s=time.monotonic()-began,
                           scenario=scenario(args.expected_mode,args.expected_worker))
                report['samples'].append(row)
                row.update(audit.sample(row,report['configured_counter_paths'],owned))
                if row['scenario'] != report['scenario_before']:
                    raise ValueError('Scenario changed during GPU collection')
                if args.signal_ready and index == 0:
                    atomic_json(ready,dict(engine_pid=session['app'],label=args.label,
                        first_sample_utc=row['utc'],schema=4,collector_sha256=report['collector_sha256']))
            report['counter_paths_after'] = sorted(query.discover(owned))
        report.update(inventory_after=inventory(session),scenario_after=scenario(args.expected_mode,args.expected_worker))
        if json.loads(session_path.read_text(encoding='utf-8-sig')) != session:
            raise ValueError('Native session changed during GPU collection')
        if sha(executable) != report['engine_sha256'] or engine.create_time() != report['engine_started_unix']:
            raise ValueError('Engine identity/executable changed during GPU collection')
        if pdh.generation() != report['generation'] or any(sha(ROOT/name) != seal for name,seal in sources.items()):
            raise ValueError('GPU collector sources changed during execution')
        report['valid'] = True
        report['audit'] = audit.audit(report,expected_samples=args.samples)
    except Exception:
        report['valid'] = False
        report['failure'] = traceback.format_exc()
    atomic_json(out,report)
    print(json.dumps(dict(valid=report['valid'],samples=len(report['samples']),
                         audit=report.get('audit'),failure=report['failure'])),flush=True)
    return 0 if report['valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
