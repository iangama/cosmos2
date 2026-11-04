"""Seal the assistant's completed manual W image review and pixel comparisons."""
from pathlib import Path
import hashlib
import json
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
out = ROOT / 'evidence/is6-layers-import-visual-20261104w.json'
if out.exists():
    raise FileExistsError('Preserve manual review')
files = [Path(__file__), ROOT / 'evidence/is6-import-native-captures-20261104w.json',
         ROOT / 'evidence/is6-layers-import-capture-process-20261104w.json',
         ROOT / 'evidence/is6-import-capture-pixel-comparison-20261104v2.json',
         ROOT / 'IS-6-CAPTURAS-CORRECAO-DIAGNOSTICO-20261104.md']
capture = json.loads(files[1].read_text(encoding='utf8'))
process = json.loads(files[2].read_text(encoding='utf8'))
comparison = json.loads(files[3].read_text(encoding='utf8'))
assert all(r['accepted'] and r['completed'] for r in [capture, process, comparison])
assert len(capture['captures']) == 16 and len(capture['replacement_mapping']) == 15
sources = {p.relative_to(ROOT).as_posix(): sha(p) for p in files}
sources.update(comparison['source_sha256'])
notes = dict(
    overview='Scene and caption follow both flags. With spatial hidden, the magnetic reference sphere, green vector and gold sample follow magnetic visibility; the independent spatial wire follows only spatial visibility. Scientific readings and units are legible at100%; panel scrolling and the fixed leave control remain available at150%.',
    storage='Save/restore, branch-name/selection and export controls are legible at150%, with the archived-reference message and fixed leave control visible.',
    import='Body, archived epoch, model, original flags and conversion/provenance policy are legible at100%/150%; confirm/cancel and the full lower notice are visible. Earth retains IGRF14; Jupiter retains JRM33 internal.'
)
reviewed = []
for item, verified in zip(capture['captures'], comparison['verified_inspection_copies'], strict=True):
    assert item['path'] == verified['original'] and sha(ROOT / item['path']) == item['sha256']
    assert sha(ROOT / verified['inspection_copy']) == verified['inspection_sha256']
    reviewed.append(dict(path=item['path'], sha256=item['sha256'],
                         inspection_copy=verified['inspection_copy'], inspection_sha256=verified['inspection_sha256'],
                         target=item['target'], section=item['section'], scale=item['scale'],
                         visible=item['artifact']['visible'], manually_reviewed=True, observations=notes[item['section']]))
equivalences = []
for row in capture['replacement_mapping']:
    current = next(v for v in capture['captures'] if v['path'] == row['replacement'])
    region = (1650, 119, 1896, 339) if current['scale'] == '1' else (1568, 179, 1885, 488)
    before = np.array(Image.open(ROOT / row['original']).convert('RGB').crop(region))
    after = np.array(Image.open(ROOT / row['replacement']).convert('RGB').crop(region))
    assert np.array_equal(before, after)
    assert sha(ROOT / row['original']) == row['original_sha256']
    sources[row['original']] = row['original_sha256']
    equivalences.append(dict(original=row['original'], replacement=row['replacement'],
                              caption_region_l_t_r_b=list(region), changed_RGB_pixels=0))
extra = []
for label in ['s', 't']:
    receipt = ROOT / ('evidence/is6-layers-import-native-20261104' + label + '.json')
    record = json.loads(receipt.read_text(encoding='utf8'))
    item = next(v for v in record['captures'] if '-399-import-' in v['path'])
    assert sha(ROOT / item['RGB']) == item['RGB_sha256']
    sources[item['RGB']] = item['RGB_sha256']
    sources[receipt.relative_to(ROOT).as_posix()] = sha(receipt)
    extra.append(dict(path=item['RGB'], sha256=item['RGB_sha256'], manually_reinspected=True,
                      note='Original RGB inspection copy retained; its caption matches W exactly. Final full-image visual acceptance uses the sixteen W images.'))
assert all(sha(ROOT / path) == seal for path, seal in sources.items())
result = dict(accepted=True, completed=True, candidate='0.21.1', source_sha256=sources,
              review_method='Direct assistant inspection of sixteen pixel-identical RGB inspection copies, with three caption detail crops; not automatic approval from DOM text or hashes alone.',
              captures=reviewed, original_caption_equivalences=equivalences, additional_original_reinspection=extra,
              diagnostic_correction=dict(file='IS-6-CAPTURAS-CORRECAO-DIAGNOSTICO-20261104.md',
                  receipt='evidence/is6-import-capture-pixel-comparison-20261104v2.json',
                  previous_PrintWindow_loss_interpretation_revoked=True,
                  native_preview_geometry_loss_not_confirmed=True),
              retained_limits=['Scientific content below the150% viewport is reached by panel scrolling; it is not required to fit on a single image.',
                  'Some100% audit images catch controls muted around the independent artifact read; the exercised UI journeys and import/storage views provide the interaction checks.',
                  'No internal Windows/CEF cause is inferred from differences in presented image previews.'],
              scope='K5 compound-import functional visual slice0.21.1 only; no own performance, spatial-only import, promotion or full IS6/v1 acceptance.')
out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
print(json.dumps(dict(accepted=True, reviewed_native_images=len(reviewed), caption_equivalences=len(equivalences), original_RGB_reinspections=len(extra))))
