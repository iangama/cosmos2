from pathlib import Path
from collections import Counter
import hashlib,json,math,sys,traceback,zipfile
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'output/is5-pp3-staging'))
import is5_pp3 as m
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def independent(p,acting,switches,mode,times):
    a,c,enabled=m.active_channels(acting,switches)
    initial=m.initial_state(p);nb=p['density_kg_m3']/m.atomic_mass
    own=np.array([[Counter(m.RATES[c]['products'])[n]-Counter(m.RATES[c]['reactants'])[n] for c in m.CHANNELS] for n in m.SPECIES],dtype=float)
    reactants=[Counter(m.RATES[c]['reactants']) for c in m.CHANNELS]
    u0=m.eos.mixture(p['temperature_K'],p['density_kg_m3'],float(np.sum(initial[:13])),float(m.Z@initial[:13]))['internal_energy_J_m3']
    def temperature(y):
        if mode=='prescribed':return p['temperature_K']
        target=float(y[-1]*u0);yi=float(np.sum(y[:13]));ye=float(m.Z@y[:13])
        return brentq(lambda t:m.eos.mixture(float(t),p['density_kg_m3'],yi,ye)['internal_energy_J_m3']-target,1e7,1.6e7,xtol=2e-6,rtol=2e-14)
    def rhs(t,y):
        T=temperature(y);k=m.rate_constants(float(T),p['density_kg_m3'],enabled)
        f=np.array([k[j]*math.prod(y[m.SPECIES.index(n)]**count for n,count in r.items()) for j,r in enumerate(reactants)])
        f[m.CHANNELS.index('be7ec')]*=float(m.Z@y[:13])
        out=np.r_[own@f,f]
        return out if mode=='prescribed' else np.r_[out,nb*float((m.Q-m.QNU)@f)/u0]
    sol=solve_ivp(rhs,[0,p['duration_s']],initial if mode=='prescribed' else np.r_[initial,1.],method='BDF',t_eval=times,rtol=2e-10,atol=m.ATOL+([] if mode=='prescribed' else [1e-12]))
    assert sol.success,sol.message
    states=sol.y.T
    return dict(number_per_baryon=states[:,:13],extents_per_baryon=states[:,13:27],temperature_K=np.array([temperature(y) for y in states]))


def main():
 out=ROOT/'evidence/is5-pp3-mixed-20261026a.json';folder=ROOT/'output/is5-pp3-mixed-20261026a'
 if out.exists() or folder.exists():raise FileExistsError('Preserve ppIII mixed evidence')
 folder.mkdir();files=[ROOT/n for n in m.IMPORTED]+[Path(__file__),ROOT/'IS-5-PP-III-CONTRATO-PREVIO.md']
 hashes={p.relative_to(ROOT).as_posix():sha(p) for p in files}
 with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
  for n in hashes:z.write(ROOT/n,n)
 r=dict(accepted=False,scientific_model_accepted=False,source_sha256=hashes,cases=[])
 try:
  for mode in ('prescribed','isochoric_ideal'):
   p=dict(m.DEFAULT_PARAMETERS);result=m.integrate_zone(p,mode=mode)
   ref=independent(p,None,None,mode,result['time_s']);pop=np.array(result['number_per_baryon']);nb=p['density_kg_m3']/m.atomic_mass
   err=float(np.max(abs(ref['number_per_baryon']-pop)));exterr=float(np.max(abs(ref['extents_per_baryon']-np.array(result['reaction_extents_m3'])/nb)))
   terr=float(np.max(abs(ref['temperature_K']-result['temperature_K'])/np.array(result['temperature_K'])))
   assert err<=1e-8 and exterr<=1e-8 and terr<=1e-7,(err,exterr,terr)
   refined=m.integrate_zone(p,mode=mode,tolerance=1e-10)
   delta=float(np.max(abs(np.array(refined['number_per_baryon'])-pop)));assert delta<=1e-8
   switches={c:c in m.previous.CHANNELS for c in m.CHANNELS}
   limit=m.integrate_zone(p,channel_switches=switches,mode=mode);old=m.previous.integrate_zone(p,mode=mode)
   le=float(np.max(abs(np.array(limit['number_per_baryon'])[:,:12]-old['number_per_baryon'])))
   lt=float(np.max(abs(np.array(limit['temperature_K'])-old['temperature_K'])/np.array(old['temperature_K'])))
   assert le<=1e-8 and lt<=1e-7
   for name,value in [('result',result),('refined',refined),('limit',limit)]:
    path=folder/(mode+'-'+name+'.json');path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
   r['cases'].append(dict(mode=mode,BDF_composition_absolute=err,BDF_extents_absolute=exterr,BDF_temperature_relative=terr,refinement_composition_absolute=delta,ppII_limit_composition_absolute=le,ppII_limit_temperature_relative=lt))
   print(json.dumps(r['cases'][-1]),flush=True)
  assert all(sha(ROOT/n)==v for n,v in hashes.items())
  r.update(accepted=True,scope='Mixed BDF energy-inversion and ppII limit only; competition stress/Jacobian/refusals pending before full science acceptance.')
 except Exception:r['failure']=traceback.format_exc()
 out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in r.items() if k!='source_sha256'}),flush=True)
 return 0 if r['accepted'] else 1
if __name__=='__main__':raise SystemExit(main())
