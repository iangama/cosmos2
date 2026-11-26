"""Coulomb mixture against author Fortran routines, high precision and identities."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import subprocess
import sys
import traceback
import zipfile
import mpmath as mp
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT/'output/is5-coulomb-mixture-staging'
RESEARCH = ROOT/'output/is5-coulomb-research-20261028'
sys.path.insert(0, str(STAGE))
import is5_coulomb_mixture as model
import is5_jet as ad

sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
KEYS = ['free_energy_J_m3', 'internal_energy_J_m3', 'pressure_Pa', 'heat_capacity_J_m3_K']
PARTS = ['ii', 'ie', 'ee', 'mix']


def scaled_error(actual, expected, floor=1e-280):
    return abs(actual-expected)/max(abs(expected), floor)


def fixture(t, rho, hydrogen, metal, seed):
    y = np.zeros(16)
    y[0], y[3] = hydrogen, (1-hydrogen-metal)/4
    y[seed] = metal/(14 if seed == 7 else 16)
    return dict(T=t, rho=rho, Y=y.tolist(), A=[1,2,3,4,12,13,13,14,15,15,7,7,8,16,17,17],
                Z=[1,1,2,2,6,7,6,7,8,7,4,3,5,8,9,8])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('Invalid immutable label')
    path = ROOT/f'evidence/is5-coulomb-mixture-{args.label}.json'
    archive = ROOT/f'output/is5-coulomb-mixture-{args.label}.zip'
    raw_fortran = ROOT/f'output/is5-coulomb-mixture-{args.label}-fortran.txt'
    raw_original = ROOT/f'output/is5-coulomb-mixture-{args.label}-Fortran-original.txt'
    if any(p.exists() for p in [path, archive, raw_fortran, raw_original]):
        raise FileExistsError('Preserve Coulomb mixture evidence')
    files = [*model.FILES, Path(__file__), RESEARCH/'reference-driver.f90', RESEARCH/'reference-coulomb',
             RESEARCH/'eos22-CTF-aligned.f', RESEARCH/'reference-coulomb-CTF-aligned',
             RESEARCH/'reference-CTF-alignment.json', ROOT/'scripts/build-is5-coulomb-reference.py',
             ROOT/'IS-5-COULOMB-MISTURA-REFERENCIA-B.md',
             ROOT/'output/is5-thermal-staging/is5_eos.py', ROOT/'output/is5-thermal-staging/is5_core.py']
    protected = {}
    for name in ['is5-coulomb-foundation-20261028b', 'is5-cno2-science-20261027a']:
        receipt = ROOT/f'evidence/{name}.json'
        obj = json.loads(receipt.read_text(encoding='utf-8'))
        if not obj['accepted']:
            raise ValueError('Prior scientific acceptance missing')
        files.append(receipt)
        for n, h in obj['source_sha256'].items():
            if sha(ROOT/n) != h:
                raise ValueError('Prior accepted source changed: '+n)
            protected[n] = h
    hashes = {p.relative_to(ROOT).as_posix():sha(p) for p in files}
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for n in hashes:
            z.write(ROOT/n, n)
    r = dict(accepted=False, completed=False, source_sha256=hashes, archive_sha256=sha(archive),
             generation=model.generation(), prior_sources_checked=len(protected), cases=[],
             structural_checks=[], refusals=[], limits_before_execution=dict(high_precision=2e-9,
                    authors_Fortran=5e-5, differences=2e-6, Maxwell=2e-6))
    try:
        points = [fixture(t, rho, h, z, seed) for t in [1.1e7, 1.5e7, 2.8e7]
                  for rho in [1.1e4, 1.5e5] for h, z, seed in [(.34, .01, 7), (.7, .02, 13)]]
        candidates = [model.evaluate(p['T'], p['rho'], p['Y'], p['A'], p['Z']) for p in points]
        lines = []
        for p, candidate in zip(points, candidates):
            d = candidate['diagnostics']
            lines.append(f"16 {d['rs']:.17g} {d['electron_Gamma']:.17g}")
            yi = sum(p['Y'])
            lines.extend(f'{v/yi:.17g} {z}' for v, z in zip(p['Y'], p['Z']))
        binary = '/mnt/c/Users/Ian/cosmos2/output/is5-coulomb-research-20261028/reference-coulomb-CTF-aligned'
        command = ['wsl.exe', '--distribution', 'Ubuntu-24.04', '--exec', binary] if sys.platform == 'win32' else [binary]
        run = subprocess.run(command, input='\n'.join(lines)+'\n', text=True, capture_output=True, timeout=60)
        raw_fortran.write_text(run.stdout, encoding='utf-8')
        r['Fortran_execution'] = dict(command=command, returncode=run.returncode, stderr=run.stderr,
                                     stdout_path=raw_fortran.relative_to(ROOT).as_posix(), stdout_sha256=sha(raw_fortran))
        if run.returncode:
            raise RuntimeError('Independent Fortran reference failed')
        values = [[float(v) for v in line.split()] for line in run.stdout.splitlines() if line.strip()]
        assert len(values) == len(points) and all(len(v) == 16 for v in values)
        original_command = [*command[:-1], binary.replace('-CTF-aligned', '')]
        original_run = subprocess.run(original_command, input='\n'.join(lines)+'\n', text=True, capture_output=True, timeout=60)
        raw_original.write_text(original_run.stdout, encoding='utf-8')
        r['Fortran_original_execution'] = dict(command=original_command, returncode=original_run.returncode,
                        stdout_path=raw_original.relative_to(ROOT).as_posix(), stdout_sha256=sha(raw_original),
                        stderr=original_run.stderr, comparison='Original rounded CTF, residuals reported without treating it as identical to the candidate fit')
        assert original_run.returncode == 0
        original_values = [[float(v) for v in line.split()] for line in original_run.stdout.splitlines() if line.strip()]
        assert len(original_values) == len(points) and all(len(v) == 16 for v in original_values)
        mp.mp.dps = 50
        for index, (p, actual, author) in enumerate(zip(points, candidates, values)):
            t, rho, y, z = p['T'], p['rho'], p['Y'], p['Z']
            nb = rho/model.MU
            scales = [nb*sum(y)*model.K*t]*3+[nb*sum(y)*model.K]
            fortran_errors = {}
            original_errors = {}
            for j, component in enumerate(PARTS):
                for k, key in enumerate(KEYS):
                    reference = author[j*4+k]*scales[k]
                    error = scaled_error(actual['components'][component][key], reference,
                                         1e-12*scales[k])
                    fortran_errors[component+':'+key] = error
                    original_reference = original_values[index][j*4+k]*scales[k]
                    original_errors[component+':'+key] = scaled_error(actual['components'][component][key], original_reference, 1e-12*scales[k])
            assert max(fortran_errors.values()) <= 5e-5, (index, fortran_errors)
            mt, mn = mp.mpf(str(t)), mp.mpf(str(nb))
            my = [mp.mpf(str(v)) for v in y]
            components = model.free_energy_components(mt, mn, my, z, mp)
            high_errors = {}
            for component in PARTS:
                f = components[component]
                dT = mp.diff(lambda q:model.free_energy_components(q, mn, my, z, mp)[component], mt)
                dTT = mp.diff(lambda q:model.free_energy_components(q, mn, my, z, mp)[component], mt, 2)
                dn = mp.diff(lambda q:model.free_energy_components(mt, q, my, z, mp)[component], mn)
                refs = [f, f-mt*dT, mn*dn-f, -mt*dTT]
                for key, ref, scale in zip(KEYS, refs, scales):
                    high_errors[component+':'+key] = scaled_error(actual['components'][component][key], float(ref), 1e-12*scale)
            assert max(high_errors.values()) <= 2e-9, (index, high_errors)
            # Composition Hessian tested independently at a N14 and an O16 fixture.
            gradient_errors = []
            if index in [6, 7]:
                for i in range(16):
                    def retained_u(value):
                        pop = list(my)
                        pop[i] = value
                        ff = lambda temp:sum(model.free_energy_components(temp, mn, pop, z, mp).values())
                        return ff(mt)-mt*mp.diff(ff, mt)
                    ref = mp.diff(retained_u, my[i])
                    gradient_errors.append(scaled_error(actual['components']['sum']['du_dnumber_per_baryon_J_m3'][i], float(ref)))
                assert max(gradient_errors) <= 2e-9, (index, gradient_errors)
            delta = 5e-5
            tp = model.evaluate(t*(1+delta), rho, y, p['A'], z)
            tm = model.evaluate(t*(1-delta), rho, y, p['A'], z)
            rp = model.evaluate(t, rho*(1+delta), y, p['A'], z)
            rm = model.evaluate(t, rho*(1-delta), y, p['A'], z)
            maxwell = {}
            cv_errors = {}
            for component in [*PARTS, 'sum', 'total']:
                get = lambda state:state['total'] if component == 'total' else state['components'][component]
                ac, ap, am, ar, al = map(get, [actual, tp, tm, rp, rm])
                dE = (ar['internal_energy_J_m3']/(rho*(1+delta))-al['internal_energy_J_m3']/(rho*(1-delta)))/(2*rho*delta)
                dP = (ap['pressure_Pa']-am['pressure_Pa'])/(2*t*delta)
                maxwell[component] = abs(ac['pressure_Pa']-rho*rho*dE-t*dP)/max(abs(ac['pressure_Pa']), 1e-12*scales[0])
                cv = (ap['internal_energy_J_m3']-am['internal_energy_J_m3'])/(2*t*delta)
                cv_errors[component] = scaled_error(cv, ac['heat_capacity_J_m3_K'], 1e-12*scales[3])
            assert max(maxwell.values()) <= 2e-6, (index, maxwell)
            assert max(cv_errors.values()) <= 2e-6, (index, cv_errors)
            r['cases'].append(dict(fixture=p, EOS=actual, Fortran_relative_errors=fortran_errors,
                                   Fortran_original_rounded_constant_relative_errors=original_errors,
                                   high_precision_relative_errors=high_errors,
                                   composition_gradient_relative_errors=gradient_errors,
                                   Maxwell_relative_errors=maxwell, Cv_difference_relative_errors=cv_errors))
            print(json.dumps(dict(case=index+1, passed=True,
                                  Fortran=max(fortran_errors.values()), high_precision=max(high_errors.values()))), flush=True)
        good = points[6]
        # Permutation and identical-species splitting cannot change the thermodynamics.
        order = list(reversed(range(16)))
        perm = model.evaluate(good['T'], good['rho'], *[[good[key][i] for i in order] for key in ['Y', 'A', 'Z']])
        base = candidates[6]
        split = model.evaluate(good['T'], good['rho'], [good['Y'][0]/2, *good['Y'][1:], good['Y'][0]/2],
                               [*good['A'], good['A'][0]], [*good['Z'], good['Z'][0]])
        for other in [perm, split]:
            for name in [*PARTS, 'sum']:
                for key in KEYS:
                    assert scaled_error(other['components'][name][key], base['components'][name][key]) < 2e-10
        r['structural_checks'] += ['species_permutation', 'identical_species_split']
        pure = model.evaluate(15e6, 1.5e5, [.25], [4], [2])
        assert all(pure['components']['mix'][key] == 0 for key in KEYS)
        r['structural_checks'].append('identical_charge_mixing_exact_zero')
        # Integral of the separately published u_ii/Gamma, not the implementation of f_ii.
        for g in [1e-9, 1e-5, .001, .1, 1., 10., 20.]:
            a1, a2 = mp.mpf('-.907347'), mp.mpf('.62849')
            a3 = -mp.sqrt(3)/2-a1/mp.sqrt(a2)
            u = lambda q:q**mp.mpf('1.5')*(a1/mp.sqrt(a2+q)+a3/(1+q))+mp.mpf('.0045')*q*q/(170+q)-mp.mpf('8.4e-5')*q*q/(mp.mpf('.0037')+q*q)
            reference = mp.quad(lambda q:u(q)/q, [0, mp.mpf(str(g))])
            assert scaled_error(model.ocp_free(g), float(reference)) < 2e-9
        r['structural_checks'].append('OCP_free_energy_integral_of_published_U')
        # Mathematical weak-coupling limit, independent of the public zone guard.
        z, y = [1, 2, 8], [.4, .15, .0025]
        previous_error = None
        dh_errors = []
        for t in [1e11, 1e12, 1e13]:
            nb = 1e30
            raw = model.free_energy_components(t, nb, y, z)
            kap = math.sqrt(4*math.pi*model.COULOMB*nb*sum(v*(q*q+q) for v, q in zip(y,z))/(model.K*t))
            dh = -model.K*t*kap**3/(12*math.pi)
            err = scaled_error(sum(raw.values()), dh)
            assert previous_error is None or err < previous_error
            previous_error = err
            dh_errors.append(err)
        assert dh_errors[-1] < .01, dh_errors
        r['weak_DH_mathematical_limit_errors'] = dh_errors
        r['structural_checks'].append('full_polarizable_DH_limit_with_mixing')
        valid = (good['T'], good['rho'], good['Y'], good['A'], good['Z'])
        bad = [(True, *valid[1:]), (float('nan'), *valid[1:]), (9e6, *valid[1:]),
               (3.1e7, *valid[1:]), (valid[0], 1e3, *valid[2:]),
               (*valid[:2], [1.], [1], [True]), (*valid[:2], [-1., .5], [1,4], [1,2]),
               (*valid[:2], [.7, .1], [1,4], [1,2]), (*valid[:2], [.7], [1,4], [1,2]),
               (*valid[:2], [.7, .075], [1.,4], [1,2]), (*valid[:2], [.7, .075], [1,4], [2,2]),
               (*valid[:2], [1.,0.], [1,4], [1,2]),
               (1e7, 3e5, [1/56], [56], [26])]
        for req in bad:
            try:
                model.evaluate(*req)
            except ValueError as e:
                r['refusals'].append(str(e))
            else:
                raise AssertionError('Invalid/out-of-domain Coulomb mixture accepted: '+repr(req))
        assert all(sha(ROOT/n) == h for n,h in {**hashes, **protected}.items())
        r.update(accepted=True, completed=True,
                 scope='Numerical classical-ion nonideal mixture EOS only; no coupled network/screening/product or observational calibration.')
    except Exception:
        r['failure'] = traceback.format_exc()
    path.write_text(json.dumps(r, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(accepted=r['accepted'], cases=len(r['cases']), structural=r['structural_checks'],
                         refusals=len(r['refusals']), failure=r.get('failure'))), flush=True)
    return 0 if r['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
