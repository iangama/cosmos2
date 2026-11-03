"""Compare emitted native CSV batches against every adopted immutable SI map cell."""
from pathlib import Path
import csv
import hashlib
import json
import sys
import traceback
import zipfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'output/is3-body-points-staging'),str(ROOT/'output/is3-body-maps-product/app')]
from body_field_points import batches
from body_field_geometry import build
from body_field_map_geometry import build as display,view
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    folder=ROOT/'output/is3-body-points-check-20261024a';receipt=ROOT/'evidence/is3-body-points-check-20261024a.json'
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve points evidence.')
    science=ROOT/'evidence/is3-body-maps-check-20261024a.json';prior=json.loads(science.read_text(encoding='utf-8'));assert prior['accepted']
    paths=[Path(__file__),ROOT/'output/is3-body-points-staging/body_field_points.py',science]
    paths.extend(ROOT/m['data']['path'] for m in prior['models'])
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in paths};folder.mkdir()
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in paths:z.write(p,p.relative_to(ROOT).as_posix())
    report={'schema':1,'accepted':False,'completed':False,'source_sha256':hashes,'cases':[]}
    try:
        for model in prior['models']:
            data=json.loads((ROOT/model['data']['path']).read_text(encoding='utf-8'))
            for kind in ['shell','cut']:
                case=folder/(data['model']+'-'+kind);case.mkdir()
                g=build(data['reading']);g['field_maps']=data;g['map_display']=display(data,kind);g['view']=view(data,g['map_display'])
                code,meshes=batches(g,case,'ProbeFrame','probe',[0.,0.,0.])
                assert 0<len(meshes)<=8
                assert code.count('Type="RenderablePointCloud"')==len(meshes) and 'ConstellationLines' not in code
                count=0;covered=set()
                for mesh in meshes:
                    assert sha(Path(mesh['file']))==mesh['file_sha256']
                    with Path(mesh['file']).open(newline='',encoding='utf-8') as f:rows=list(csv.DictReader(f))
                    values=np.array([[float(row[axis]) for axis in ['x','y','z']] for row in rows])
                    assert len(values)==len(mesh['cells'])==mesh['points']
                    expected=np.array([data[kind]['samples'][r][c]['position_model_m'] for r,c in mesh['cells']])/g['reference_radius_m']
                    assert np.array_equal(values,expected)
                    assert mesh['float32_vertex_max_component_error_m']<=1e-6*g['reference_radius_m']
                    for row,column in mesh['cells']:
                        assert (row,column) not in covered;covered.add((row,column))
                        sample=data[kind]['samples'][row][column];assert sample is not None
                        low,high=g['map_display']['minimum_sampled_T'],g['map_display']['maximum_sampled_T']
                        index=0 if high==low else min(7,int(8*(sample['field_norm_T']-low)/(high-low)))
                        assert mesh['color_rgb']==g['map_display']['palette_rgb'][index]
                    count+=len(rows)
                assert count==g['map_display']['drawn_symbols']
                assert count==614 if kind=='shell' else count==4225-data['cut']['masked_cells']
                report['cases'].append({'model':data['model'],'representation':kind,'points':count,'batches':len(meshes),
                    'exact_CSV_source_cells':True,'mask_bins_seam_preserved':True,'float32_bound_R':1e-6})
        assert all(sha(ROOT/name)==value for name,value in hashes.items())
        report.update(accepted=True,completed=True,scope='Every emitted normalized CSV point and color matches its immutable SI source cell. At most8 batches; masked domain absent, seam/poles deduplicated. Native point size/position/render, lifecycle, visuals and performance separate.')
    except Exception:report['failure']=traceback.format_exc()
    receipt.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'accepted':report['accepted'],'cases':len(report['cases']),'failure':report.get('failure')}))
    return 0 if report['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
