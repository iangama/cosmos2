"""Prepare a partial local snapshot for the expanded journey; never copy active calculation inputs."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
base = ROOT / 'scripts/sync-github-source-snapshot-v16.py'
target = ROOT / 'scripts/sync-github-source-snapshot-v17.py'
receipt = ROOT / 'evidence/github-source-sync-v17-preparation-20261113a.json'
assert not target.exists() and not receipt.exists()
text = base.read_text(encoding='utf8')
marker = "patterns = ['evidence/is6-expanded-journey*.json',"
assert text.count(marker) == 1
text = text.replace(marker, """patterns = ['evidence/is6-expanded*.json',
            'output/is6-expanded-instruments-service-*/recipe-before-execution.json',
            'output/is6-expanded-instruments-service-*/orbital-worker/*.json',
            'output/is6-expanded-instruments-service-*/saved-sixteen/*.json',
            'output/is6-expanded-instruments-service-*/particle-*/worker/*.json',
            'output/is6-expanded-instruments-service-*/particle-*/checkpoints/**/*.json',
            'output/is6-expanded-instruments-service-*/layers-*/**/*.json',
            'output/is6-expanded-instruments-service-*/solar-zone/saved.json',
            'output/is6-expanded-instruments-service-*/solar-zone/branches/*.json',
            'output/is6-expanded-instruments-service-*/solar-zone/exports/*.json',
            'output/is6-expanded-journey-native-*/*.png',
            'output/is6-expanded-journey-native-*/stored-archives/**/*.json',
            'output/is6-expanded-journey-native-host-*/*.log',
            'output/is6-expanded-journey-product0.27.0/particle-checkpoints/**/*.json',
            'output/is6-expanded-journey-product0.27.0/layer-checkpoints/**/*.json',
            'output/is6-expanded-journey-product0.27.0/solar-zone-checkpoints/saved.json',
            'output/is6-expanded-journey-product0.27.0/solar-zone-checkpoints/branches/*.json',
            'output/is6-expanded-journey-product0.27.0/solar-zone-checkpoints/exports/*.json',
            'output/is6-expanded-journey-product0.27.0/gravity-sessions/**/*.json',
            'output/is6-expanded-journey-product0.27.0/gravity-sessions/**/*.bin',
            'output/is6-expanded-journey-product0.27.0/execution-logs/**/*',
            'output/handoff-archive/cota-20261113*.txt',
            'evidence/is6-expanded-journey*.json',""")
ast.parse(text)
target.write_text(text, encoding='utf8')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
receipt.write_text(json.dumps(dict(prepared=True, executed=False, local_only=True, base_sha256=sha(base), target_sha256=sha(target),
    scope='Partial expanded-journey source/evidence snapshot. Excludes runtimes, full capsules, personal sessions and live nuclear _work inputs.'), indent=2) + '\n')
print('v17 prepared; no copy or push executed')
