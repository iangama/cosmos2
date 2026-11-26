"""Reconstruct actual SM float32 vertices independently in SI, including offsets."""
from pathlib import Path
from copy import deepcopy
import hashlib
import json
import sys
import tempfile
import numpy as np
ROOT=Path(__file__).resolve().parents[1];STAGE=ROOT/'output/c212-em-potential-staging';sys.path.insert(0,str(STAGE))
from em_potential import contours
from em_potential_mesh import prepare_mesh
cases=[]
with tempfile.TemporaryDirectory(prefix='cosmos2-potential-mesh-') as temp:
    for trial,offset in enumerate((0.,1e9-3)):
        xs=[offset-2+i/8 for i in range(33)];ys=[offset-2+i/8 for i in range(33)];z=offset+.35
        grid={'x_m':xs,'y_m':ys,'z_m':z}
        m={'system_id':'reference','edit_token':'reference','revision':2,'time_s':1.25,'frame':'EM_SI_FIXED_INERTIAL',
           'samples':[{'position_m':[x,y,z],'valid':True,'electric_potential_V':3*(x-offset)-2*(y-offset)} for x in xs for y in ys]}
        geometry=contours(grid,m,[-1.,0.,1.],exclusions=[]);layer={'measurement':m,'geometry':geometry};before=deepcopy(layer)
        folder=Path(temp)/str(trial);prepared=prepare_mesh(layer,folder,enabled=False);assert layer==before and len(prepared['meshes'])==3
        worst=0.
        for mesh,node in zip(prepared['meshes'],prepared['nodes']):
            assert not node['Renderable']['Enabled'] and node['Parent']=='C2EMRoot'
            assert node['Transform']['Scale']['Scale']==mesh['local_unit_model_m']*1e9
            assert node['Transform']['Translation']['Position']==[x*1e9 for x in mesh['center_model_m']]
            rows=Path(mesh['file']).read_text().splitlines();actual=[]
            for i,row in enumerate(rows):
                if row.startswith('mesh '):
                    assert rows[i+2]=='2';actual.append(np.array([[float(v) for v in r.split()] for r in rows[i+3:i+5]],dtype=np.float32).astype(float))
            assert len(actual)==len(mesh['segment_indices']) and len(actual)*2==mesh['vertex_count']
            reconstructed=[p*mesh['local_unit_model_m']+mesh['center_model_m'] for p in actual]
            error=max(float(np.max(abs(p-np.array(geometry['segments'][index]['points_m'])))) for p,index in zip(reconstructed,mesh['segment_indices']))
            assert error==mesh['SI_reconstruction_component_error_m']
            assert all(np.all(p[:,2]==z) for p in reconstructed)
            assert mesh['float32_local_component_error_model_m']<=3e-7*mesh['local_unit_model_m'];worst=max(worst,error)
        cases.append({'offset_m':offset,'levels':3,'segments':len(geometry['segments']),'maximum_reconstruction_component_error_m':worst,'actual_slice_z_preserved':True})
        try:prepare_mesh(layer,folder)
        except ValueError:pass
        else:raise AssertionError('Existing mesh directory overwritten')
        bad=deepcopy(layer);bad['measurement']['time_s']+=1
        try:prepare_mesh(bad,Path(temp)/('bad'+str(trial)))
        except ValueError:pass
        else:raise AssertionError('Mismatched layer accepted')
report={'status':'isolated_native_potential_SM_preparation_and_independent_SI_reconstruction_verified','cases':cases,
        'stale_stamp_and_overwrite_refused':True,'science_layer_unchanged':True,
        'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (STAGE/'em_potential.py',STAGE/'em_potential_mesh.py',Path(__file__))},
        'scope':'Actual temporary SM files parsed and cast tofloat32, native node definitions only. No engine nodes/CEF/persistence or performance acceptance.'}
(ROOT/'evidence/em-potential-mesh-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
