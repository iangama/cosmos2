"""Preserve auditorA; accept native integer-valued JSON doubles for trace counters."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
old=ROOT/'scripts/audit-is6-dynamics16-profile.py';target=ROOT/'scripts/audit-is6-dynamics16-profile-v2.py'
assert not target.exists()
text=old.read_text(encoding='utf8')
old_check="assert type(item['count']) is int and item['count']>0"
assert text.count(old_check)==1
text=text.replace(old_check,"assert type(item['count']) in (int,float) and item['count']>0 and math.isfinite(item['count']) and item['count']==int(item['count'])")
text=text.replace("f'evidence/is6-dynamics16-profile-audit-{label}.json'","f'evidence/is6-dynamics16-profile-audit-v2-{label}.json'")
compile(text,str(target),'exec');target.write_text(text,encoding='utf8')
record=dict(prepared=True,measurement_limits_changed=False,frame_data_observed=False,
    basis='Already archived0.25.1 native trace counts are integer-valued doubles, e.g.4517.0. AuditorA incorrectly requires Python int. V2 preserves count>0/finite/integer value and every frame, RAM, GPU and clock threshold.',
    before_new_measurement_data_analysis=True,original_auditor_sha256=hashlib.sha256(old.read_bytes()).hexdigest(),
    new_auditor_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(ROOT/'evidence/is6-dynamics16-profile-audit-v2-preparation-20261112a.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(prepared=True,limits_unchanged=True)))
