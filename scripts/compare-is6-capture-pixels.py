"""Verify actual RGB pixels independently of their displayed tool preview."""
from pathlib import Path
import hashlib
import json
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
out = ROOT / 'evidence/is6-import-capture-pixel-comparison-20261104v2.json'
if out.exists():
    raise FileExistsError('Preserve comparison receipt')
sources = {Path(__file__).relative_to(ROOT).as_posix(): sha(Path(__file__))}
for name in ['IS-6-CAPTURAS-CORRECAO-DIAGNOSTICO-20261104.md',
             'evidence/is6-import-caption-diagnostic-20261104v.json',
             'evidence/is6-import-caption-review-20261104v.json',
             'evidence/is6-import-native-captures-20261104w.json']:
    sources[name] = sha(ROOT / name)
images = {}
formats = {}
for name in ['engine-before', 'printwindow', 'engine-after']:
    path = ROOT / ('evidence/cosmos2-is6-caption-v-' + name + '.png')
    im = Image.open(path)
    sources[path.relative_to(ROOT).as_posix()] = sha(path)
    formats[name] = dict(mode=im.mode, size=list(im.size))
    if 'A' in im.getbands():
        histogram = im.getchannel('A').histogram()
        formats[name]['alpha_histogram'] = {str(i): n for i, n in enumerate(histogram) if n}
    images[name] = np.array(im.convert('RGB'))
regions = dict(left_panel=[36, 175, 530, 924], caption=[1568, 180, 1884, 487],
               footer=[36, 953, 1884, 1053])
comparisons = []
for name in ['printwindow', 'engine-after']:
    delta = np.max(np.abs(images['engine-before'].astype(np.int16) - images[name].astype(np.int16)), axis=2)
    changed = np.argwhere(delta)
    row = dict(first='engine-before', second=name, different_pixels=int(np.count_nonzero(delta)),
               max_channel_difference=int(delta.max()), changed_coordinates_y_x=changed.tolist(),
               region_different_pixels={k: int(np.count_nonzero(delta[t:b, l:r])) for k, (l, t, r, b) in regions.items()})
    assert not any(row['region_different_pixels'].values())
    comparisons.append(row)
assert comparisons[0]['different_pixels'] == 4 and comparisons[1]['different_pixels'] == 0
capture = json.loads((ROOT / 'evidence/is6-import-native-captures-20261104w.json').read_text(encoding='utf8'))
assert capture['accepted'] and capture['completed'] and len(capture['captures']) == 16
copies = []
for item in capture['captures']:
    original = ROOT / item['path']
    copy = ROOT / 'output/is6-native-framebuffer-RGB-20261104w' / original.name
    first, second = Image.open(original), Image.open(copy)
    assert sha(original) == item['sha256']
    assert first.mode == second.mode == 'RGB'
    assert first.size == second.size == (1920, 1080)
    assert first.tobytes() == second.tobytes()
    sources[item['path']] = item['sha256']
    sources[copy.relative_to(ROOT).as_posix()] = sha(copy)
    copies.append(dict(original=item['path'], original_sha256=item['sha256'],
                       inspection_copy=copy.relative_to(ROOT).as_posix(), inspection_sha256=sha(copy),
                       equal_RGB_pixels=True))
result = dict(accepted=True, completed=True, source_sha256=sources, formats=formats,
              regions=regions, comparisons=comparisons, verified_inspection_copies=copies,
              supersedes_interpretation=['evidence/is6-import-caption-review-20261104v.json',
                  'IS-6-COEXISTENCIA-MIGRACAO-NATIVA-K5-REVISAO-C.md: initial PrintWindow-loss diagnosis only'],
              findings=['The V files have identical RGB pixels throughout all three inspected UI regions.',
                  'Only four pixels outside those UI regions differ between native and PrintWindow images.',
                  'The earlier claim that the PrintWindow file lost UI pixels is refuted by direct comparison.',
                  'All sixteen W inspection copies preserve exactly the native RGB pixels; original PNGs remain unchanged.',
                  'The image preview presentation is not sufficient evidence of an internal product or capture-method defect.'],
              scope='Pixel comparison and correction of a prior interpretation only; manual visual review, own performance and promotion remain separate.')
out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
print(json.dumps(dict(accepted=True, comparisons=comparisons, verified_RGB_copies=len(copies))))
