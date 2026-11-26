"""Record the assistant's completed direct review of six original0.26.2 framebuffers."""
import hashlib
import json
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'evidence/is6-dynamics16-visual-20261112b.json';assert not out.exists()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=[ROOT/f'evidence/is6-dynamics16-native-20261112{label}.json' for label in ['c','d']]
c,d=[json.loads(p.read_text(encoding='utf8')) for p in paths]
assert d['functional_accepted'] and len(c['captures'])==2 and len(d['captures'])==4
captures=c['captures']+d['captures']
assert len({(r['name'],r['scale']) for r in captures})==6
for item in captures:
    assert sha(ROOT/item['path'])==sha(ROOT/item['native_original'])==item['sha256']
    with Image.open(ROOT/item['path']) as im:assert im.size==(1920,1080);im.load()
result=dict(accepted=True,completed=True,candidate='0.26.2',captures=captures,
    native_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in paths},
    direct_review=dict(all_six_originals_viewed=True,selected_labels_clear_and_outside_markers=True,
        total_acceleration_and_units_visible_both_scales=True,concise_model_summary_visible=True,
        detailed_model_available_in_collapsed_section=True,no_horizontal_overflow=True,
        marker_scope='Expanded point-mass markers explicitly identified; not textured physical surfaces.'),
    compared_to_refused_presentation='0.26.1 had a verbose default panel and occluded labels. Its original captures and functional receipts are preserved.',
    script_sha256=sha(Path(__file__)),scope='Direct review of six unedited native framebuffer images; own performance acceptance remains pending.')
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(accepted=True,captures=6,direct_review_recorded=True)))
