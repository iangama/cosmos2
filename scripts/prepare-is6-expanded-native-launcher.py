"""Prepare an isolated, gated native launcher/opener after actual instrument service acceptance."""
import argparse
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    parser.add_argument('--service-label', required=True)
    args = parser.parse_args()
    for label in [args.label, args.service_label]:
        assert label and len(label) <= 24 and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in label)
    receipt = ROOT / f'evidence/is6-expanded-native-launcher-preparation-{args.label}.json'
    launcher = ROOT / 'scripts/launch-is6-expanded-journey-candidate.py'
    opener = ROOT / 'scripts/open-expanded-journey-app.py'
    assert not receipt.exists() and not launcher.exists() and not opener.exists()
    service_path = ROOT / f'evidence/is6-expanded-instruments-service-{args.service_label}.json'
    service = json.loads(service_path.read_text())
    assert service['accepted'] and service['completed'] and service['common_four_phase_unchanged']
    assert all(sha(ROOT / n) == seal for n, seal in service['source_sha256'].items())
    base = ROOT / 'scripts/launch-is6-dynamics16-candidate-v5.py'
    text = base.read_text().replace('is6-dynamics16-product0.26.2', 'is6-expanded-journey-product0.27.0')
    text = text.replace('0.26.2', '0.27.0')
    text = text.replace("assert manifest['inherited_service']['python_files_byte_identical'] and manifest['changed']==['ui/body-editor.js','ui/index.html','ui/solar.js']", "assert manifest['changed']==[]")
    text = text.replace("for kind in ['service','http']:\n        proof=json.loads((ROOT/f'evidence/is6-dynamics16-{kind}-20261112c.json').read_text(encoding='utf8'))", "for kind in ['service','http']:\n        proof=json.loads((ROOT/f'evidence/is6-expanded-journey-{kind}-20261112b.json').read_text(encoding='utf8'))")
    marker = "    candidate=ROOT/'output/is6-expanded-journey-product0.27.0'\n"
    gate = f"    instruments=json.loads((ROOT/'evidence/is6-expanded-instruments-service-{args.service_label}.json').read_text())\n    assert instruments['accepted'] and instruments['completed']\n"
    text = text.replace(marker, gate + marker, 1)
    text = text.replace("launch['is6Dynamics16Candidate'] = True", "launch['is6Dynamics16Candidate'] = True\n        launch['is6ExpandedJourneyCandidate'] = True")
    text = text.replace('IS6-Dynamics16-', 'IS6-ExpandedJourney-')
    ast.parse(text)
    assert 'is6-dynamics16-product0.26.2' not in text and '0.26.2' not in text
    launcher.write_text(text, encoding='utf8')
    base_opener = ROOT / 'scripts/open-dynamics16-app.py'
    text = base_opener.read_text().replace('launch-is6-dynamics16-candidate-v5.py', launcher.name)
    text = text.replace('is6-dynamics16-product0.26.2', 'is6-expanded-journey-product0.27.0').replace('0.26.2', '0.27.0')
    text = text.replace('is6-principal-moons-navigation-open-', 'is6-expanded-journey-open-')
    ast.parse(text)
    opener.write_text(text, encoding='utf8')
    result = dict(prepared=True, native_executed=False, candidate='0.27.0', product_changed=False,
                  source_sha256={p.relative_to(ROOT).as_posix(): sha(p) for p in [Path(__file__), base, base_opener, service_path]},
                  launcher_sha256=sha(launcher), opener_sha256=sha(opener),
                  scope='Own gated launcher/opener only. No shortcuts changed or native acceptance.')
    receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps(dict(prepared=True, candidate='0.27.0', native_executed=False)))


if __name__ == '__main__':
    main()
