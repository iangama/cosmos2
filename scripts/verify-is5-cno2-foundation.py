"""Cold-CNO-II fits/Q, control independence and isolated F17 analytic thermal decay."""
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
sys.path.insert(0,str(ROOT/'output/is5-cno2-staging'))
import is5_cno2 as m
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    out=ROOT/'evidence/is5-cno2-foundation-20261027a.json'
    folder=ROOT/'output/is5-cno2-foundation-20261027a'
    if out.exists() or folder.exists():raise FileExistsError('Preserve foundation evidence')
    folder.mkdir();files=[ROOT/n for n in m.IMPORTED]+[Path(__file__),ROOT/'IS-5-CNO-II-CONTRATO-PREVIO.md']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in files}
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for n in hashes:z.write(ROOT/n,n)
    r=dict(accepted=False,scientific_model_accepted=False,source_sha256=hashes,rate_checks=0,gate_checks=0,cases=[])
    try:
        assert m.NSPEC==16 and m.NCHAN==18 and m.NVAR==34
        assert np.array_equal(m.A@m.S,np.zeros(18)) and np.array_equal(m.Z@m.S+m.NU,np.zeros(18))
        q={c:Decimal(m.RATES[c]['Q_AME2020_decimal_MeV']) for c in m.CHANNELS}
        cycles=[2*q['pp']+2*q['dp']+q['he3he3'],sum(q[c] for c in ['pp','dp','he3alpha','be7ec','li7pa']),
                sum(q[c] for c in ['pp','dp','he3alpha','be7p','b8beta2a']),sum(q[c] for c in m.legacy.CHANNELS[3:]),sum(q[c] for c in ['n14pg','o15beta','n15pg','o16pg','f17beta','o17pa'])]
        target=(4*Decimal(m.DATA['nuclides']['p']['AME2020']['quantities']['mass_excess']['raw_value'])-Decimal(m.DATA['nuclides']['he4']['AME2020']['quantities']['mass_excess']['raw_value']))/1000
        assert all(v==target for v in cycles);r['five_Q_cycles_MeV']=str(target)
        for c in ('n15pg','o16pg','f17beta','o17pa'):
            for t,ref in m.RATES[c]['reference_rates'].items():
                assert math.isclose(m.legacy.rate_value(float(t),m.RATES[c]),ref,rel_tol=1e-12);r['rate_checks']+=1
        catalytic=np.zeros(16);catalytic[m.CATALYST_INDICES]=1
        assert np.array_equal(catalytic@m.S,np.zeros(18))
        added=('n15pg','o16pg','f17beta','o17pa')
        for bits in itertools.product((False,True),repeat=3):
            a=dict(zip(('strong','weak','electromagnetic'),bits))
            for cb in itertools.product((False,True),repeat=4):
                switches={c:True for c in m.CHANNELS};switches.update(zip(added,cb));enabled=m.active_channels(a,switches)[2]
                for c in ('n15pg','o16pg'):assert enabled[c]==(a['strong'] and a['electromagnetic'] and switches[c])
                assert enabled['f17beta']==(a['weak'] and switches['f17beta'])
                assert enabled['o17pa']==(a['strong'] and switches['o17pa'])
                r['gate_checks']+=1
            all_on=m.active_channels(a,None)[2]
            for c in m.CHANNELS:
                switches={n:n!=c for n in m.CHANNELS};one_off=m.active_channels(a,switches)[2]
                assert not one_off[c] and all(one_off[n]==all_on[n] for n in m.CHANNELS if n!=c)
        j=m.CHANNELS.index('f17beta');b=m.SPECIES.index('f17');daughter=m.SPECIES.index('o17');nb=1.5e5/m.atomic_mass
        initial=np.zeros(34);initial[0]=.5;initial[b]=1e-4/17;initial[3]=(1-.5-1e-4)/4
        half=m.DATA['nuclides']['f17']['NUBASE2020']['half_life_s'];k=math.log(2)/half
        p={**m.DEFAULT_PARAMETERS,'duration_s':float(20*half),'hydrogen_fraction':.5,'catalyst_fraction':0.}
        switches={c:c=='f17beta' for c in m.CHANNELS}
        assert m.rate_constants(15e6,1.5e5,switches)[j]==k
        assert math.isclose(m.rate_constants(15e6,1.5e5,switches,'reaclib_wc12')[j],m.legacy.rate_value(15e6,m.RATES['f17beta']),rel_tol=1e-12)
        for mode in ('prescribed','isochoric_ideal'):
            result=m._integrate(p,None,switches,mode,'nubase2020',1e-10,initial)
            t=np.array(result['time_s']);parent=initial[b]*np.exp(-k*t);events=initial[b]*(-np.expm1(-k*t))
            y=np.tile(initial[:16],(len(t),1));y[:,b]=parent;y[:,daughter]+=events
            error=float(np.max(abs(np.array(result['number_per_baryon'])-y)));assert error<1e-12
            for field in ('produced_positrons_m3','annihilated_electrons_m3','neutrino_count_m3'):
                assert np.max(abs(np.array(result[field])-events*nb))/max(events*nb)<1e-8
            assert not any(result['captured_electrons_m3'])
            for field,qvalue in [('energy_available_J_m3',m.Q[j]),('energy_neutrinos_J_m3',m.QNU[j])]:
                assert np.max(abs(np.array(result[field])-events*nb*qvalue))/max(events*nb*qvalue)<1e-8
            terr=0.
            if mode=='isochoric_ideal':
                u0=m.eos.mixture(15e6,1.5e5,float(sum(initial[:16])),float(m.Z@initial[:16]))['internal_energy_J_m3']
                expected=[]
                for yi,e in zip(y,events):
                    target_u=u0+e*nb*(m.Q[j]-m.QNU[j])
                    expected.append(brentq(lambda temp:m.eos.mixture(float(temp),1.5e5,float(sum(yi)),float(m.Z@yi))['internal_energy_J_m3']-target_u,1e7,1.6e7,xtol=1e-6))
                terr=float(np.max(abs(np.array(expected)-result['temperature_K'])/np.array(expected)));assert terr<1e-7
            path=folder/(mode+'.json');path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
            r['cases'].append(dict(mode=mode,composition_absolute=error,temperature_relative=terr,path=path.relative_to(ROOT).as_posix(),sha256=sha(path)))
        assert all(sha(ROOT/n)==v for n,v in hashes.items())
        r.update(accepted=True,scope='Foundation only. Competition, mixed independent BDF/refinement, pp-III limit, Jacobian and refusals remain before scientific/worker/UI acceptance.')
    except Exception:r['failure']=traceback.format_exc()
    out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in r.items() if k!='source_sha256'}),flush=True)
    return 0 if r['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
