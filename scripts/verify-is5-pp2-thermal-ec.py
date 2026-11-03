"""Stress changing electron number in an isolated thermal Be7 capture fixture."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
import argparse
import hashlib
import json
import traceback
import zipfile
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

ROOT=Path(__file__).resolve().parents[1]
h=SourceFileLoader('pp2_ec_science',str(ROOT/'scripts/verify-is5-pp2.py')).load_module();m=h.m
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label')
    folder=ROOT/('output/is5-pp2-thermal-ec-'+args.label);receipt=ROOT/('evidence/is5-pp2-thermal-ec-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve fixture evidence')
    folder.mkdir();files=[ROOT/n for n in m.IMPORTED]+[Path(__file__),ROOT/'scripts/verify-is5-pp2.py']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in files}
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
    r=dict(accepted=False,completed=False,source_sha256=hashes,cases=[])
    try:
        for initial_mass in (1e-5,1e-4):
            p={**m.DEFAULT_PARAMETERS,'hydrogen_fraction':.5,'catalyst_fraction':0.,'duration_s':2*31557600.}
            switches={c:c=='be7ec' for c in m.CHANNELS};initial=np.zeros(24)
            initial[0]=.5;initial[3]=(.5-initial_mass)/4;initial[10]=initial_mass/7
            actual=m._integrate(p,None,switches,'isochoric_ideal','nubase2020',1e-10,initial)
            nb=p['density_kg_m3']/m.atomic_mass;be0=float(initial[10]);ye0=float(m.Z@initial[:12]);yi=float(np.sum(initial[:12]))
            u0=m.eos.mixture(p['temperature_K'],p['density_kg_m3'],yi,ye0)['internal_energy_J_m3']
            ec=m.CHANNELS.index('be7ec');q=float(m.Q[ec]-m.QNU[ec])
            def temperature(b,u):
                ye=ye0-(be0-b)
                return brentq(lambda t:m.eos.mixture(float(t),p['density_kg_m3'],yi,ye)['internal_energy_J_m3']-u,1e7,1.6e7,xtol=2e-6,rtol=2e-14)
            def rhs(t,y):
                b=float(y[0]);u=float(y[1]*u0);T=temperature(b,u);T6=T/1e6
                decay=5.60e-9*(p['density_kg_m3']/1000)*(ye0-(be0-b))*T6**(-.5)*(1+.004*(T6-16))*b
                return [-decay,nb*q*decay/u0]
            reference=solve_ivp(rhs,[0,p['duration_s']],[be0,1.],method='BDF',t_eval=actual['time_s'],rtol=2e-11,atol=[1e-20,1e-13]);assert reference.success
            tref=np.array([temperature(float(b),float(u*u0)) for b,u in reference.y.T])
            terr=float(np.max(abs(tref-actual['temperature_K'])/np.array(actual['temperature_K'])))
            berr=float(np.max(abs(reference.y[0]-np.array(actual['number_per_baryon'])[:,10])))
            assert terr<=1e-7 and berr<=1e-8
            assert actual['temperature_K'][-1]>p['temperature_K'] and not np.any(actual['produced_positrons_m3'])
            assert actual['neutrino_count_m3']==actual['captured_electrons_m3']
            name='Be7-X-'+str(initial_mass)+'.json';path=folder/name;path.write_text(json.dumps(actual,indent=2)+'\n')
            r['cases'].append(dict(initial_Be7_mass_fraction=initial_mass,initial_T_K=p['temperature_K'],final_T_K=actual['temperature_K'][-1],
                BDF_temperature_relative_error=terr,BDF_Be7_per_baryon_error=berr,conservation=actual['conservation'],path=path.relative_to(ROOT).as_posix(),sha256=sha(path)))
        assert all(sha(ROOT/n)==v for n,v in hashes.items());r.update(accepted=True,completed=True)
    except Exception:r['failure']=traceback.format_exc()
    receipt.write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n',encoding='utf-8');print(json.dumps(dict(accepted=r["accepted"],cases=len(r["cases"]),failure=r.get("failure")),ensure_ascii=False),flush=True)
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
