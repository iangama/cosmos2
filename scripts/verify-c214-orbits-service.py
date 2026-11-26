"""Native service cohort: independent clock quadrature, controls, cancellation identities and private persistence."""
import argparse
import copy
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys
import threading
import time
import traceback
import zipfile

import numpy as np
from scipy.integrate import quad

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / 'output/c214-orbits-staging'
sys.path.insert(0, str(STAGE / 'app'))
import forces
from timelike_service import Laboratory
import timelike_force_adapter as adapter
import timelike_orbits as core

sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def wait(lab, seconds=20):
    end = time.monotonic()+seconds
    while True:
        state = lab.status()
        if not state['busy']:
            return state
        assert time.monotonic() < end
        time.sleep(.005)


def submit(lab, configuration):
    state = lab.status()
    return lab.command(dict(command='compute', edit_token=state['edit_token'], revision=state['revision'], configuration=configuration))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    assert args.label and len(args.label) <= 20 and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
    folder = ROOT / f'output/c214-orbits-service-{args.label}'
    out = ROOT / f'evidence/c214-orbits-service-{args.label}.json'
    assert not folder.exists() and not out.exists()
    cpu_path = ROOT / 'evidence/c214-orbits-numerics-20261114a.json'
    cpu = json.loads(cpu_path.read_text())
    assert cpu['accepted'] and cpu['completed'] and len(cpu['cases']) == 20
    assert sha(STAGE/'app/timelike_orbits.py') == cpu['source_sha256']['output/c214-orbits-staging/timelike_orbits.py']
    names = ['scripts/verify-c214-orbits-service.py','C2-14-ORBITAS-SERVICO-CONTRATO-20261114.md',cpu_path.relative_to(ROOT).as_posix()]
    sources = {name:sha(ROOT/name) for name in names}
    for base in [STAGE/'app',STAGE/'data/science']:
        sources.update({p.relative_to(ROOT).as_posix():sha(p) for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    protected = {name:sha(ROOT/name) for name in ['output/session.json','user/sessions/latest.json',
                  'Iniciar-Cosmos2.cmd','Abrir-Planetas-e-Luas.cmd','Abrir-Dinamica16.cmd'] if (ROOT/name).is_file()}
    request = dict(scenario='timelike-orbits', parameters=dict(radial_cycles=1, semi_latus_rectum_rs=10000.,eccentricity=.2))
    folder.mkdir()
    (folder/'recipe-before-execution.json').write_text(json.dumps(dict(configuration=request, source_sha256=sources, protected_sha256=protected),indent=2)+'\n',encoding='utf8')
    with zipfile.ZipFile(folder/'executed-sources.zip','x',zipfile.ZIP_DEFLATED) as archive:
        for name in sources:archive.write(ROOT/name,name)
    answer = dict(accepted=False, completed=False, source_sha256=sources, protected_sha256=protected, groups=[], refusals=[],
                  scope='Native CPU/service controls and persistence only, no HTTP, native UI or residency acceptance.')
    labs = []

    def refuse(name, function):
        try:function()
        except (ValueError, RuntimeError, KeyError, TypeError) as error:
            answer['refusals'].append(dict(name=name,error=str(error)))
        else:raise AssertionError('Invalid service request accepted: '+name)

    try:
        original = forces.evaluate(request)
        reference = copy.deepcopy(original['result']['reference'])
        comparison = copy.deepcopy(original['result']['reference_positions'])
        native_clock_errors = []
        for orbit, clock in itertools.product([False,True],repeat=2):
            cfg = copy.deepcopy(request)
            cfg['controls'] = dict(gravity=dict(acting=True,visible=True,effects=dict(orbital_acceleration=orbit,proper_clock_rate=clock)))
            response = forces.evaluate(cfg)
            value = response['result']; actual = value['timelike']
            assert value['reference'] == reference and value['reference_positions'] == comparison
            assert actual['orbit_effect_applied'] is orbit and actual['clock_effect_applied'] is clock
            assert len(value['time_s']) == len(actual['readings']) == len(value['positions']) == 1025
            assert actual['readings'][0]['applied_clock_time_s'] == 0
            if not orbit:
                points = np.asarray(value['positions']); tt = np.asarray(value['time_s'])
                speed = np.asarray(original['result']['positions'])[0,1] if False else actual['readings'][0]['velocity_coordinate_m_s'][1]
                assert np.max(np.abs(points[:,0]-points[0,0])) <= 1e-14 and np.all(points[:,2] == 0)
                assert np.max(np.abs(points[:,1]*value['position_unit_m']-speed*tt)) <= 2e-10*value['position_unit_m']
                units = original['result']['timelike']['configuration']
                kappa = 1/units['semi_latus_rectum_rs']
                r0 = points[0,0]
                time_unit = math.sqrt(value['position_unit_m']**3/units['mu_m3_s2'])
                tangent = speed*time_unit/value['position_unit_m']
                end = tt[-1]/time_unit

                def exact_lag_rate(t):
                    # Direct line-element evaluation, independent of the adapter's polar velocity decomposition.
                    r = math.hypot(r0,tangent*t)
                    A = 1-kappa/r
                    dr = tangent*tangent*t/r
                    dphi = r0*tangent/(r*r)
                    decrement = (1-A)+kappa/2*(dr*dr/A+r*r*dphi*dphi)
                    return decrement/(1+math.sqrt(1-decrement))

                expected,_ = quad(exact_lag_rate,0,end,epsabs=2e-13,epsrel=2e-12)
                physical = end-actual['readings'][-1]['metric_worldline_proper_time_s']/time_unit
                # Compare the stored integrated delay too: the close-clock subtraction is only a subsidiary check.
                integrated = actual['intervention_clock_nodes']['lag'][-1]
                err = abs(integrated-expected)
                assert err <= 2e-11*max(1,end)
                assert abs(physical-expected) <= 2e-11*max(1,end)
                native_clock_errors.append(err)
            if not clock:
                assert all(row['applied_lag_s'] == 0 and row['applied_clock_rate'] == 1 for row in actual['readings'])
            hidden = copy.deepcopy(cfg);hidden['controls']['gravity']['visible'] = False
            invisible = forces.evaluate(hidden)
            assert invisible['result'] == response['result'] and invisible['physics_sha256'] == response['physics_sha256']
            assert invisible['configuration_sha256'] != response['configuration_sha256']
            (folder/f'controls-{int(orbit)}-{int(clock)}.json').write_text(json.dumps(response,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
        disabled = forces.evaluate(dict(request,controls=dict(gravity=dict(acting=False))))['result']
        assert not disabled['timelike']['orbit_effect_applied'] and not disabled['timelike']['clock_effect_applied']
        answer['groups'].append(dict(name='four-operator-combinations-and-visibility',maximum_inertial_clock_error_scaled=max(native_clock_errors)))
        original['result']['reference']['constants']['energy_per_c2'] = -1
        assert forces.evaluate(request)['result']['reference'] == reference
        answer['groups'].append(dict(name='published-result-cannot-mutate-cached-physics'))
        # New private persistence uses the same generation and signals an archived generation change.
        saved = forces.save_configuration(request,directory=folder/'saved')
        restored = forces.load_configuration_record(directory=folder/'saved')
        assert restored['restoration']['status'] == 'same_generation' and restored['configuration'] == saved['configuration']
        assert forces.evaluate(restored['configuration'])['result'] == forces.evaluate(request)['result']
        answer['groups'].append(dict(name='private-save-and-recalculate-same-generation'))
        lab = Laboratory();labs.append(lab)
        initial = lab.status()
        sent = submit(lab,request)
        ready = wait(lab)
        assert ready['phase'] == 'complete' and ready['published_job_id'] == sent['job_id'] and ready['result']['result'] == forces.evaluate(request)['result']
        refuse('obsolete-compute-token',lambda:lab.command(dict(command='compute',revision=initial['revision'],edit_token=initial['edit_token'],configuration=request)))
        refuse('cancel-completed-job',lambda:lab.command(dict(command='cancel',revision=ready['revision'],edit_token=ready['edit_token'],job_id=ready['job_id'])))
        before = lab.status()
        refuse('fractional-cycle',lambda:submit(lab,dict(request,parameters=dict(radial_cycles=1.5))))
        assert lab.status() == before
        refuse('wrong-scenario',lambda:submit(lab,dict(scenario='gravity')))
        refuse('unknown-command',lambda:lab.command(dict(command='replace')))
        refuse('unknown-control',lambda:forces.evaluate(dict(request,controls=dict(gravity=dict(other=True)))))
        refuse('unknown-effect',lambda:forces.evaluate(dict(request,controls=dict(gravity=dict(effects=dict(no_such_effect=True))))))
        refuse('invalid-domain',lambda:forces.evaluate(dict(request,parameters=dict(semi_latus_rectum_rs=999))))
        # Controlled wait is a protocol fixture only; all scientific comparisons above used real computations.
        entered = threading.Event()
        modes = ['ready']

        def controlled(cfg,cancelled):
            if modes[-1] == 'ready':return dict(marker='last-complete')
            entered.set()
            if modes[-1] == 'fail':raise RuntimeError('controlled refusal')
            while not cancelled():time.sleep(.002)
            raise core.Cancelled('controlled cancellation')

        protocol = Laboratory(evaluate=controlled);labs.append(protocol)
        submit(protocol,request);last = wait(protocol)
        modes.append('wait');busy = submit(protocol,request);assert entered.wait(2)
        refuse('submit-while-busy',lambda:submit(protocol,request))
        refuse('foreign-job-cancel',lambda:protocol.command(dict(command='cancel',edit_token=busy['edit_token'],revision=busy['revision'],job_id='foreign')))
        protocol.command(dict(command='cancel',edit_token=busy['edit_token'],revision=busy['revision'],job_id=busy['job_id']))
        stopped = wait(protocol)
        assert stopped['phase'] == 'cancelled' and stopped['result'] == last['result'] and stopped['published_job_id'] == last['published_job_id']
        modes.append('fail');submit(protocol,request);failed = wait(protocol)
        assert failed['phase'] == 'failed' and failed['result'] == last['result']
        answer['groups'].append(dict(name='cancellation-failure-busy-and-stale-identities-preserve-last-complete'))
        # Legacy science entry points stay usable in the self-contained data namespace.
        assert forces.evaluate(dict(scenario='gravity'))['ok'] and forces.evaluate(dict(scenario='relativity'))['ok']
        answer['groups'].append(dict(name='legacy-gravity-and-null-ray-smoke-in-isolated-data-namespace'))
        assert all(sha(ROOT/name)==seal for name,seal in (sources|protected).items())
        answer.update(accepted=True,completed=True)
    except Exception:
        answer['failure'] = traceback.format_exc()
    finally:
        for lab in labs:lab.close()
    out.write_text(json.dumps(answer,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({key:value for key,value in answer.items() if key not in ['source_sha256','protected_sha256']},ensure_ascii=False),flush=True)
    return 0 if answer['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
