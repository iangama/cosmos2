"""Screened Radau evolution against BDF in U with independent EOS inversion."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import time
import traceback
import zipfile
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'output/is5-coulomb-network-staging'))
import is5_coulomb_network as model

sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def independent(p, mode, times, tolerance):
    """Energy coordinate, numerical inverse, manually assembled mass-action flux."""
    base = model.base
    rho = p['density_kg_m3']
    nb = rho/model.eos.MU
    y0 = base.initial_state(p)
    initial = model.eos.evaluate(p['temperature_K'],rho,[float(v) for v in y0[:16]],model.AI,model.ZI)
    u0 = initial['total']['internal_energy_J_m3']
    thermal = mode == 'isochoric'
    if thermal:
        y0 = np.r_[y0,1.]
    calls, inversions = 0, 0
    def thermo(t,pop):
        return model.eos.evaluate(float(t),rho,[float(v) for v in pop],model.AI,model.ZI)
    def inverse(pop, energy):
        nonlocal inversions
        inversions += 1
        cache = {}
        def residual(t):
            q = thermo(t,pop)
            cache[t] = q
            return q['total']['internal_energy_J_m3']/u0-energy
        t = brentq(residual,1e7*(1+1e-12),1.6e7*(1-1e-12),xtol=1e-6,rtol=2e-13)
        return float(t),cache.get(t) or thermo(t,pop)
    def rhs(time, values):
        nonlocal calls
        calls += 1
        if calls > base.legacy.MAX_RHS_EVALUATIONS:
            raise RuntimeError('Independent BDF RHS budget exceeded')
        pop = values[:16]
        if thermal:
            t, state = inverse(pop,float(values[-1]))
        else:
            t, state = p['temperature_K'],thermo(p['temperature_K'],pop)
        bare = base.rate_constants(t,rho)
        # Screening has its own accepted derivative/difference verification.
        wrapper = dict(components=state['components'])
        factors = model._screening_from_state(t,rho,pop,wrapper)[0]
        flux = []
        for j,reactants in enumerate(base.REACTANTS):
            value = bare[j]*factors[j]
            for species,multiplicity in reactants.items():
                value *= pop[base.SPECIES.index(species)]**multiplicity
            if base.CHANNELS[j] == 'be7ec':
                value *= float(base.Z@pop)
            flux.append(value)
        flux = np.array(flux)
        # Explicit U deposition has no EOS composition gradient or dT/dt.
        return np.r_[base.S@flux,flux,nb*float((base.Q-base.QNU)@flux)/u0] if thermal else np.r_[base.S@flux,flux]
    sol = solve_ivp(rhs,[0,p['duration_s']],y0,method='BDF',t_eval=times,rtol=tolerance,
                    atol=base.ATOL+([1e-12] if thermal else []))
    assert sol.success, sol.message
    pop = sol.y[:16,:].T
    temps = [inverse(y,float(u))[0] for y,u in zip(pop,sol.y[-1])] if thermal else [p['temperature_K']]*len(times)
    return dict(number_per_baryon=pop.tolist(),temperature_K=temps,extents_per_baryon=sol.y[16:34,:].T.tolist(),
                solver=dict(method='BDF',energy_coordinate=thermal,RHS_calls=calls,EOS_inversions=inversions))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label',required=True)
    args = parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('Invalid label')
    path = ROOT/f'evidence/is5-coulomb-evolution-{args.label}.json'
    archive = ROOT/f'output/is5-coulomb-evolution-{args.label}.zip'
    folder = ROOT/f'output/is5-coulomb-evolution-{args.label}'
    if path.exists() or archive.exists() or folder.exists():
        raise FileExistsError('Preserve evolution evidence')
    anchor = ROOT/'evidence/is5-coulomb-screening-20261028a.json'
    prior = json.loads(anchor.read_text(encoding='utf-8'))
    assert prior['accepted'] and prior['generation'] == model.generation()
    hashes = {**prior['source_sha256'],anchor.relative_to(ROOT).as_posix():sha(anchor),
              Path(__file__).relative_to(ROOT).as_posix():sha(Path(__file__))}
    assert all(sha(ROOT/n) == h for n,h in hashes.items())
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:
            z.write(ROOT/n,n)
    folder.mkdir()
    r = dict(accepted=False,completed=False,source_sha256=hashes,archive_sha256=sha(archive),
             generation=model.generation(),cases=[],controls=[],refusals=[],
             limits_before_execution=dict(T_relative=1e-7,Y_absolute=1e-8,energy_normalized=1e-8))
    try:
        year = 31557600.
        specifications = [('n14','prescribed',1000),('n14','isochoric',1000),
                          ('o16','prescribed',1000),('o16','isochoric',1000),('n14','isochoric',100000)]
        for index,(seed,mode,years) in enumerate(specifications):
            p = {**model.base.DEFAULT_PARAMETERS,'catalyst_seed':seed,'duration_s':years*year}
            start = time.perf_counter()
            actual = model.integrate_zone(p,mode=mode)
            out = folder/f'case{index}-Radau.json'
            out.write_text(json.dumps(actual,ensure_ascii=False)+'\n',encoding='utf-8')
            print(json.dumps(dict(case=index,stage='Radau-complete',solver=actual['solver'],
                                  T_final=actual['temperature_K'][-1],seconds=time.perf_counter()-start)),flush=True)
            reference = independent(p,mode,actual['time_s'],2e-10)
            ref_path = folder/f'case{index}-BDF-U.json'
            ref_path.write_text(json.dumps(reference,ensure_ascii=False)+'\n',encoding='utf-8')
            refined = model.integrate_zone(p,mode=mode,tolerance=2e-10)
            refined_path = folder/f'case{index}-Radau-refined.json'
            refined_path.write_text(json.dumps(refined,ensure_ascii=False)+'\n',encoding='utf-8')
            pop = np.array(actual['number_per_baryon'])
            temps = np.array(actual['temperature_K'])
            err_y = float(np.max(abs(pop-np.array(reference['number_per_baryon']))))
            err_t = float(np.max(abs(temps-np.array(reference['temperature_K']))/temps))
            refine_y = float(np.max(abs(pop-np.array(refined['number_per_baryon']))))
            refine_t = float(np.max(abs(temps-np.array(refined['temperature_K']))/temps))
            assert max(err_y,refine_y) <= 1e-8 and max(err_t,refine_t) <= 1e-7
            if years == 100000:
                assert actual['temperature_K'][-1]-actual['temperature_K'][0] > 1e4
            r['cases'].append(dict(seed=seed,mode=mode,years=years,BDF_composition_absolute_error=err_y,
                  BDF_temperature_relative_error=err_t,refinement_composition_absolute_error=refine_y,
                  refinement_temperature_relative_error=refine_t,conservation=actual['conservation'],
                  temperatures=[actual['temperature_K'][0],actual['temperature_K'][-1]],
                  artifact_sha256={v.relative_to(ROOT).as_posix():sha(v) for v in [out,ref_path,refined_path]},
                  elapsed_seconds=time.perf_counter()-start))
            print(json.dumps(dict(case=index,completed=True,Y_error=err_y,T_error=err_t,
                                  seconds=time.perf_counter()-start)),flush=True)
        short = {**model.base.DEFAULT_PARAMETERS,'duration_s':100*year}
        for mode in ['prescribed','isochoric']:
            actual = model.integrate_zone(short,mode=mode,include_coulomb=False,include_screening=False)
            legacy = model.base.integrate_zone(short,mode='prescribed' if mode == 'prescribed' else 'isochoric_ideal')
            ey = float(np.max(abs(np.array(actual['number_per_baryon'])-np.array(legacy['number_per_baryon']))))
            et = float(np.max(abs(np.array(actual['temperature_K'])-np.array(legacy['temperature_K']))/np.array(legacy['temperature_K'])))
            assert ey <= 1e-8 and et <= 1e-7
            r['controls'].append(dict(name='ideal_legacy_limit',mode=mode,Y_error=ey,T_error=et))
        for name,acting in [('alloff',dict(strong=False,weak=False,electromagnetic=False)),
                            ('weakoff',dict(weak=False)),('EMoff',dict(electromagnetic=False))]:
            actual = model.integrate_zone(short,acting,mode='isochoric')
            if name in ['alloff','EMoff']:
                assert np.max(abs(np.array(actual['number_per_baryon'])-np.array(actual['initial_number_per_baryon']))) < 1e-14
                assert max(abs(v-actual['temperature_K'][0]) for v in actual['temperature_K']) < 1e-5
            if name == 'weakoff':
                assert max(actual['neutrino_count_m3']) == 0
            r['controls'].append(dict(name=name,conservation=actual['conservation']))
        unscreened = model.integrate_zone(short,mode='isochoric',include_screening=False)
        assert np.array(unscreened['screening_factors']).min() == np.array(unscreened['screening_factors']).max() == 1.
        r['controls'].append(dict(name='Coulomb_reservoir_without_screening',conservation=unscreened['conservation']))
        for opts in [dict(include_coulomb=False),dict(include_coulomb=1),dict(include_screening=1),
                     dict(mode='unknown'),dict(tolerance=True),dict(tolerance=1e-14)]:
            try:
                model.integrate_zone(short,**opts)
            except ValueError as e:
                r['refusals'].append(str(e))
            else:
                raise AssertionError('Invalid screened integration accepted')
        # Whole-run refusal after a valid hot initial state; no partial result is published.
        hot = {**short,'temperature_K':1.5999999e7,'duration_s':1e6*year}
        try:
            model.integrate_zone(hot)
        except ValueError as e:
            r['refusals'].append('whole-run hot trajectory: '+str(e))
        else:
            raise AssertionError('Out-of-domain full trajectory was accepted')
        assert all(sha(ROOT/n) == h for n,h in hashes.items())
        r.update(accepted=True,completed=True,scope='Coupled screened classical-ion zone science only; worker/product/performance not accepted.')
    except Exception:
        r['failure'] = traceback.format_exc()
    path.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(accepted=r['accepted'],cases=len(r['cases']),controls=len(r['controls']),
                         refusals=len(r['refusals']),failure=r.get('failure'))),flush=True)
    return 0 if r['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
