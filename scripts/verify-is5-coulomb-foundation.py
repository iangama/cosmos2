"""Independent polylog FD response, thermodynamic identities and DH domain refusals."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import math
import sys
import traceback
import zipfile
import mpmath as mp
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT/'output/is5-coulomb-staging'
sys.path.insert(0, str(STAGE))
import is5_coulomb as model

sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def relative(a, b):
    return abs(a-b)/max(abs(b), 1e-280)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('Invalid immutable evidence label')
    path = ROOT/f'evidence/is5-coulomb-foundation-{args.label}.json'
    archive = ROOT/f'output/is5-coulomb-foundation-{args.label}.zip'
    if path.exists() or archive.exists():
        raise FileExistsError('Preserve Coulomb evidence and archive')
    files = [*model.FILES, Path(__file__), ROOT/'IS-5-COULOMB-VERIFICACAO-B.md', ROOT/'output/is5-thermal-staging/is5_eos.py',
             ROOT/'output/is5-thermal-staging/is5_core.py']
    # Existing accepted sources are checked without repeating their scientific integrations.
    anchors = ['is5-thermal-eos-20261026a', 'is5-cno2-science-20261027a',
               'is5-cno2-worker-artifact-20261027a', 'is5-native-cno2-20261027a']
    protected = {}
    for name in anchors:
        receipt = ROOT/f'evidence/{name}.json'
        obj = json.loads(receipt.read_text(encoding='utf-8'))
        if not obj.get('accepted'):
            raise ValueError('Existing source anchor is not accepted: '+name)
        files.append(receipt)
        for n, h in obj['source_sha256'].items():
            if sha(ROOT/n) != h:
                raise ValueError('Previously accepted source differs: '+n)
            protected[n] = h
    hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in files}
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for n in hashes:
            z.write(ROOT/n, n)
    r = dict(accepted=False, completed=False, source_sha256=hashes,
             archive_sha256=sha(archive), generation=model.generation(),
             prior_sources_checked=len(protected), response=[], cases=[], screening=[], refusals=[],
             limits_before_execution=dict(response_relative=2e-9, EOS_relative=2e-10,
                                          differences_relative=2e-6, Maxwell_relative=2e-6))
    mp.mp.dps = 50
    fd = lambda s, eta: mp.re(-mp.polylog(mp.mpf(str(s))+1, -mp.exp(eta)))
    try:
        for eta in [-20., -10., -5., -1., 0., 1., 3., 10., 20.]:
            t = 1.5e7
            actual = model.response_eta(t, eta)
            mt, mh, mk, mme, me = map(lambda x: mp.mpf(str(x)), (t, model.H, model.K, model.ME, eta))
            c = 2/(mh/mp.sqrt(2*mp.pi*mme*mk*mt))**3
            f, g = fd(.5, me), fd(-.5, me)
            ne = c*f
            R = lambda x: fd(-.5, x)/fd(.5, x)
            a = lambda x: -mp.mpf('1.5')/R(x)
            qL = ne*mp.diff(R, me)*a(me)
            qLL = ne*(mp.diff(R, me, 2)*a(me)**2+mp.diff(R, me)*mp.diff(a, me)*a(me))
            dqdne = lambda x: fd(-1.5, x)/fd(-.5, x)
            references = dict(susceptibility_m3_J=c*g/(mk*mt),
                              q_effective_electron_density_m3=c*g,
                              dq_dlnT_fixed_ne_m3=qL, d2q_dlnT2_fixed_ne_m3=qLL,
                              dq_dne_fixed_T=dqdne(me),
                              d_dlnT_dq_dne_fixed_ne=mp.diff(dqdne, me)*a(me))
            raw_errors = {key:relative(actual[key], float(value)) for key, value in references.items()}
            errors = dict(raw_errors)
            for key in ['dq_dlnT_fixed_ne_m3', 'd2q_dlnT2_fixed_ne_m3']:
                errors[key] = abs(actual[key]-float(references[key]))/float(ne)
            key = 'd_dlnT_dq_dne_fixed_ne'
            errors[key] = abs(actual[key]-float(references[key]))
            assert max(errors.values()) <= 2e-9, (eta, errors)
            # Independent chemical-potential difference of the number density.
            deta = 2e-5
            chi_fd = float(c)*(model.ideal.fermi(.5, eta+deta)-model.ideal.fermi(.5, eta-deta))/(2*deta*model.K*t)
            assert relative(chi_fd, actual['susceptibility_m3_J']) <= 2e-6
            # Number held fixed while the temperature and its implicit eta move.
            h = 2e-4
            rp = model.electron_response(t*math.exp(h), float(ne))
            rm = model.electron_response(t*math.exp(-h), float(ne))
            fd_qL = (rp['q_effective_electron_density_m3']-rm['q_effective_electron_density_m3'])/(2*h)
            fd_qLL = (rp['dq_dlnT_fixed_ne_m3']-rm['dq_dlnT_fixed_ne_m3'])/(2*h)
            derivative_error = max(abs(fd_qL-actual['dq_dlnT_fixed_ne_m3']),
                                   abs(fd_qLL-actual['d2q_dlnT2_fixed_ne_m3']))/float(ne)
            assert derivative_error <= 2e-6, (eta, derivative_error)
            r['response'].append(dict(eta=eta, reference_scaled_errors=errors,
                                      reference_raw_relative_errors=raw_errors,
                                      difference_error_over_ne=derivative_error,
                                      chi_difference_relative_error=relative(chi_fd, actual['susceptibility_m3_J'])))
        classical = model.response_eta(1.5e7, -20.)
        assert abs(classical['q_over_ne']-1) < 2e-9
        for t in [1.9e7, 2.3e7, 2.8e7]:
            for rho in [1.05e4, 1.4e4]:
                for x in [.35, .7]:
                    y = [x, (1-x)/4]
                    a, z = [1, 4], [1, 2]
                    original = copy.deepcopy((y, a, z))
                    actual = model.evaluate(t, rho, y, a, z)
                    assert original == (y, a, z)
                    mt, mr, mu, mk, ee, ep = map(lambda v:mp.mpf(str(v)),
                                               (t, rho, model.MU, model.K, model.E, model.EPS))
                    my = [mp.mpf(str(v)) for v in y]
                    nb = mr/mu
                    counts = [nb*v for v in my]
                    # F(V,T,Ni) gives volume/T/composition derivatives independently.
                    def F(volume, temp, populations):
                        moment = sum(n*(q*q+q) for n, q in zip(populations, z))/volume
                        return -volume*mk*temp/(12*mp.pi)*(ee**2*moment/(ep*mk*temp))**mp.mpf('1.5')
                    f = F(mp.mpf(1), mt, counts)
                    u = f-mt*mp.diff(lambda temp:F(mp.mpf(1), temp, counts), mt)
                    p = -mp.diff(lambda volume:F(volume, mt, counts), mp.mpf(1))
                    cv = -mt*mp.diff(lambda temp:F(mp.mpf(1), temp, counts), mt, 2)
                    corr = actual['correction']
                    errors = {key:relative(corr[key], float(val)) for key, val in
                              [('free_energy_J_m3', f), ('internal_energy_J_m3', u),
                               ('pressure_Pa', p), ('heat_capacity_J_m3_K', cv)]}
                    assert max(errors.values()) <= 2e-10
                    gradient_errors = []
                    chemical_errors = []
                    delta = 5e-5
                    for i in range(2):
                        def fn(value):
                            populations = list(counts)
                            populations[i] = value
                            return F(mp.mpf(1), mt, populations)
                        chem = mp.diff(fn, counts[i])
                        chemical_errors.append(relative(corr['neutral_chemical_potential_J'][i], float(chem)))
                        yp, ym = np.array(y), np.array(y)
                        d = y[i]*delta
                        yp[i] += d
                        ym[i] -= d
                        def raw(pop):
                            c0 = model._classical(t, rho/model.MU, pop, np.array(z))
                            b0 = model.ideal.mixture(t, rho, float(sum(pop)), float(np.array(z)@pop))
                            return c0, b0
                        cp, bp = raw(yp)
                        cm, bm = raw(ym)
                        dc = (cp['internal_energy_J_m3']-cm['internal_energy_J_m3'])/(2*d)
                        dtot = ((cp['internal_energy_J_m3']+bp['internal_energy_J_m3'])-
                                (cm['internal_energy_J_m3']+bm['internal_energy_J_m3']))/(2*d)
                        gradient_errors.extend([relative(dc, corr['du_dnumber_per_baryon_J_m3'][i]),
                                                relative(dtot, actual['total']['du_dnumber_per_baryon_J_m3'][i])])
                    assert max(chemical_errors) <= 2e-10
                    assert max(gradient_errors) <= 2e-6
                    dT, dr = t*delta, rho*delta
                    tp = model.evaluate(t+dT, rho, y, a, z)
                    tm = model.evaluate(t-dT, rho, y, a, z)
                    rp = model.evaluate(t, rho+dr, y, a, z)
                    rm = model.evaluate(t, rho-dr, y, a, z)
                    maxwell = {}
                    cv_errors = {}
                    for key in ['correction', 'total']:
                        cvfd = (tp[key]['internal_energy_J_m3']-tm[key]['internal_energy_J_m3'])/(2*dT)
                        cv_errors[key] = relative(cvfd, actual[key]['heat_capacity_J_m3_K'])
                        de = (rp[key]['internal_energy_J_m3']/(rho+dr)-rm[key]['internal_energy_J_m3']/(rho-dr))/(2*dr)
                        dp = (tp[key]['pressure_Pa']-tm[key]['pressure_Pa'])/(2*dT)
                        maxwell[key] = abs(actual[key]['pressure_Pa']-rho*rho*de-t*dp)/abs(actual[key]['pressure_Pa'])
                    assert max(maxwell.values()) <= 2e-6
                    assert max(cv_errors.values()) <= 2e-6
                    assert all(corr[k] < 0 for k in ['free_energy_J_m3', 'internal_energy_J_m3', 'pressure_Pa'])
                    pair = model.screening(t, rho, y, a, z, 1, 1)
                    # Neutral electron terms cancel in a charge-conserving virtual fusion.
                    moment = nb*sum(my[i]*(z[i]**2+z[i]) for i in range(2))
                    muq = lambda q:mp.mpf('1.5')*f*(q*q+q)/moment
                    href = (2*muq(1)-muq(2))/(mk*mt)
                    herr = relative(pair['exponent'], float(href))
                    assert herr <= 2e-10
                    r['screening'].append(dict(T=t, rho=rho, x=x, pair=pair, chemical_relative_error=herr))
                    r['cases'].append(dict(T=t, rho=rho, x=x, EOS=actual,
                                           reference_relative_errors=errors, chemical_relative_errors=chemical_errors,
                                           gradient_relative_errors=gradient_errors, Maxwell_relative_errors=maxwell,
                                           Cv_difference_relative_errors=cv_errors))
        good = (2.8e7, 1.05e4, [.7, .075], [1, 4], [1, 2])
        bad = [(True, *good[1:]), (float('nan'), *good[1:]), (9e6, *good[1:]),
               (3.1e7, *good[1:]), (good[0], 1e3, *good[2:]),
               (*good[:2], [True, .075], *good[3:]), (*good[:2], [-.1, .275], *good[3:]),
               (*good[:2], [1., .075], *good[3:]), (*good[:2], [.7], *good[3:]),
               (*good[:3], [1., 4], good[4]), (*good[:4], [1, True]),
               (*good[:3], [1, 301], good[4]), (*good[:4], [2, 2]),
               (1.5e7, 1.5e5, [.34, .65/4, .01/14], [1, 4, 14], [1, 2, 7]),
               (1e7, 3e5, [.7, .075], [1, 4], [1, 2]),
               (good[0], good[1], [.7, .075, 1e-30], [1, 4, 16], [1, 2, 8])]
        for request in bad:
            try:
                model.evaluate(*request)
            except ValueError as e:
                r['refusals'].append(str(e))
            else:
                raise AssertionError('Invalid/out-of-domain EOS request accepted: '+repr(request))
        for charges in [(True, 1), (1., 1), (0, 1), (26, 1), (2, 2)]:
            try:
                model.screening(*good, *charges)
            except ValueError as e:
                r['refusals'].append(str(e))
            else:
                raise AssertionError('Invalid/out-of-domain pair accepted')
        # Exact zero trace does not constrain bath; positive trace must constrain it.
        zero = model.evaluate(good[0], good[1], [.7, .075, 0.], [1, 4, 16], [1, 2, 8])
        assert zero['total']['pressure_Pa'] == model.evaluate(*good)['total']['pressure_Pa']
        assessment = model.assess(*bad[-3])
        assert not assessment['inside_domain']
        assert 'maximum_ion_Gamma' in assessment['violations']
        r['solar_default_refused'] = assessment
        weak = model.evaluate(1.9e7, 1.4e4, [.7, .075], [1, 4], [1, 2])
        hot = model.evaluate(2.8e7, 1.4e4, [.7, .075], [1, 4], [1, 2])
        dilute = model.evaluate(1.9e7, 1.05e4, [.7, .075], [1, 4], [1, 2])
        assert abs(hot['correction']['pressure_Pa']) < abs(weak['correction']['pressure_Pa'])
        assert abs(dilute['correction']['pressure_Pa']) < abs(weak['correction']['pressure_Pa'])
        assert all(sha(ROOT/n) == h for n, h in {**hashes, **protected}.items())
        r.update(accepted=True, completed=True,
                 scope='Numerical FD response and restricted classical DH EOS/screening only; solar CNO explicitly refused, no coupled solver/worker/UI.')
    except Exception:
        r['failure'] = traceback.format_exc()
    path.write_text(json.dumps(r, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(accepted=r['accepted'], response=len(r['response']), cases=len(r['cases']),
                         screening=len(r['screening']), refusals=len(r['refusals']),
                         protected=r['prior_sources_checked'], failure=r.get('failure'))), flush=True)
    return 0 if r['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
