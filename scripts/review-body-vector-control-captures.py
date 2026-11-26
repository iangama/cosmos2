"""Preserve an original-pixel review of the completed vector control captures."""
from pathlib import Path
import hashlib
import json
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def main():
    receipt = ROOT/'evidence/is3-body-vector-controls-visual-review-20261024.json'
    folder = ROOT/'output/is3-body-vector-controls-visual-review-20261024'
    if receipt.exists() or folder.exists():
        raise FileExistsError('Preserve the earlier review.')
    source = ROOT/'evidence/is3-native-body-layer-20261024a.json'
    report = json.loads(source.read_text(encoding='utf-8'))
    folder.mkdir()
    rows = []
    for model in ['earth', 'jupiter']:
        captures = [c for c in report['captures'] if c['model'] == model]
        arrays = []
        for capture in captures:
            path = ROOT/capture['path']
            assert hashlib.sha256(path.read_bytes()).hexdigest() == capture['sha256']
            arrays.append(np.asarray(Image.open(path).convert('RGBA')))
        assert [c['scale'] for c in captures] == ['100', '150']
        # This rectangle excludes both side panels at both interface scales.
        regions = [a[180:900, 550:1500] for a in arrays]
        maximum = int(np.max(np.abs(regions[0].astype(int)-regions[1].astype(int))))
        assert maximum == 0
        counts = []
        for capture, array in zip(captures, arrays):
            region = array[500:650, 650:800, :3].astype(float)
            r, g, b = [region[:, :, i] for i in range(3)]
            counts.append(int(((g > 140) & (r < .7*g) & (b < .85*g)).sum()))
            Image.fromarray(array[480:660, 620:1120]).resize((1500, 540), Image.Resampling.NEAREST).convert('RGB').save(
                folder/(model+'-'+capture['scale']+'-arrow-original-pixels.png'))
        assert counts[0] == counts[1] and counts[0] > 0
        rows.append({'model': model, 'captures': captures, 'scene_ROI_xyxy': [550, 180, 1500, 900],
                     'maximum_RGBA_difference': maximum, 'arrow_ROI_xyxy': [650, 500, 800, 650],
                     'green_pixel_count_100_150': counts})
    receipt.write_text(json.dumps({'schema': 1, 'accepted': True, 'rows': rows,
        'source_receipt_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'review_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'manual_review': 'Original controls legible at100/150; grid, yellow point, green arrow and fixed-sample label visible. Original scene pixels are identical between scales. Crops preserve pixels with nearest-neighbor enlargement.',
        'scope': 'These four fixed-camera control captures only. No general renderer, field-line, surface-texture or final Solar System visual acceptance.'}, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print(json.dumps({'accepted': True, 'models': [r['model'] for r in rows],
                      'maximum_RGBA_difference': 0, 'arrow_pixels': [r['green_pixel_count_100_150'] for r in rows]}))


if __name__ == '__main__':
    main()
