"""Preserve0.7 and stage0.7.1 with batched native points and compact map markers."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'output/is3-body-maps-product'
DEST=ROOT/'output/is3-body-points-product'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    receipt=ROOT/'evidence/is3-body-points-candidate-prepared-20261024.json'
    if DEST.exists() or receipt.exists():raise FileExistsError('Preserve candidate.')
    accepted=json.loads((ROOT/'evidence/node-lifecycle-v2-native-20261024a.json').read_text(encoding='utf-8'))
    assert accepted['accepted']
    files=[p for p in BASE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    before={p.relative_to(ROOT).as_posix():sha(p) for p in files}
    owner=sha(ROOT/'user/sessions/latest.json');DEST.mkdir()
    shutil.copytree(BASE/'app',DEST/'app',ignore=shutil.ignore_patterns('__pycache__'))
    (DEST/'gravity-sessions').mkdir()
    with zipfile.ZipFile(DEST/'base-0.7-sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in files:
            if 'gravity-sessions' not in p.parts:z.write(p,p.relative_to(ROOT).as_posix())
    app=DEST/'app'
    shutil.copy2(ROOT/'output/is3-body-points-staging/body_field_points.py',app/'body_field_points.py')
    def replace(name,old,new):
        p=app/name;s=p.read_text(encoding='utf-8');assert s.count(old)==1,(name,old);p.write_text(s.replace(old,new),encoding='utf-8')
    replace('body_registry.py',"'version':'0.7.0'","'version':'0.7.1'")
    replace('body_registry.py','output/is3-body-maps-product/app/jrm33-coefficients.json','output/is3-body-points-product/app/jrm33-coefficients.json')
    replace('body_registry.py',"'body_field_map_layer.py'","'body_field_map_layer.py','body_field_points.py'")
    replace('body_field_scene.py','from body_field_maps import build as build_maps','from body_field_maps import build as build_maps\nfrom body_field_points import batches')
    replace('body_field_scene.py',"        for index,item in enumerate(geometry['map_display']['bins']):\n            mesh('field_map_bin_'+str(index),item['segments_m'],item['color_rgb'],2)",
            "        points_code,points_meshes=batches(geometry,folder,frame,token,angles)\n        code+=points_code;meshes.extend(points_meshes);nodes.extend(m['node'] for m in points_meshes)")
    # The green arrow and panel identify the original B query; map cells use a
    # compact '+' at their exact location. Avoid two long labels at one point.
    replace('body_field_scene.py',"    local=product(matrix,geometry['point_model_m'])", "    local=product(matrix,geometry['point_model_m'])\n    label_text='' if representation in ('shell','cut') else 'B · amostra fixa'")
    replace('body_field_scene.py','Text="B · amostra fixa",FontSize=50','Text=\'+lua(label_text)+\',FontSize=50')
    replace('body_field_map_layer.py','Text="+ Sonda do mapa"','Text="+"')
    replace('ui/body-field-map.js','Célula ${probe.row}/${probe.column}', 'Marcador + · célula ${probe.row}/${probe.column}')
    assert all(sha(ROOT/name)==value for name,value in before.items())
    assert sha(ROOT/'user/sessions/latest.json')==owner
    receipt.write_text(json.dumps({'schema':1,'prepared':True,'accepted':False,'base_sha256':before,
        'owner_pointer_sha256':owner,'source_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in app.rglob('*') if p.is_file()},
        'scope':'Isolated0.7.1 batches at most8 native pointcloud nodes instead of3 lines per cell; same source grids, bins, mask and probe. Graphic round markers with constant per-map diameter and0.18degree cap, no size/force semantics. Compact cell marker. Native/visual/checkpoint/profile pending.'},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'prepared':True,'base_preserved':True}))


if __name__=='__main__':main()
