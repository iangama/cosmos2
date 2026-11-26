"""Add explicit J profile identity; preserve measured I runners/auditors first."""
from pathlib import Path
import ast
import hashlib
import json
import tarfile

ROOT = Path(__file__).resolve().parents[1]
runners = ('benchmark-em128-new-runtime-native.py', 'benchmark-em128-potential-native.py', 'benchmark-em-cloud-source128-native.py')
auditors = ('review-em128-new-runtime-benchmark.py', 'review-em-cloud-source128-benchmark.py')
archive = ROOT / 'output/em-viewport-before-profile-support-20261022.tar.gz'
if not archive.exists():
    with tarfile.open(archive, 'w:gz') as tar:
        for name in (*runners, *auditors, 'em_framing_profile_audit.py'):
            path = ROOT / 'scripts' / name
            tar.add(path, arcname=str(path.relative_to(ROOT)))


def change(source, old, new):
    assert source.count(old) == 1, old
    return source.replace(old, new)


for name in runners:
    path = ROOT / 'scripts' / name
    source = path.read_text()
    if "parser.add_argument('--viewport'" in source:
        assert 'assert not args.viewport or args.framing' in source
        continue
    marker = 'args = parser.parse_args()' if 'args = parser.parse_args()' in source else 'args=parser.parse_args()'
    source = change(source, marker, "parser.add_argument('--viewport',action='store_true')\n" + marker)
    source = change(source, 'assert not args.framing or args.cloud_editor', 'assert not args.framing or args.cloud_editor\nassert not args.viewport or args.framing')
    source = change(source, "if args.framing:CANDIDATE=ROOT/'output/c212-em-framing-product'", "if args.framing:CANDIDATE=ROOT/'output/c212-em-framing-product'\nif args.viewport:CANDIDATE=ROOT/'output/c212-em-viewport-product'")
    source = change(source, "if args.framing:LAUNCHER=ROOT/'scripts/start-c212-em-framing-candidate.ps1'", "if args.framing:LAUNCHER=ROOT/'scripts/start-c212-em-framing-candidate.ps1'\nif args.viewport:LAUNCHER=ROOT/'scripts/start-c212-em-viewport-candidate.ps1'")
    source = change(source, "if args.framing:assert session['emFramingCandidate']", "if args.framing:assert session['emFramingCandidate']\nif args.viewport:assert session['emViewportCandidate']")
    source = change(source, "'framing_profile':args.framing,", "'framing_profile':args.framing,\n        'viewport_profile':args.viewport,")
    marker = 'report = {' if 'report = {' in source else 'report={'
    source = change(source, marker, "if args.viewport:\n    configuration += [ROOT/'scripts/em_viewport_profile_audit.py']\n" + marker)
    ast.parse(source)
    path.write_text(source)
for name in auditors:
    path = ROOT / 'scripts' / name
    source = path.read_text()
    suffix = 'em-cloud/' if 'cloud-source' in name else 'em/'
    old = 'output/c212-em-framing-product/' + suffix
    new = 'output/c212-em-viewport-product/' + suffix
    source = source.replace("'" + old + "')", "'" + old + "','" + new + "')")
    # The previous replacement also touched the exact I equality. Replace it
    # with an explicit two-prefix membership rather than broadening any flag.
    source = source.replace("(prefix=='" + old + "','" + new + "')", "(prefix in ('" + old + "','" + new + "'))")
    marker = "\n        if r.get('framing_profile'):"
    source = change(source, marker, "\n        assert bool(r.get('viewport_profile'))==(prefix=='" + new + "')\n        if r.get('viewport_profile'):assert r['session']['emViewportCandidate']" + marker)
    source = change(source, '            from em_framing_profile_audit import audit_dependencies', "            if r.get('viewport_profile'):\n                from em_viewport_profile_audit import audit_dependencies\n            else:\n                from em_framing_profile_audit import audit_dependencies")
    if 'cloud-source' not in name:
        source = change(source, '                from em_framing_profile_audit import audit_potential', "                if r.get('viewport_profile'):\n                    from em_viewport_profile_audit import audit_potential\n                else:\n                    from em_framing_profile_audit import audit_potential")
    ast.parse(source)
    path.write_text(source)
source = (ROOT / 'scripts/em_framing_profile_audit.py').read_text()
source = source.replace("BASE='output/c212-em-framing-product/'", "BASE='output/c212-em-viewport-product/'")
source = source.replace("audit='scripts/em_framing_profile_audit.py'", "audit='scripts/em_viewport_profile_audit.py'")
source = change(source, "    assert report['framing_profile'] and report['cloud_editor_profile'] and report['integration_profile']", "    assert report['viewport_profile'] and report['session']['emViewportCandidate']\n    assert report['framing_profile'] and report['cloud_editor_profile'] and report['integration_profile']")
source = change(source, 'assert conf[BASE+name]==proof_sources[BASE+name]', "assert conf[BASE+name]==proof_sources['output/c212-em-framing-product/'+name]")
source = source.replace("I's static", "J's unchanged static")
ast.parse(source)
path = ROOT / 'scripts/em_viewport_profile_audit.py'
assert not path.exists()
path.write_text(source)
paths = [ROOT / 'scripts' / name for name in (*runners, *auditors, 'em_viewport_profile_audit.py')]
report = {'status': 'J_explicit_profiles_prepared_not_executed', 'prior_I_sources_archive': str(archive.relative_to(ROOT)),
          'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
          'updated_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
          'scope': 'Explicit viewport flag requires framing/cloud-editor/integration/time/topic-cleanup. Exact prefixes and session flags required; scientific/frame/resource limits unchanged.'}
(ROOT / 'evidence/em-viewport-profile-support-prepared.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': report['status'], 'archive_sha256': report['archive_sha256']}), flush=True)
