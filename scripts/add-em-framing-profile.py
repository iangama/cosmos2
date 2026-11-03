"""Prepare explicit I runners/auditors while preserving their H source."""
from pathlib import Path
import hashlib
import json
import tarfile

ROOT=Path(__file__).resolve().parents[1]
runners=('benchmark-em128-new-runtime-native.py','benchmark-em128-potential-native.py','benchmark-em-cloud-source128-native.py')
auditors=('review-em128-new-runtime-benchmark.py','review-em-cloud-source128-benchmark.py')
archive=ROOT/'output/em-framing-before-profile-support-20261022.tar.gz'
assert not archive.exists()
paths=[ROOT/'scripts'/name for name in (*runners,*auditors)]
with tarfile.open(archive,'w:gz') as tar:
    for p in paths:tar.add(p,arcname=p.relative_to(ROOT))
for name in runners:
    p=ROOT/'scripts'/name;s=p.read_text();assert '--framing' not in s
    marker='args = parser.parse_args()' if 'args = parser.parse_args()' in s else 'args=parser.parse_args()'
    s=s.replace(marker,"parser.add_argument('--framing',action='store_true')\n"+marker,1)
    marker='assert not args.cloud_editor or args.integration'
    s=s.replace(marker,marker+'\nassert not args.framing or args.cloud_editor',1)
    marker="if args.cloud_editor:CANDIDATE=ROOT/'output/c212-em-cloud-editor-product'"
    assert marker in s;s=s.replace(marker,marker+"\nif args.framing:CANDIDATE=ROOT/'output/c212-em-framing-product'",1)
    marker="if args.cloud_editor:LAUNCHER=ROOT/'scripts/start-c212-em-cloud-editor-candidate.ps1'"
    assert marker in s;s=s.replace(marker,marker+"\nif args.framing:LAUNCHER=ROOT/'scripts/start-c212-em-framing-candidate.ps1'",1)
    marker="owner = ROOT/'user/sessions/latest.json'" if "owner = ROOT/" in s else "owner=ROOT/'user/sessions/latest.json';original=owner.read_bytes()"
    assert marker in s;s=s.replace(marker,"if args.framing:assert session['emFramingCandidate']\n"+marker,1)
    marker="'cloud_editor_profile':args.cloud_editor,"
    assert marker in s;s=s.replace(marker,marker+"\n        'framing_profile':args.framing,",1)
    marker='report = {' if 'report = {' in s else 'report={'
    additions="if args.framing:\n    configuration += [ROOT/'scripts/em_framing_profile_audit.py',ROOT/'evidence/em-framing-static-sampler-release2-check.json']\n"
    if name!='benchmark-em-cloud-source128-native.py':
        additions+="    configuration += [ROOT/'scripts/build-em-cloud-kernel.ps1',CANDIDATE/'em-cloud/CMakeLists.txt']\n    configuration += [p for p in (CANDIDATE/'em-cloud').rglob('*') if p.is_file() and p.suffix in ('.py','.json','.cpp','.dll') and '__pycache__' not in p.parts]\n"
    assert marker in s;s=s.replace(marker,additions+marker,1)
    if name=='benchmark-em128-potential-native.py':
        marker="'frozen_potential_render':route_potential,"
        assert marker in s;s=s.replace(marker,"'frozen_potential_layer':potential,"+marker,1)
    p.write_text(s)
for name in auditors:
    p=ROOT/'scripts'/name;s=p.read_text();assert 'framing_profile' not in s
    cloud=name=='review-em-cloud-source128-benchmark.py';suffix='em-cloud/' if cloud else 'em/'
    old='output/c212-em-cloud-editor-product/'+suffix;new='output/c212-em-framing-product/'+suffix
    # Extend existing exact prefix allowlists without changing any thresholds.
    s=s.replace("(prefix=='"+old+"')","(prefix in ('"+old+"',))")
    s=s.replace("'"+old+"')","'"+old+"','"+new+"')")
    s=s.replace("'"+old+"',))","'"+old+"','"+new+"'))")
    marker="        if r.get('integration_profile'):"
    assert marker in s;s=s.replace(marker,"        assert bool(r.get('framing_profile'))==(prefix=='"+new+"')\n        if r.get('framing_profile'):\n            assert r['session']['emFramingCandidate']\n            from em_framing_profile_audit import audit_dependencies\n            result['framing_static_dependencies']=audit_dependencies(r,frozen)\n"+marker,1)
    if not cloud:
        marker="            render=run['frozen_potential_render'];"
        assert marker in s;s=s.replace(marker,"            if r.get('framing_profile'):\n                from em_framing_profile_audit import audit_potential\n                result.setdefault('framing_potential_audits',[]).append(audit_potential(r,run,ke))\n"+marker,1)
    p.write_text(s)
receipt={'status':'explicit_I_profiles_prepared_not_executed','prior_H_sources_archive':str(archive.relative_to(ROOT)),
         'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
         'updated_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
(ROOT/'evidence/em-framing-profile-support-prepared.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
