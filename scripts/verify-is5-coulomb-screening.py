"""Screening against charge/mass-conserving virtual-fusion free-energy differences."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import sys
import traceback
import zipfile
import mpmath as mp
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'output/is5-coulomb-network-staging'))
import is5_coulomb_network as model

sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('Invalid label')
    path = ROOT/f'evidence/is5-coulomb-screening-{args.label}.json'
    archive = ROOT/f'output/is5-coulomb-screening-{args.label}.zip'
    if path.exists() or archive.exists():
        raise FileExistsError('Preserve screening evidence')
    files = [*model.FILES, *model.eos.FILES, *model.base.FILES, Path(__file__)]
    for name in ['is5-coulomb-mixture-20261028b', 'is5-coulomb-mixture-composition-20261028a']:
        receipt = ROOT/f'evidence/{name}.json'
        prior = json.loads(receipt.read_text(encoding='utf-8'))
        assert prior['accepted']
        assert all(sha(ROOT/n) == h for n,h in prior['source_sha256'].items())
        files.append(receipt)
    hashes = {p.relative_to(ROOT).as_posix():sha(p) for p in files}
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for n in hashes:
            z.write(ROOT/n, n)
    r = dict(accepted=False, completed=False, source_sha256=hashes, archive_sha256=sha(archive),
             generation=model.generation(), cases=[], refusals=[],
             limits_before_execution=dict(virtual_fusion_difference_scaled=2e-6, high_precision_scaled=2e-9))
    try:
        mp.mp.dps = 50
        for t,rho,seed in [(1.1e7,1.1e4,'n14'),(1.5e7,1.5e5,'n14'),(1.5e7,1.5e5,'o16'),(1.59e7,2.9e5,'o16')]:
            p = {**model.base.DEFAULT_PARAMETERS, 'temperature_K':t, 'density_kg_m3':rho, 'catalyst_seed':seed}
            y = model.base.initial_state(p)[:16]
            result = model.screening_factors(t,rho,[float(v) for v in y])
            nb = rho/model.eos.MU
            mt, mn = mp.mpf(str(t)), mp.mpf(str(nb))
            rows = []
            for j,(i1,i2) in model.BINARY.items():
                pair = result['pairs'][model.CHANNELS[j]]
                zc, ac = pair['compound_charge'], pair['compound_mass_number']
                z = [*model.ZI, zc]
                a = np.array([*model.AI, ac])
                pop = [mp.mpf(str(v)) for v in y]+[mp.mpf(0)]
                direction = np.zeros(17,dtype=int)
                direction[i1] -= 1
                direction[i2] -= 1
                direction[-1] += 1
                assert int(a@direction) == 0 and int(np.array(z)@direction) == 0
                def free(extent, component=None):
                    yy = [v+extent*int(d) for v,d in zip(pop,direction)]
                    parts = model.eos.free_energy_components(mt,mn,yy,z,mp)
                    return sum(parts.values()) if component is None else parts[component]
                reference = -mp.diff(free,mp.mpf(0))/(mn*mp.mpf(str(model.eos.K))*mt)
                eps = mp.mpf('1e-7')
                difference = -(free(eps)-free(-eps))/(2*eps*mn*mp.mpf(str(model.eos.K))*mt)
                expected = float(reference)
                scale = max(abs(expected),1e-4)
                high_error = abs(pair['exponent']-expected)/scale
                fd_error = abs(pair['exponent']-float(difference))/scale
                ee_h = -mp.diff(lambda q:free(q,'ee'),mp.mpf(0))/(mn*mp.mpf(str(model.eos.K))*mt)
                assert high_error <= 2e-9 and fd_error <= 2e-6
                assert abs(float(ee_h)) <= 1e-12 and abs(pair['exponent_components']['ee']) <= 1e-12
                assert abs(math.exp(pair['exponent'])-result['factors'][j]) < 1e-14
                rows.append(dict(channel=model.CHANNELS[j],pair=pair,reference_h=expected,
                                 high_precision_scaled_error=high_error,difference_scaled_error=fd_error,
                                 ee_virtual_fusion_h=float(ee_h)))
            assert len(rows) == 13
            assert result['factors'][model.CHANNELS.index('pp')] == result['factors'][model.CHANNELS.index('dp')]
            assert result['factors'][model.CHANNELS.index('c12pg')] == result['factors'][model.CHANNELS.index('c13pg')]
            for j in set(range(model.NCHAN))-set(model.BINARY):
                assert result['factors'][j] == 1., model.CHANNELS[j]
            # A beta final product is not the charge-conserving entrance compound.
            state = model._state(t,rho,y,True)
            mu = state['components']['sum']['neutral_chemical_potential_J']
            wrong_pp = (2*mu[0]-mu[1])/(model.eos.K*t)
            assert abs(wrong_pp-result['pairs']['pp']['exponent']) > 1e-3
            for strong in [False,True]:
                for weak in [False,True]:
                    for em in [False,True]:
                        _,_,active = model.base.active_channels(dict(strong=strong,weak=weak,electromagnetic=em))
                        bare = model.base.rate_constants(t,rho,active)
                        screened = bare*np.array(result['factors'])
                        for j,c in enumerate(model.CHANNELS):
                            assert (screened[j] == 0) == (not active[c])
                            if j not in model.BINARY:
                                assert screened[j] == bare[j]
            r['cases'].append(dict(T=t,rho=rho,seed=seed,pairs=rows,wrong_beta_product_pp_h=wrong_pp))
            print(json.dumps(dict(T=t,rho=rho,seed=seed,pairs=len(rows),passed=True)),flush=True)
        p = model.base.DEFAULT_PARAMETERS
        y = [float(v) for v in model.base.initial_state(p)[:16]]
        for request in [(True,1.5e5,y),(15e6,1e3,y),(9e6,1.5e5,y),(15e6,1.5e5,y[:15]),
                        (15e6,1.5e5,[True,*y[1:]]),(15e6,1.5e5,[-1.,*y[1:]])]:
            try:
                model.screening_factors(*request)
            except ValueError as e:
                r['refusals'].append(str(e))
            else:
                raise AssertionError('Invalid screening request accepted')
        assert all(sha(ROOT/n) == h for n,h in hashes.items())
        r.update(accepted=True,completed=True,scope='Static thermodynamic fusion screening only; no coupled evolution/worker/product acceptance.')
    except Exception:
        r['failure'] = traceback.format_exc()
    path.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(accepted=r['accepted'],cases=len(r['cases']),refusals=len(r['refusals']),failure=r.get('failure'))),flush=True)
    return 0 if r['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
