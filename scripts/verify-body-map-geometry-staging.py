"""Check discrete map colors, glyph quantization, seam handling and cut camera axes."""
from pathlib import Path
import copy
import hashlib
import json
import sys
import traceback
import zipfile

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'output/is3-body-maps-staging'
APP=ROOT/'output/is3-body-view-topology-product/app'
sys.path[:0]=[str(STAGE),str(APP)]
import numpy as np
import body_field_map_geometry as display

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    folder=ROOT/'output/is3-map-geometry-check-20261024a';receipt=ROOT/'evidence/is3-map-geometry-check-20261024a.json'
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve geometry evidence.')
    science=ROOT/'evidence/is3-body-maps-check-20261024a.json';prior=json.loads(science.read_text(encoding='utf-8'));assert prior['accepted']
    paths=[STAGE/'body_field_map_geometry.py',Path(__file__).resolve(),ROOT/'IS-3-MAPAS-NATIVOS-CONTRATO.md',science]
    paths += [ROOT/model['data']['path'] for model in prior['models']]
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in paths};folder.mkdir()
    with zipfile.ZipFile(folder/'executed-sources.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for p in paths:archive.write(p,p.relative_to(ROOT).as_posix())
    report={'schema':1,'accepted':False,'completed':False,'source_sha256':hashes,'cases':[]}
    try:
        for model in prior['models']:
            data=json.loads((ROOT/model['data']['path']).read_text(encoding='utf-8'))
            for kind in ['shell','cut']:
                geometry=display.build(data,kind);radius=geometry['reference_radius_m']
                cells=[cell for item in geometry['bins'] for cell in item['cells']]
                assert len(cells)==len({tuple(cell) for cell in cells})==geometry['drawn_symbols']
                if kind=='shell':assert len(cells)==614
                else:assert len(cells)==65*65-data['cut']['masked_cells']
                maximum=0.
                for index,item in enumerate(geometry['bins']):
                    for row,column in item['cells']:
                        value=data[kind]['samples'][row][column]['field_norm_T']
                        low,high=geometry['minimum_sampled_T'],geometry['maximum_sampled_T']
                        assert low<=value<=high
                        if high>low:
                            expected=min(7,int(8*(value-low)/(high-low)));assert index==expected
                    vertices=np.asarray(item['segments_m'])/radius
                    if vertices.size:maximum=max(maximum,float(np.max(np.abs(vertices.astype(np.float32).astype(float)-vertices))))
                assert maximum<=1e-6
                camera=display.view(data,geometry);matrix=np.asarray(data['body_to_render'])
                if kind=='cut':
                    position=matrix.T@camera['position_render_relative_m'];up=matrix.T@camera['up_render'];u=np.array(data['cut']['u_axis_model'])
                    assert abs(np.dot(position,u))<=1e-10*camera['distance_m']
                    assert abs(position[2])<=1e-10*camera['distance_m'] and np.max(np.abs(up-[0.,0.,1.]))<=1e-12
                    look=-position/np.linalg.norm(position);screen_right=np.cross(look,up)
                    assert np.dot(screen_right,u)>1-1e-12
                report['cases'].append({'model':data['model'],'kind':kind,'symbols':len(cells),'float32_max_error_R':maximum,'camera_axes_valid':True})
        for variant in [{'representation':'invalid'},{'representation':'shell','corrupt':True}]:
            bad=copy.deepcopy(data)
            if variant.get('corrupt'):bad['shell']['samples'][0][0]['field_norm_T']=float('nan')
            try:display.build(bad,variant['representation'])
            except ValueError:pass
            else:raise AssertionError('Bad display accepted.')
        assert all(sha(ROOT/name)==value for name,value in hashes.items())
        report.update(accepted=True,completed=True,scope='Discrete source cells/colors/graphic glyphs and body-frame camera geometry; native rendering, probes and persistence still require separate checks.')
    except Exception:report['failure']=traceback.format_exc()
    receipt.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'accepted':report['accepted'],'cases':len(report['cases']),'failure':report.get('failure')}))
    return 0 if report['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
