"""Pin the real frozen source capsule without treating publication counters as physics."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
base = ROOT / 'scripts/verify-is6-expanded-instruments-service-v2.py'
target = ROOT / 'scripts/verify-is6-expanded-instruments-service-v3.py'
out = ROOT / 'evidence/is6-expanded-instruments-service-v3-preparation-20261113a.json'
failed = ROOT / 'evidence/is6-expanded-instruments-service-20261113b.json'
prior = json.loads(failed.read_text())
assert not target.exists() and not out.exists()
assert not prior['accepted'] and 'assert p == phase and r == worker_reading' in prior['failure']
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(base) == prior['source_sha256'][base.relative_to(ROOT).as_posix()]
text = base.read_text()
old = '        self.orbital, self.reading = orbital, None\n'
new = old + '        self.phase = copy.deepcopy(orbital.latest)\n'
assert text.count(old) == 1
text = text.replace(old, new)
old = "        return dict(mode='experiment', physics=copy.deepcopy(self.orbital.latest),\n"
new = "        assert physical(self.orbital.latest) == physical(self.phase)\n        return dict(mode='experiment', physics=copy.deepcopy(self.phase),\n"
assert text.count(old) == 1
text = text.replace(old, new)
old = '''            source16 = copy.deepcopy(source.orbital.latest)
            try:
                source.orbital.latest = initial16
                refuse('Particle source16 ' + naif, lambda: initial_admission._initial(request))
            finally:
                source.orbital.latest = source16
'''
new = '''            class RejectedSource16:
                def status(self):
                    return dict(mode='experiment', physics=copy.deepcopy(initial16), body_field_preview=dict(reading=copy.deepcopy(worker_reading)))
            rejected_admission = ParticleLaboratory.__new__(ParticleLaboratory)
            rejected_admission.lab = RejectedSource16()
            refuse('Particle source16 ' + naif, lambda: rejected_admission._initial(request))
'''
assert text.count(old) == 1
text = text.replace(old, new)
old = "ROOT / 'IS-6-PERCURSO-AMPLIADO16-INSTRUMENTOS-REVISAO-B.md',"
new = old + "\n              ROOT / 'IS-6-PERCURSO-AMPLIADO16-INSTRUMENTOS-REVISAO-C.md',\n              ROOT / 'evidence/is6-expanded-instruments-service-20261113b.json',\n              ROOT / 'scripts/verify-is6-expanded-instruments-service-v2.py',"
assert text.count(old) == 1
text = text.replace(old, new)
ast.parse(text)
target.write_text(text, encoding='utf8')
result = dict(prepared=True, executed=False, base_sha256=sha(base), target_sha256=sha(target),
              failed_receipt_sha256=sha(failed), product_changed=False,
              change='Pin the actual paused source snapshot in the read-only status adapter; enforce exact physical equality with current real worker on every status call. Preserve publication counters in the pinned source.')
out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
print(json.dumps(result))
