"""First pp-III slice: original rates/Q, complete gates and isolated B8 decay."""
from pathlib import Path
from decimal import Decimal
import hashlib
import itertools
import json
import math
import sys
import traceback
import zipfile
import numpy as np
from scipy.optimize import brentq
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'output/is5-pp3-staging'))
import is5_pp3 as m
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    out=ROOT/'evidence/is5-pp3-foundation-20261026a.json'
    folder=ROOT/'output/is5-pp3-foundation-20261026a'
    if out.exists() or folder.exists():raise FileExistsError('Preserve foundation evidence')
    folder.mkdir();files=[ROOT/n for n in m.IMPORTED]+[Path(__file__),ROOT/'IS-5-PP-III-CONTRATO-PREVIO.md']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in files}
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
    r=dict(accepted=False,scientific_model_accepted=False,source_sha256=hashes,rate_checks=0,gate_checks=0,cases=[])
    try:
        assert m.NSPEC==13 and m.NCHAN==14 and m.NVAR==27
        assert np.array_equal(m.A@m.S,np.zeros(14)) and np.array_equal(m.Z@m.S+m.NU,np.zeros(14))
        q={c:Decimal(m.RATES[c]['Q_AME2020_decimal_MeV']) for c in m.CHANNELS}
        cycles=[2*q['pp']+2*q['dp']+q['he3he3'],sum(q[c] for c in ['pp','dp','he3alpha','be7ec','li7pa']),
                sum(q[c] for c in ['pp','dp','he3alpha','be7p','b8beta2a']),sum(q[c] for c in m.legacy.CHANNELS[3:])]
        target=(4*Decimal(m.DATA['nuclides']['p']['AME2020']['quantities']['mass_excess']['raw_value'])-Decimal(m.DATA['nuclides']['he4']['AME2020']['quantities']['mass_excess']['raw_value']))/1000
        assert all(v==target for v in cycles);r['four_Q_cycles_MeV']=str(target)
        for c in ('be7p','b8beta2a'):
            for t,ref in m.RATES[c]['reference_rates'].items():
                assert math.isclose(m.legacy.rate_value(float(t),m.RATES[c]),ref,rel_tol=1e-12);r['rate_checks']+=1
        for bits in itertools.product((False,True),repeat=3):
            a=dict(zip(('strong','weak','electromagnetic'),bits))
            for cb in itertools.product((False,True),repeat=14):
                switches=dict(zip(m.CHANNELS,cb));enabled=m.active_channels(a,switches)[2]
                assert enabled['be7p']==(a['strong'] and a['electromagnetic'] and switches['be7p'])
                assert enabled['b8beta2a']==(a['strong'] and a['weak'] and switches['b8beta2a'])
                assert {c:enabled[c] for c in m.previous.CHANNELS}==m.previous.active_channels(a,{c:switches[c] for c in m.previous.CHANNELS})[2]
                r['gate_checks']+=1
        j=m.CHANNELS.index('b8beta2a');b=m.SPECIES.index('b8');nb=1.5e5/m.atomic_mass
        initial=np.zeros(27);initial[0]=.5;initial[b]=1e-4/8;initial[3]=(1-.5-1e-4)/4
        p={**m.DEFAULT_PARAMETERS,'duration_s':20.,'hydrogen_fraction':.5,'catalyst_fraction':0.}
        switches={c:c=='b8beta2a' for c in m.CHANNELS}
        half=m.DATA['nuclides']['b8']['NUBASE2020']['half_life_s'];k=math.log(2)/half
        assert m.rate_constants(15e6,1.5e5,switches)[j]==k
        for mode in ('prescribed','isochoric_ideal'):
            result=m._integrate(p,None,switches,mode,'nubase2020',1e-10,initial)
            t=np.array(result['time_s']);parent=initial[b]*np.exp(-k*t);events=initial[b]*(-np.expm1(-k*t))
            y=np.tile(initial[:13],(len(t),1));y[:,b]=parent;y[:,3]+=2*events
            error=float(np.max(abs(np.array(result['number_per_baryon'])-y)));assert error<1e-12
            for field in ('produced_positrons_m3','annihilated_electrons_m3','neutrino_count_m3'):
                assert np.max(abs(np.array(result[field])-events*nb))/max(events*nb)<1e-8
            assert not any(result['captured_electrons_m3'])
            for field,qvalue in [('energy_available_J_m3',m.Q[j]),('energy_neutrinos_J_m3',m.QNU[j])]:
                assert np.max(abs(np.array(result[field])-events*nb*qvalue))/max(events*nb*qvalue)<1e-8
            terr=0.
            if mode=='isochoric_ideal':
                u0=m.eos.mixture(15e6,1.5e5,float(sum(initial[:13])),float(m.Z@initial[:13]))['internal_energy_J_m3']
                expected=[]
                for yi,e in zip(y,events):
                    target_u=u0+e*nb*(m.Q[j]-m.QNU[j])
                    expected.append(brentq(lambda temp:m.eos.mixture(float(temp),1.5e5,float(sum(yi)),float(m.Z@yi))['internal_energy_J_m3']-target_u,1e7,1.6e7,xtol=1e-6))
                terr=float(np.max(abs(np.array(expected)-result['temperature_K'])/np.array(expected)));assert terr<1e-7
            path=folder/(mode+'.json');path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
            r['cases'].append(dict(mode=mode,composition_absolute=error,temperature_relative=terr,path=path.relative_to(ROOT).as_posix(),sha256=sha(path)))
        assert all(sha(ROOT/n)==v for n,v in hashes.items())
        r.update(accepted=True,scope='Foundation only. Competition, mixed independent BDF/refinement, pp-II limit, Jacobian and refusals remain before scientific/worker/UI acceptance.')
    except Exception:r['failure']=traceback.format_exc()
    out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in r.items() if k!='source_sha256'}),flush=True)
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
