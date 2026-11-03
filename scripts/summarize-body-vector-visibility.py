"""Measure green-arrow pixels in fixed-camera diagnostics; never infer field strength."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]


def measure(path):
    with Image.open(path) as source:
        rgb=np.asarray(source.convert('RGB'),dtype=np.float64)
    if rgb.shape[:2]!=(1080,1920):raise ValueError('Only the fixed1920×1080 Earth view is adopted.')
    # The unchanged Earth prototype projects its arrow into this rectangle.
    # Numerical direction/intensity are NOT reconstructed from the raster.
    region=rgb[500:650,650:800]
    red,green,blue=[region[:,:,i] for i in range(3)]
    mask=(green>140)&(red<.7*green)&(blue<.85*green)
    return int(mask.sum())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('receipts',nargs='+');parser.add_argument('--label',required=True);args=parser.parse_args()
    if not args.label or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label):parser.error('Invalid label.')
    destination=ROOT/('evidence/is3-visibility-summary-'+args.label+'.json')
    if destination.exists():raise FileExistsError('Preserve summary.')
    rows=[]
    for name in args.receipts:
        path=ROOT/name;report=json.loads(path.read_text(encoding='utf-8'))
        assert report['completed'] and report['accepted']
        for i,capture in enumerate(report['captures']):
            views=[('PrintWindow',capture)]+[('engine',item) for item in capture.get('engine_captures',[])]
            for source,item in views:
                image=ROOT/item['path'];assert hashlib.sha256(image.read_bytes()).hexdigest()==item['sha256']
                rows.append({'receipt':name,'capture_index':i+1,'scale':capture['scale'],
                    'CEF_visible':capture.get('CEF_visible'),'grid_visible':capture.get('lab_grid_visible'),
                    'label_visible':capture.get('sample_label_visible'),'source':source,'path':item['path'],
                    'arrow_colored_pixels_in_fixed_ROI':measure(image)})
    destination.write_text(json.dumps({'schema':1,'ROI_xywh':[650,500,150,150],
        'mask':'G>140,R<0.7G,B<0.85G; diagnostic counts, no pass threshold or SI interpretation.',
        'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'rows':rows,
        'scope':'Compare visibility at an unchanged projected Earth point only. Counts do not replace manual image review, scientific coordinates, magnitude or general visual acceptance.'},indent=2)+'\n')
    print(json.dumps(rows))


if __name__=='__main__':main()
