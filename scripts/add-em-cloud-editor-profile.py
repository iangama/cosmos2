"""Explicit H profile identity; retain all declared scientific/resource limits."""
from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[1]
for name in ('benchmark-em128-new-runtime-native.py','benchmark-em128-potential-native.py','benchmark-em-cloud-source128-native.py'):
    p=ROOT/'scripts'/name;s=p.read_text();assert '--cloud-editor' not in s
    s=s.replace('args=parser.parse_args()',"parser.add_argument('--cloud-editor',action='store_true');args=parser.parse_args()") if 'args=parser.parse_args()' in s else s.replace('args = parser.parse_args()',"parser.add_argument('--cloud-editor', action='store_true')\nargs = parser.parse_args()")
    key='assert not args.integration or args.time_controls';assert key in s
    s=s.replace(key,key+'\nassert not args.cloud_editor or args.integration')
    key="if args.integration:CANDIDATE=ROOT/'output/c212-em-integration-product'";assert key in s
    s=s.replace(key,key+"\nif args.cloud_editor:CANDIDATE=ROOT/'output/c212-em-cloud-editor-product'")
    key=next(line for line in s.splitlines() if line.startswith('if args.integration:') and 'LAUNCHER=' in line)
    s=s.replace(key,key+"\nif args.cloud_editor:LAUNCHER=ROOT/'scripts/start-c212-em-cloud-editor-candidate.ps1'")
    key="'integration_profile': args.integration," if "'integration_profile': args.integration," in s else "'integration_profile':args.integration,"
    assert key in s;s=s.replace(key,key+"\n          'cloud_editor_profile':args.cloud_editor,")
    if name=='benchmark-em-cloud-source128-native.py':
        key="        page.goto('http://127.0.0.1:4700/em-cloud.html')";assert key in s
        s=s.replace(key,key+"\n        if args.cloud_editor:\n            page.wait_for_function('state&&!pending&&typeof cloudPanel!==\"undefined\"',timeout=30000)\n            page.locator('#interface-scale').select_option('1')\n            if page.evaluate('cloudPanel')!='layers':page.locator('[data-cloud-panel=\"layers\"]').click()\n            report['cloud_editor_UI']={'interface_scale':1,'active_panel':'layers'}")
    ast.parse(s);p.write_text(s)
for name,folder in (('review-em128-new-runtime-benchmark.py','em'),('review-em-cloud-source128-benchmark.py','em-cloud')):
    p=ROOT/'scripts'/name;s=p.read_text();assert 'cloud_editor_profile' not in s
    old='output/c212-em-integration-product/'+folder+'/';new='output/c212-em-cloud-editor-product/'+folder+'/'
    s=s.replace("'"+old+"/')","'"+old+"/')") if False else s
    # Expand only prefix identities; the criteria remain exactly as frozen G.
    s=s.replace("'"+old+"')","'"+old+"','"+new+"')")
    s=s.replace("(prefix=='"+old+"','"+new+"')","(prefix in ('"+old+"','"+new+"'))")
    # The tuple expansion above also covers the time-controls prefix allowlist.
    key="        if r.get('integration_profile'):";assert key in s
    before="        assert bool(r.get('cloud_editor_profile'))==(prefix=='"+new+"')\n        if r.get('cloud_editor_profile'):\n            assert r['session']['emCloudEditorCandidate']"
    if folder=='em-cloud':before+=" and r['cloud_editor_UI']=={'interface_scale':1,'active_panel':'layers'}"
    s=s.replace(key,before+'\n'+key)
    ast.parse(s);p.write_text(s)
print('H explicit profiles prepared; current G/F frozen archives preserved.',flush=True)
