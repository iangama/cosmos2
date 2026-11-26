"""Additional composition/domain audit of the frozen, accepted mixture B sources."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import traceback
import zipfile
import mpmath as mp
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'output/is5-coulomb-mixture-staging'))
import is5_coulomb_mixture as model

sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):
        parser.error('Invalid label')
    path = ROOT/f'evidence/is5-coulomb-mixture-composition-{args.label}.json'
    archive = ROOT/f'output/is5-coulomb-mixture-composition-{args.label}.zip'
    if path.exists() or archive.exists():
        raise FileExistsError('Preserve composition evidence')
    anchor = ROOT/'evidence/is5-coulomb-mixture-20261028b.json'
    prior = json.loads(anchor.read_text(encoding='utf-8'))
    assert prior['accepted'] and prior['generation'] == model.generation()
    hashes = {**prior['source_sha256'], anchor.relative_to(ROOT).as_posix():sha(anchor),
              Path(__file__).relative_to(ROOT).as_posix():sha(Path(__file__))}
    assert all(sha(ROOT/n) == h for n,h in hashes.items())
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for n in hashes:
            z.write(ROOT/n, n)
    r = dict(accepted=False, completed=False, source_sha256=hashes, archive_sha256=sha(archive),
             generation=model.generation(), cases=[], refusals=[], limits_before_execution=dict(gradient_relative=2e-6))
    try:
        mp.mp.dps = 50
        for index in [0, 1, 6, 7, 10, 11]:
            case = prior['cases'][index]
            p, actual = case['fixture'], case['EOS']
            t, rho, y, z = p['T'], p['rho'], p['Y'], p['Z']
            mt, mn = mp.mpf(str(t)), mp.mpf(str(rho/model.MU))
            def energy(pop):
                my = [mp.mpf(str(v)) for v in pop]
                f = lambda temp:sum(model.free_energy_components(temp, mn, my, z, mp).values())
                uc = float(f(mt)-mt*mp.diff(f, mt))
                base = model.ideal.mixture(t, rho, float(sum(pop)), float(np.array(z)@pop))
                return uc, uc+base['internal_energy_J_m3']
            errors = []
            for i in range(16):
                delta = 1e-5*max(abs(y[i]), .01)
                plus, minus = list(y), list(y)
                plus[i] += delta
                minus[i] -= delta
                up, um = energy(plus), energy(minus)
                dc, dtot = [(a-b)/(2*delta) for a,b in zip(up,um)]
                refc = actual['components']['sum']['du_dnumber_per_baryon_J_m3'][i]
                reft = actual['total']['du_dnumber_per_baryon_J_m3'][i]
                errc, errt = abs(dc-refc)/abs(refc), abs(dtot-reft)/abs(reft)
                assert max(errc, errt) <= 2e-6, (index, i, errc, errt)
                errors.append(dict(species_index=i, initial_Y=y[i], correction_relative=errc, total_relative=errt))
            r['cases'].append(dict(prior_case=index, fixture=p, gradient_errors=errors))
            print(json.dumps(dict(case=index, gradient_max=max(max(q['correction_relative'],q['total_relative']) for q in errors))), flush=True)
        # Positive trace remains subject to the per-species liquid/quantum guard.
        for trace in [1e-8, 1e-20, 1e-30]:
            try:
                model.evaluate(1e7, 3e5, [.7-56*trace, .075, trace], [1,4,56], [1,2,26])
            except ValueError as e:
                r['refusals'].append(dict(trace=trace, reason=str(e)))
            else:
                raise AssertionError('A positive high-Gamma trace was discarded')
        zeros = model.evaluate(1e7, 3e5, [.7,.075,0.], [1,4,56], [1,2,26])
        residue = model.evaluate(1.5e7,1.5e5,[.7,.075,-1e-30],[1,4,14],[1,2,7])
        assert residue['diagnostics']['negative_residue_indices'] == [2]
        assert residue['components']['ii']['free_energy_J_m3'] < 0
        r['zero_trace_accepted'] = zeros['diagnostics']
        r['raw_negative_residue_preserved'] = residue['diagnostics']
        assert all(sha(ROOT/n) == h for n,h in hashes.items())
        r.update(accepted=True, completed=True, scope='Supplementary numerical composition/domain audit only; no evolution/product.')
    except Exception:
        r['failure'] = traceback.format_exc()
    path.write_text(json.dumps(r, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(accepted=r['accepted'], cases=len(r['cases']), refusals=len(r['refusals']), failure=r.get('failure'))), flush=True)
    return 0 if r['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
