"""Persist original-image review and pixel differences in an ROI clear of both CEF scales."""
from pathlib import Path
import hashlib
import json
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=ROOT/'evidence/is3-native-body-points-20261024a.json'
report=json.loads(source.read_text(encoding='utf-8'));assert report['accepted']
dest=ROOT/'evidence/is3-body-points-visual-review-20261024a.json'
if dest.exists():raise FileExistsError('Preserve visual review.')
for capture in report['captures']:assert sha(ROOT/capture['path'])==capture['sha256']
roi=[520,200,1500,900];pairs=[]
for model in ['399','599']:
    for kind in ['shell','cut']:
        images=[np.asarray(Image.open(ROOT/('evidence/cosmos2-is3-body-points-20261024a-'+model+'-'+kind+'-'+scale+'.png')).convert('RGBA'))[roi[1]:roi[3],roi[0]:roi[2]] for scale in ['100','150']]
        delta=np.abs(images[0].astype(int)-images[1].astype(int))
        pairs.append({'model':model,'representation':kind,'ROI':roi,'identical':bool(np.array_equal(*images)),
            'different_pixels':int(np.count_nonzero(np.any(delta,axis=2))),'maximum_RGBA_difference':int(delta.max())})
result={'schema':1,'accepted':True,'completed':True,'script_sha256':sha(Path(__file__)),
        'native_receipt_sha256':sha(source),'captures':report['captures'],'ROI_pairs':pairs,
        'manual_review':'All eight original1920x1080 PNG reviewed. Sample positions/colors and compact + marker visible, SI text legible at100/150, no horizontal overflow. Full Jovian cut sampled rectangle and masked body interior now visible after CPU idle and later GL frames. Long overlapping labels removed. The image-preview display can omit apparent regions: compare actual original pixels before inferring any vanished geometry.',
        'scope':'Visual acceptance of these four discrete frozen maps at these camera/UI scales only. Does not certify every view, generic point populations, performance or complete product visual design.'}
dest.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'accepted':True,'pairs':pairs}))
