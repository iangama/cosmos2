"""Independent two-extent Be7 competition with evolving H and electron fraction."""
from pathlib import Path
import hashlib,json,sys,traceback,zipfile
import numpy as np
from scipy.integrate import solve_ivp
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'output/is5-pp3-staging'))
import is5_pp3 as m
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
 out=ROOT/'evidence/is5-pp3-competition-20261026a.json';folder=ROOT/'output/is5-pp3-competition-20261026a'
 if out.exists() or folder.exists():raise FileExistsError('Preserve competition')
 folder.mkdir();files=[ROOT/n for n in m.IMPORTED]+[Path(__file__),ROOT/'IS-5-PP-III-CONTRATO-PREVIO.md']
 hashes={p.relative_to(ROOT).as_posix():sha(p) for p in files}
 with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
  for n in hashes:z.write(ROOT/n,n)
 r=dict(accepted=False,scientific_model_accepted=False,source_sha256=hashes,refusals=0)
 try:
  x=np.full(13,.01);x[0]=.4;x[3]=.49;x/=sum(x);y=np.r_[x/m.A,np.zeros(14)]
  k=m.rate_constants(15e6,1.5e5);jac=m.flux_jacobian(y,k);errors=[]
  for i in range(13):
   delta=y[i]*1e-5;plus=y.copy();minus=y.copy();plus[i]+=delta;minus[i]-=delta
   numeric=(m.flux(plus,k)-m.flux(minus,k))/(2*delta);nz=abs(jac[:,i])>1e-50
   errors.append(float(np.max(abs(numeric[nz]-jac[nz,i])/abs(jac[nz,i]))))
  assert max(errors)<2e-7;r['jacobian_relative_max']=max(errors)
  initial=np.zeros(27);initial[0]=.5;initial[3]=.48/4;initial[10]=.02/7
  ye0=float(m.Z@initial[:13]);be0=float(initial[10]);h0=.5
  switches={c:c in ('be7ec','be7p') for c in m.CHANNELS}
  kec=k[m.CHANNELS.index('be7ec')];kp=k[m.CHANNELS.index('be7p')]
  duration=float(12/(kec*ye0));p={**m.DEFAULT_PARAMETERS,'duration_s':duration,'hydrogen_fraction':.5,'catalyst_fraction':0.}
  result=m._integrate(p,None,switches,'prescribed','nubase2020',1e-10,initial)
  def rhs(t,e):
   li,b8=e;be=be0-li-b8
   return [kec*(ye0-li)*be,kp*(h0-b8)*be]
  sol=solve_ivp(rhs,[0,duration],[0.,0.],method='BDF',t_eval=result['time_s'],rtol=1e-11,atol=1e-16)
  assert sol.success
  expected=np.tile(initial[:13],(241,1));li,b8=sol.y
  expected[:,0]=h0-b8;expected[:,10]=be0-li-b8;expected[:,11]=li;expected[:,12]=b8
  error=float(np.max(abs(np.array(result['number_per_baryon'])-expected)));assert error<1e-8
  assert li[-1]>0 and b8[-1]>0 and expected[-1,0]<h0 and float(expected[-1]@m.Z)<ye0
  r.update(competition_absolute_per_baryon=error,final_EC_fraction=float(li[-1]/(li[-1]+b8[-1])))
  (folder/'calculated.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
  for change in [dict(temperature_K=1e7),dict(temperature_K=16e6),dict(temperature_K=True),dict(duration_s=0),dict(density_kg_m3=float('nan'))]:
   try:m.integrate_zone({**m.DEFAULT_PARAMETERS,**change})
   except ValueError:r['refusals']+=1
   else:raise AssertionError('Invalid request accepted')
  try:m.integrate_zone({**m.DEFAULT_PARAMETERS,'duration_s':1e6*31557600.},mode='isochoric_ideal')
  except ValueError:r['refusals']+=1
  else:raise AssertionError('Thermal domain exceeded without whole-run refusal')
  assert all(sha(ROOT/n)==v for n,v in hashes.items())
  r.update(accepted=True,scope='Competition/Jacobian/refusals only; aggregate with foundation and mixed receipts after source hashes agree. No worker/UI acceptance.')
 except Exception:r['failure']=traceback.format_exc()
 out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in r.items() if k!='source_sha256'}),flush=True)
 return 0 if r['accepted'] else 1
if __name__=='__main__':raise SystemExit(main())
