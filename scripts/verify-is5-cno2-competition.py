"""Finite-fuel N15 branching, sixteen-species Jacobian and closed CNO-II route."""
from pathlib import Path
import hashlib,json,math,sys,traceback,zipfile
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'output/is5-cno2-staging'))
import is5_cno2 as m
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
 out=ROOT/'evidence/is5-cno2-competition-20261027a.json';folder=ROOT/'output/is5-cno2-competition-20261027a'
 if out.exists() or folder.exists():raise FileExistsError('Preserve CNO-II competition')
 folder.mkdir();files=[ROOT/n for n in m.IMPORTED]+[Path(__file__),ROOT/'IS-5-CNO-II-CONTRATO-PREVIO.md']
 hashes={p.relative_to(ROOT).as_posix():sha(p) for p in files}
 with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
  for n in hashes:z.write(ROOT/n,n)
 r=dict(accepted=False,scientific_model_accepted=False,source_sha256=hashes,refusals=0)
 try:
  x=np.full(16,.01);x[0]=.4;x[3]=.4;x/=sum(x);y=np.r_[x/m.A,np.zeros(18)]
  k=m.rate_constants(15e6,1.5e5);jac=m.flux_jacobian(y,k);errors=[]
  for i in range(16):
   delta=y[i]*1e-5;plus=y.copy();minus=y.copy();plus[i]+=delta;minus[i]-=delta
   numeric=(m.flux(plus,k)-m.flux(minus,k))/(2*delta);nz=abs(jac[:,i])>1e-50
   errors.append(float(np.max(abs(numeric[nz]-jac[nz,i])/abs(jac[nz,i]))))
  assert max(errors)<2e-7;r['jacobian_relative_max']=max(errors)
  initial=np.zeros(34);initial[0]=.5;initial[3]=.48/4;initial[m.SPECIES.index('n15')]=.02/15
  ka=k[m.CHANNELS.index('n15pa')];kg=k[m.CHANNELS.index('n15pg')];total=ka+kg
  b0=float(initial[m.SPECIES.index('n15')]);a=.5-b0
  p={**m.DEFAULT_PARAMETERS,'duration_s':float(12/(total*.5)),'hydrogen_fraction':.5,'catalyst_fraction':0.}
  switches={c:c in ('n15pa','n15pg') for c in m.CHANNELS}
  result=m._integrate(p,None,switches,'prescribed','nubase2020',1e-10,initial)
  t=np.array(result['time_s']);ex=np.exp(-a*total*t);parent=a*b0*ex/(a+b0*(-np.expm1(-a*total*t)))
  extent=b0-parent;alpha=extent*ka/total;gamma=extent*kg/total
  expected=np.tile(initial[:16],(241,1));expected[:,0]=a+parent;expected[:,m.SPECIES.index('n15')]=parent
  expected[:,3]+=alpha;expected[:,m.SPECIES.index('c12')]+=alpha;expected[:,m.SPECIES.index('o16')]+=gamma
  error=float(np.max(abs(np.array(result['number_per_baryon'])-expected)));assert error<1e-10
  nb=p['density_kg_m3']/m.atomic_mass
  for c,events in [('n15pa',alpha),('n15pg',gamma)]:
   measured=np.array(result['reaction_extents_m3'])[:,m.CHANNELS.index(c)]/nb
   assert np.max(abs(measured-events))<1e-10
  assert not any(result['neutrino_count_m3'])
  r.update(competition_absolute_per_baryon=error,gamma_fraction_from_fits=float(kg/total))
  (folder/'branching.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
  route=('n14pg','o15beta','n15pg','o16pg','f17beta','o17pa')
  p={**m.DEFAULT_PARAMETERS,'catalyst_seed':'o16','duration_s':1e8*31557600.}
  result=m.integrate_zone(p,channel_switches={c:c in route for c in m.CHANNELS})
  assert all(result['reaction_extents_m3'][-1][m.CHANNELS.index(c)]>0 for c in route)
  assert result['conservation']['catalyst_number_relative_error']<1e-8
  r['closed_route_conservation']=result['conservation']
  (folder/'closed-route.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
  for change in [dict(temperature_K=1e7),dict(temperature_K=16e6),dict(temperature_K=True),dict(duration_s=0),dict(density_kg_m3=float('nan')),dict(catalyst_seed='o18')]:
   try:m.integrate_zone({**m.DEFAULT_PARAMETERS,**change})
   except ValueError:r['refusals']+=1
   else:raise AssertionError('Invalid request accepted')
  try:m.integrate_zone({**m.DEFAULT_PARAMETERS,'duration_s':1e6*31557600.},mode='isochoric_ideal')
  except ValueError:r['refusals']+=1
  else:raise AssertionError('Thermal domain exceeded without whole-run refusal')
  assert all(sha(ROOT/n)==v for n,v in hashes.items())
  r.update(accepted=True,scope='CNO-II branching/Jacobian/closed route/refusals only; aggregate with foundation/mixed after common-source verification.')
 except Exception:r['failure']=traceback.format_exc()
 out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in r.items() if k!='source_sha256'}),flush=True)
 return 0 if r['accepted'] else 1
if __name__=='__main__':raise SystemExit(main())
