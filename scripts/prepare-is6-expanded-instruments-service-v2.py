"""Preserve failed A; supply the real worker's fully identified magnetic reading in B."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
base = ROOT / 'scripts/verify-is6-expanded-instruments-service.py'
target = ROOT / 'scripts/verify-is6-expanded-instruments-service-v2.py'
receipt = ROOT / 'evidence/is6-expanded-instruments-service-v2-preparation-20261113a.json'
assert not target.exists() and not receipt.exists()
failed = ROOT / 'evidence/is6-expanded-instruments-service-20261113a.json'
prior = json.loads(failed.read_text())
assert not prior['accepted'] and len(prior['steps']) == 1
assert 'Field frame/generation differs from paused phase' in prior['failure']
assert hashlib.sha256(base.read_bytes()).hexdigest() == prior['source_sha256'][base.relative_to(ROOT).as_posix()]
text = base.read_text()
old = '            source.reading = reading\n'
new = '''            if naif == '399':
                worker_reading = orbital.call('earth_field', **orbital_guard(phase), body_id=body['id'],
                    latitude_deg=point['latitude'], longitude_deg=point['longitude'], altitude_m=point['altitude'])['result']
            else:
                worker_reading = orbital.call('jupiter_field', **orbital_guard(phase), body_id=body['id'],
                    latitude_deg=point['latitude'], east_longitude_deg=point['longitude'], radius_m=point['radius'],
                    degree=recipe['jovian_degree'])['result']
            assert worker_reading['scientific_generation'] == phase['scientific_generation']
            assert {k: v for k, v in worker_reading.items() if k != 'scientific_generation'} == reading
            source.reading = worker_reading
'''
assert text.count(old) == 1
text = text.replace(old, new)
text = text.replace('assert p == phase and r == reading', 'assert p == phase and r == worker_reading')
text = text.replace("particle_record['source_reading'] == reading", "particle_record['source_reading'] == worker_reading")
old = "ROOT / 'IS-6-PERCURSO-AMPLIADO16-INSTRUMENTOS-CONTRATO.md']"
assert text.count(old) == 1
text = text.replace(old, "ROOT / 'IS-6-PERCURSO-AMPLIADO16-INSTRUMENTOS-CONTRATO.md',\n              ROOT / 'IS-6-PERCURSO-AMPLIADO16-INSTRUMENTOS-REVISAO-B.md',\n              ROOT / 'evidence/is6-expanded-instruments-service-20261113a.json',\n              ROOT / 'scripts/verify-is6-expanded-instruments-service.py']")
ast.parse(text)
target.write_text(text, encoding='utf8')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
result = dict(prepared=True, executed=False, base_sha256=sha(base), target_sha256=sha(target),
              failed_receipt_sha256=sha(failed), product_changed=False,
              change='Use real orbital worker earth_field/jupiter_field readings with matching scientific_generation for particle admission; compare independent raw reading exactly.')
receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
print(json.dumps(result))
