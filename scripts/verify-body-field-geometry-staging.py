"""Verify frozen magnetic geometry and native mesh serialization without a live renderer."""
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

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is3-tides-product/app'
STAGING=ROOT/'output/is3-body-vector-staging'
sys.path.insert(0,str(APP));sys.path.insert(0,str(STAGING))
from body_field_geometry import arrow,build,product
from body_field_scene import prepare

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
LIMITS={'direction_relative':1e-12,'length_relative':1e-12,'rotation_matrix':2e-14,
    'relative_point_render_m':.001,'float32_vertex_per_reference_radius':1e-6,'ellipsoid_equation':2e-14}


def euler_matrix(angles):
    x,y,z=angles;cx,sx=math.cos(x),math.sin(x);cy,sy=math.cos(y),math.sin(y);cz,sz=math.cos(z),math.sin(z)
    return np.array([[cz*cy,cz*sy*sx-sz*cx,cz*sy*cx+sz*sx],
        [sz*cy,sz*sy*sx+cz*cx,sz*sy*cx-cz*sx],[-sy,cy*sx,cy*cx]])


def parse_mesh(path):
    lines=path.read_text().splitlines();curves=[];i=0
    while i<len(lines):
        if lines[i].startswith('#'):i+=1;continue
        assert lines[i]=='mesh -c 1 {' and lines[i+1].startswith('id ')
        count=int(lines[i+2]);points=[[float(v) for v in line.split()] for line in lines[i+3:i+3+count]]
        assert len(points)==count and all(len(p)==3 for p in points) and lines[i+3+count]=='}'
        curves.append(points);i+=4+count
    return curves


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label.')
    folder=ROOT/('output/is3-body-field-geometry-check-'+args.label);receipt=ROOT/('evidence/is3-body-field-geometry-check-'+args.label+'.json')
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve evidence.')
    folder.mkdir()
    fixtures=[ROOT/'output/is3-earth-field-check-20261023a/all-field-readings.json',
        ROOT/'output/is3-jupiter-field-check-20261023a/all-readings.json']
    paths=[STAGING/'body_field_geometry.py',STAGING/'body_field_scene.py',APP/'body_attributes.py',
        ROOT/'IS-3-VETOR-NATIVO-CONTRATO.md',Path(__file__).resolve(),*fixtures]
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    with zipfile.ZipFile(folder/'executed-sources-and-fixtures.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in paths:z.write(p,p.relative_to(ROOT).as_posix())
    report={'schema':1,'source_sha256':hashes,'limits_before_execution':LIMITS,'checks':{},'completed':False,'accepted':False,
        'scope':'Pure geometry and mesh serialization of previously validated readings. No live scene/API/UI/performance or field-line acceptance; not linked into product.'}
    def persist():receipt.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    persist()
    try:
        worst_direction=worst_length=0.
        cases=[[1.,0.,0.],[0.,-2.,0.],[0.,0.,3.],[3.,4.,5.],[-3.,-4.,-5.],[1e-100,-2e-100,3e-100]]
        for field in cases:
            result=arrow([7.,-8.,9.],field,13.);tip=np.array(result['segments_m'][0][1]);tail=np.array(result['segments_m'][0][0])
            delta=tip-tail;direction=np.array(field)/np.linalg.norm(np.array(field))
            error=float(np.max(np.abs(delta/13.-direction)));worst_direction=max(worst_direction,error);assert error<=LIMITS['direction_relative']
            error=abs(float(np.linalg.norm(delta))/13.-1);worst_length=max(worst_length,error);assert error<=LIMITS['length_relative']
            assert np.dot(delta,np.array(field))>0
        assert arrow([0,0,0],[0,0,0],1)['drawn'] is False
        report['checks']['analytic_vectors_sign_length_direction_and_zero']={'cases':len(cases),'max_direction_error':worst_direction,'max_length_error':worst_length}
        readings=sum([json.loads(p.read_text(encoding='utf-8')) for p in fixtures],[])
        matrix_error=quantization=ellipsoid_error=0.;results=[]
        for reading in readings:
            before=copy.deepcopy(reading);code,result=prepare(reading);g,r=result['geometry'],result['render']
            assert reading==before and r['frame_position_render_m']==g['center_render_m']
            assert g['metadata']['epoch']==reading['epoch'] and g['metadata']['edit_token']==reading['edit_token']
            expected_field=product(g['body_to_render'],g['field_model_T'])
            assert max(abs(a-b) for a,b in zip(expected_field,reading['field_render_T']))<1e-18
            rotation=euler_matrix(r['model_to_render_rotation_euler_rad'])
            error=float(np.max(np.abs(rotation-np.array(g['body_to_render']))));matrix_error=max(matrix_error,error);assert error<=LIMITS['rotation_matrix']
            a,_,b=g['reference']['semiaxes_m']
            for curve in g['reference_curves_m']:
                for x,y,z in curve:
                    error=abs((x*x+y*y)/(a*a)+z*z/(b*b)-1);ellipsoid_error=max(ellipsoid_error,error);assert error<=LIMITS['ellipsoid_equation']
            expected_curves={'reference_grid':g['reference_curves_m'],'sample_point':g['point_cross_segments_m'],
                'magnetic_vector':g['arrow']['segments_m']}
            for mesh in r['meshes']:
                parsed=parse_mesh(Path(mesh['file']));expected=expected_curves[mesh['quantity']]
                assert len(parsed)==len(expected)==mesh['curves'] and sum(map(len,parsed))==mesh['vertices']
                for actual,wanted in zip(parsed,expected):
                    assert np.array_equal(np.array(actual),np.array(wanted)/a)
                error=mesh['float32_vertex_max_component_error_m']/a;quantization=max(quantization,error);assert error<=LIMITS['float32_vertex_per_reference_radius']
                assert sha(Path(mesh['file']))==mesh['file_sha256'] and sha(Path(mesh['names_file']))==mesh['names_sha256']
            view=g['view'];position=np.array(view['position_render_relative_m']);up=np.array(view['up_render'])
            assert abs(float(position@up)/np.linalg.norm(position))<1e-12 and abs(float(np.linalg.norm(up))-1)<1e-12
            assert view['distance_m']>3*max(a,math.hypot(*g['point_model_m']))
            assert code.count('openspace.addSceneGraphNode(')==len(r['nodes'])
            assert sha(Path(r['receipt']))==r['receipt_sha256']
            results.append({'model':g['model'],'reading_sha256':g['reading_sha256'],'render':r})
        report['checks']['validated_readings_to_frozen_meshes']={'cases':len(readings),'rotation_max_matrix_error':matrix_error,
            'float32_max_error_per_reference_radius':quantization,'ellipsoid_equation_max_error':ellipsoid_error,
            'phase_identity_input_unchanged_mesh_edges_and_camera_basis':True}
        refused=[]
        for label,point,field,length in [('bad_position',[True,0,0],[1,0,0],1),('bad_field',[0,0,0],[float('nan'),0,0],1),
            ('bad_norm',[0,0,0],[1.7e308]*3,1),('bad_length',[0,0,0],[1,0,0],-1)]:
            try:arrow(point,field,length)
            except ValueError:pass
            else:raise AssertionError(label)
            refused.append(label)
        for label,change in [('unknown_model',{'kind':'other'}),('bad_rotation',{'J2000_to_render':[[1,0,0],[0,1,0],[0,0,-1]]})]:
            try:build({**readings[0],**change})
            except ValueError:pass
            else:raise AssertionError(label)
            refused.append(label)
        report['checks']['refusals']=refused
        assert all(sha(ROOT/p)==h for p,h in hashes.items())
        (folder/'generated-mesh-index.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
        report['completed']=report['accepted']=True
    except Exception:report['failure']=traceback.format_exc()
    finally:persist()
    print(json.dumps({'receipt':receipt.relative_to(ROOT).as_posix(),'accepted':report['accepted'],'failure':report.get('failure'),'checks':report['checks']}))
    return 0 if report['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
