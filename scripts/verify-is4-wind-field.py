"""Independent spherical fields, differential identities, potential, domains and SI frame."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import math
import sys
import traceback
import zipfile
import numpy as np
from scipy.integrate import quad

ROOT=Path(__file__).resolve().parents[1];STAGE=ROOT/'output/is4-solar-wind-staging';APP=ROOT/'output/is4-body-particle-product0.8.1/app'
sys.path[:0]=[str(STAGE),str(APP)]
from is4_wind_field import Parker,DEFAULT,AU_M,INNER_M,OUTER_M
from is4_wind_snapshot import Snapshot
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def point(r,lat,lon):
    if abs(lat)==90.:return np.array([0.,0.,math.copysign(r,lat)])
    a,l=math.radians(lat),math.radians(lon)
    return np.array([r*math.cos(a)*math.cos(l),r*math.cos(a)*math.sin(l),r*math.sin(a)])

def main():
    p=argparse.ArgumentParser();p.add_argument('--label',required=True);args=p.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):p.error('Invalid label')
    folder=ROOT/('output/is4-wind-field-'+args.label);receipt=ROOT/('evidence/is4-wind-field-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve wind evidence')
    folder.mkdir();fixture=ROOT/'output/is4-body-snapshot-20261025b/IGRF14-13.json';phase=json.loads(fixture.read_text(encoding='utf-8'))['phase']
    files=[p for p in APP.rglob('*') if p.is_file() and '__pycache__' not in p.parts]+[p for p in STAGE.iterdir() if p.is_file()]+[Path(__file__),fixture,ROOT/'IS-4-VENTO-SOLAR-CONTRATO-PREVIO.md']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in files};owner=sha(ROOT/'user/sessions/latest.json')
    with zipfile.ZipFile(folder/'executed-sources-and-fixture.zip','w',zipfile.ZIP_DEFLATED) as z:
        for file in files:z.write(file,file.relative_to(ROOT).as_posix())
    report=dict(schema=1,accepted=False,completed=False,source_sha256=hashes,checks=[])
    try:
        maximum=dict(B_absolute_T=0.,E_absolute_V_m=0.,divB_normalized=0.,curlE_normalized=0.,gravity_absolute_m_s2=0.)
        samples=0;refusals=0
        for polarity in [1,-1]:
            cfg={**DEFAULT,'polarity':polarity};old=copy.deepcopy(cfg);f=Parker(cfg);model=Snapshot(phase,cfg);description=model.descriptor
            assert cfg==old
            rotation=np.array(description['model_to_J2000']);assert np.allclose(rotation.T@rotation,np.eye(3),rtol=0,atol=2e-15) and abs(np.linalg.det(rotation)-1)<2e-15
            sun=next(b for b in phase['bodies'] if b['reference_id']=='sol:naif:10')
            centers=[(np.array(b['position'])-sun['position'])*phase['physical_scale']['length_unit_m'] for b in phase['bodies']]
            gms=[b['mass']*phase['physical_scale']['nominal_GM_unit_m3_s2'] for b in phase['bodies']]
            for lat in [-90.,-60.,-10.,10.,30.,90.]:
                for lon in [-150.,0.,90.]:
                    for radius in [.1001,1.,5.,9.999]:
                        x=point(radius*AU_M,lat,lon);r=np.linalg.norm(x);theta=math.radians(90-lat);phi=math.radians(lon)
                        st=0. if abs(lat)==90. else math.sin(theta)
                        er=np.array([st*math.cos(phi),st*math.sin(phi),math.cos(theta)])
                        et=np.array([math.cos(theta)*math.cos(phi),math.cos(theta)*math.sin(phi),-math.sin(theta)])
                        ep=np.array([-math.sin(phi),math.cos(phi),0.]);sign=polarity*(1 if lat>0 else -1)
                        br=sign*cfg['radial_field_at_AU_T']*(AU_M/r)**2;bp=-br*cfg['rotation_rate_rad_s']*r*st/cfg['wind_speed_m_s']
                        b=br*er+bp*ep;e=cfg['wind_speed_m_s']*bp*et;actual=f.evaluate(x.tolist())
                        assert np.linalg.norm(np.array(actual['magnetic_field_T'])-b)<=3e-14*np.linalg.norm(b)+1e-24,(lat,lon,radius)
                        assert np.linalg.norm(np.array(actual['electric_field_V_m'])-e)<=3e-14*np.linalg.norm(e)+1e-18
                        assert np.linalg.norm(np.array(actual['electric_field_V_m'])+np.cross(actual['wind_velocity_m_s'],actual['magnetic_field_T']))<=3e-14*np.linalg.norm(e)+1e-18
                        normb=np.linalg.norm(b);norme=np.linalg.norm(e)
                        assert abs(np.dot(actual['electric_field_V_m'],actual['magnetic_field_T']))<=3e-14*normb*norme+1e-40
                        h=1e-5*r;db=np.empty((3,3));de=np.empty((3,3))
                        for k in range(3):
                            step=np.eye(3)[k]*h;left=f.evaluate((x-step).tolist());right=f.evaluate((x+step).tolist())
                            db[:,k]=(np.array(right['magnetic_field_T'])-left['magnetic_field_T'])/(2*h)
                            de[:,k]=(np.array(right['electric_field_V_m'])-left['electric_field_V_m'])/(2*h)
                        div=abs(np.trace(db))*r/normb
                        # At poles E=0; use the natural rotational field scale.
                        curl=np.linalg.norm([de[2,1]-de[1,2],de[0,2]-de[2,0],de[1,0]-de[0,1]])*r/max(norme,cfg['rotation_rate_rad_s']*cfg['radial_field_at_AU_T']*AU_M**2/r)
                        assert div<=2e-8 and curl<=2e-8,(lat,lon,radius,div,curl)
                        maximum['B_absolute_T']=max(maximum['B_absolute_T'],float(np.max(abs(np.array(actual['magnetic_field_T'])-b))))
                        maximum['E_absolute_V_m']=max(maximum['E_absolute_V_m'],float(np.max(abs(np.array(actual['electric_field_V_m'])-e))))
                        maximum['divB_normalized']=max(maximum['divB_normalized'],float(div));maximum['curlE_normalized']=max(maximum['curlE_normalized'],float(curl))
                        a=model.evaluate(x.tolist());inertial=rotation@x;deltas=[inertial-c for c in centers]
                        g=rotation.T@sum((-gm*d/np.linalg.norm(d)**3 for gm,d in zip(gms,deltas)),np.zeros(3))
                        assert np.allclose(a['gravity_m_s2'],g,rtol=2e-13,atol=1e-12)
                        maximum['gravity_absolute_m_s2']=max(maximum['gravity_absolute_m_s2'],float(np.max(abs(g-a['gravity_m_s2']))));samples+=1
            for lat in [-60.,-10.,10.,60.]:
                start=point(AU_M,lat,30.);end=start+np.array([.01,.005,.003 if lat>0 else -.003])*AU_M;delta=end-start
                integral=quad(lambda t:float(np.dot(f.evaluate((start+t*delta).tolist())['electric_field_V_m'],delta)),0,1,epsabs=1e-8,epsrel=1e-12)[0]
                potential=f.electric_potential_difference(start.tolist(),end.tolist())
                charge=1.602176634e-19;assert abs(charge*(integral+potential))<=1e-10*abs(charge*integral)+1e-24
            invalid=[[0.,0.,0.],[0.,0.,INNER_M*.999],[0.,0.,OUTER_M*1.001],[AU_M,0.,0.]]
            for x in invalid:
                before=f.evaluations
                try:f.evaluate(x)
                except ValueError:refusals+=1
                else:raise AssertionError('Invalid point accepted')
                assert f.evaluations==before
            assert not f.segment_in_domain((np.array([1.,0.,.09])*AU_M).tolist(),(np.array([-1.,0.,.09])*AU_M).tolist())
            assert not f.segment_in_domain((np.array([1.,0.,.2])*AU_M).tolist(),(np.array([1.,0.,-.2])*AU_M).tolist())
            assert f.segment_in_domain((np.array([1.,0.,.2])*AU_M).tolist(),(np.array([1.,.1,.3])*AU_M).tolist())
            description['model_to_J2000'][0][0]=100.;description['field']['parameters']['polarity']=100
            assert model.descriptor!=description and model.descriptor['field']['parameters']==cfg
            for s in model.sources:
                before=model.magnetic_evaluations
                assert not model.segment_in_domain(s.position_model_m,s.position_model_m)
                try:model.evaluate(s.position_model_m)
                except ValueError:refusals+=1
                else:raise AssertionError('Source exclusion accepted')
                assert model.magnetic_evaluations==before
        for patch in [{'polarity':True},{'polarity':0},{'wind_speed_m_s':True},{'wind_speed_m_s':9999.},{'radial_field_at_AU_T':float('nan')},{'rotation_rate_rad_s':float('inf')},{'rotation_rate_rad_s':-1.},{'extra':0}]:
            try:Parker({**DEFAULT,**patch})
            except ValueError:refusals+=1
            else:raise AssertionError(patch)
        for patch in [{'paused':False},{'time':True},{'revision':True},{'fixture_sha256':'bad'},{'edit_token':'bad'},{'gravity_effects':{'unsupported':True}},{'physical_scale':{}},{'bodies':phase['bodies'][:-1]}]:
            bad={**copy.deepcopy(phase),**patch};before=copy.deepcopy(bad)
            try:Snapshot(bad)
            except (ValueError,TypeError):refusals+=1
            else:raise AssertionError(patch)
            assert bad==before
        assert all(sha(ROOT/n)==v for n,v in hashes.items()) and sha(ROOT/'user/sessions/latest.json')==owner
        report.update(accepted=True,completed=True,samples=samples,refusals=refusals,maximum_errors=maximum,checks=['Independent spherical SI formulas and both polarities','E=-u cross B and E dot B=0','Divergence B/curl E away from masked HCS','Electric work via independent quadrature and stable potential differences','SPICE frozen solar axes plus independent J2000 gravity','Domain/parameter/source refusals before field queries; inputs and descriptors isolated'])
    except Exception:report['failure']=traceback.format_exc()
    receipt.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k!='source_sha256'},ensure_ascii=False))
    return 0 if report['accepted'] else 1

if __name__=='__main__':raise SystemExit(main())
