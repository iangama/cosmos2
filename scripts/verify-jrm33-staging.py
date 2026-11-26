"""JRM33 own evaluator versus pinned PSH and independent potential/dipole identities."""
from pathlib import Path
import argparse
import ast
import hashlib
import importlib.util
import itertools
import json
import math
import sys
import traceback
import zipfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'output/is3-jrm33-staging'
sys.path.insert(0,str(FOLDER))
import jrm33
LIMITS={'PSH_component_nT':1e-4,'potential_gradient_component_nT':1e-3,'dipole_relative':1e-13}


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def load_reference(degree,coordinates):
    name='jovian_jrm33_order'+str(degree)+'_internal_'+coordinates
    path=FOLDER/'upstream-PSH/Jupiter/Python'/(name+'.py')
    tree=ast.parse(path.read_text())
    assert all(isinstance(n,(ast.Import,ast.FunctionDef)) for n in tree.body)
    assert all(alias.name=='numpy' for n in tree.body if isinstance(n,ast.Import) for alias in n.names)
    for node in ast.walk(tree):
        assert not isinstance(node,(ast.ImportFrom,ast.Global,ast.Nonlocal))
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name):
            assert node.func.id not in ('open','exec','eval','compile','__import__')
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return getattr(module,name)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label.')
    folder=ROOT/('output/is3-jrm33-check-'+args.label);receipt=ROOT/('evidence/is3-jrm33-check-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve field evidence.')
    folder.mkdir()
    paths=sorted(p for p in FOLDER.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    paths += [Path(__file__).resolve(),ROOT/'IS-3-JRM33-CONTRATO.md']
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    archive=folder/'sources-reference-data-recipe.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in paths:z.write(p,p.relative_to(ROOT).as_posix())
    owner=ROOT/'user/sessions/latest.json';owner_before=sha(owner)
    report={'schema':1,'source_sha256':hashes,'archive_sha256':sha(archive),'limits_before_execution':LIMITS,
        'accepted':False,'checks':{},'scope':'Staged static internal model; independent code/identities use the same published coefficient family, not independent observations or scene integration.'}
    def persist():receipt.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    persist()
    try:
        results=[];worst=0.
        for degree in [13,18]:
            rtp=load_reference(degree,'rtp');xyz=load_reference(degree,'xyz')
            for radius,theta,phi in itertools.product([1.,1.5,2.5,10.],[0.,math.pi/6,math.pi/2,5*math.pi/6,math.pi],[0.,math.pi/2,math.pi,1.5*math.pi]):
                point=[radius*jrm33.R*math.sin(theta)*math.cos(phi),radius*jrm33.R*math.sin(theta)*math.sin(phi),radius*jrm33.R*math.cos(theta)]
                value=jrm33.sample(point,degree)
                expected=np.array(rtp(radius,theta,phi))[0]
                actual=np.array(jrm33.spherical(radius*jrm33.R,theta,phi,degree)[0])*1e9
                error=float(np.max(np.abs(actual-expected)));assert error<=LIMITS['PSH_component_nT'],(degree,radius,theta,phi,error)
                # Cartesian oracle gets precisely the same represented point.
                expected_xyz=np.array(xyz(*[v/jrm33.R for v in point]))[0]
                error_xyz=float(np.max(np.abs(np.array(value['field_SystemIII_T'])*1e9-expected_xyz)))
                assert error_xyz<=LIMITS['PSH_component_nT'],(degree,radius,theta,phi,error_xyz)
                worst=max(worst,error,error_xyz);results.append({'degree':degree,'r_Rj':radius,'theta_rad':theta,'east_phi_rad':phi,'spherical_error_nT':error,'Cartesian_error_nT':error_xyz})
        report['checks']['PSH160_cases']={'cases':len(results),'max_component_nT':worst}
        m=np.array([jrm33.COEFFICIENTS['g',1,1],jrm33.COEFFICIENTS['h',1,1],jrm33.COEFFICIENTS['g',1,0]])*1e-9
        errors=[]
        for direction in [[1.,0,0],[0,1.,0],[0,0,1.],[-1.,2.,-3.],[2.,-3.,1.]]:
            unit=np.array(direction)/np.linalg.norm(direction);point=unit*2*jrm33.R
            actual=np.array(jrm33.sample(point.tolist(),1)['field_SystemIII_T'])
            expected=(3*np.dot(m,unit)*unit-m)/8
            error=float(np.linalg.norm(actual-expected)/np.linalg.norm(expected));assert error<=LIMITS['dipole_relative'];errors.append(error)
            doubled=np.array(jrm33.sample((point*2).tolist(),1)['field_SystemIII_T'])
            assert np.allclose(doubled,actual/8,rtol=1e-13,atol=1e-20)
        report['checks']['analytic_degree1_and_inverse_cube']={'max_relative_error':max(errors)}
        gradients=[];step=1000.
        for point in [[1.1*jrm33.R,.2*jrm33.R,.3*jrm33.R],[-1.4*jrm33.R,.1*jrm33.R,-.5*jrm33.R],[2*jrm33.R,-3*jrm33.R,jrm33.R]]:
            for degree in [13,18]:
                expected=jrm33.sample(point,degree)['field_SystemIII_T'];estimated=[]
                for axis in range(3):
                    samples={}
                    for shift in [-2,-1,1,2]:
                        offset=list(point);offset[axis]+=shift*step;samples[shift]=jrm33.sample(offset,degree)['scalar_potential_T_m']
                    estimated.append((samples[2]-8*samples[1]+8*samples[-1]-samples[-2])/(12*step))
                error=max(abs(a-b)*1e9 for a,b in zip(expected,estimated));assert error<=LIMITS['potential_gradient_component_nT'],error;gradients.append(error)
        report['checks']['independent_five_point_potential_gradient']={'cases':len(gradients),'max_component_nT':max(gradients)}
        for sign in [-1,1]:
            vectors=[]
            for phi in [0.,.3,2.,5.,2*math.pi]:
                theta=0. if sign==1 else math.pi
                (br,bt,bp),_=jrm33.spherical(1.5*jrm33.R,theta,phi,13)
                s,c=math.sin(theta),math.cos(theta);cl,sl=math.cos(phi),math.sin(phi)
                vectors.append([(br*s+bt*c)*cl-bp*sl,(br*s+bt*c)*sl+bp*cl,br*c-bt*s])
            assert np.max(np.abs(np.array(vectors)-vectors[0]))*1e9<=LIMITS['PSH_component_nT']
        periodic_a=jrm33.spherical(2*jrm33.R,math.pi/3,0.,13)[0]
        periodic_b=jrm33.spherical(2*jrm33.R,math.pi/3,2*math.pi,13)[0]
        assert max(abs(a-b)*1e9 for a,b in zip(periodic_a,periodic_b))<=LIMITS['PSH_component_nT']
        report['checks']['pole_Cartesian_invariance_and_longitude_periodicity']=True
        refusals=[]
        for label,point,degree in [('zero',[0.,0,0],13),('inner',[.9*jrm33.R,0.,0],13),('outer',[21*jrm33.R,0.,0],13),
            ('bool',[True,0,0],13),('NaN',[float('nan'),0,0],13),('infinite',[float('inf'),0,0],13),
            ('missing',[1.,0],13),('degree30',[jrm33.R,0.,0],30),('bool_degree',[jrm33.R,0.,0],True)]:
            try:jrm33.sample(point,degree)
            except ValueError:pass
            else:raise AssertionError(label)
            refusals.append(label)
        report['checks']['domain_refusals']=refusals
        assert sha(owner)==owner_before and all(sha(ROOT/name)==digest for name,digest in hashes.items())
        result=folder/'all-PSH-comparisons.json';result.write_text(json.dumps(results,allow_nan=False)+'\n')
        report['comparisons_sha256']=sha(result);report['accepted']=True
    except Exception:report['failure']=traceback.format_exc()
    finally:persist()
    print(json.dumps({'receipt':receipt.relative_to(ROOT).as_posix(),'accepted':report['accepted'],'checks':report['checks'],'failure':report.get('failure')}))
    return 0 if report['accepted'] else 1

if __name__=='__main__':raise SystemExit(main())
