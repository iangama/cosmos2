"""Continue at150percent; preserve the valid100percent cases from nativeA."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
target=ROOT/'scripts/verify-native-is6-dynamics16-v2.py';assert not target.exists()
text=(ROOT/'scripts/verify-native-is6-dynamics16.py').read_text(encoding='utf8')
old="    folder.mkdir()"
new="    previous_path=ROOT/'evidence/is6-dynamics16-native-20261112a.json'\n    previous=json.loads(previous_path.read_text(encoding='utf8'))\n    assert len(previous['selections'])==16 and {s['scale'] for s in previous['selections']}=={'1'}\n    assert len({s['body'] for s in previous['selections']})==16 and previous['owner_view_restored']\n    assert 'Selected body camera not confirmed' in previous.get('failure','')\n    assert all(sha(ROOT/n)==s for n,s in previous['source_sha256'].items())\n    folder.mkdir()"
assert text.count(old)==1;text=text.replace(old,new)
text=text.replace("files += [Path(__file__),APP.parent/", "files += [previous_path,Path(__file__),APP.parent/")
text=text.replace("for scale in ['1','1.5']:", "for scale in ['1.5']:")
text=text.replace('if(!document.body.classList.contains("details-open"))$("panel-toggle").click()', 'if(document.body.classList.contains("details-open"))$("panel-toggle").click()')
old="            result['checks']['all16_selection_camera_reading_both_scales']=True"
new="            assert len(result['selections'])==16 and {s['scale'] for s in result['selections']}=={'1.5'}\n            result['checks']['all16_selection_camera_reading_both_scales']=dict(previous_receipt=previous_path.relative_to(ROOT).as_posix(),previous_sha256=sha(previous_path),previous_cases=16,current_cases=16,layout_correction='Large UI shows controls when details-open is false; nativeA had attempted a hidden control.')"
assert text.count(old)==1;text=text.replace(old,new)
compile(text,str(target),'exec');target.write_text(text,encoding='utf8')
target=ROOT/'scripts/diagnose-is6-dynamics16-ui150-v2.py';assert not target.exists()
text=(ROOT/'scripts/diagnose-is6-dynamics16-ui150.py').read_text(encoding='utf8').replace('ui150-diagnostic-20261112a.json','ui150-diagnostic-20261112b.json')
old="        page.locator('#ui-scale').select_option('1.5')"
text=text.replace(old,old+"\n        page.evaluate('if(document.body.classList.contains(\"details-open\"))$(\"panel-toggle\").click()')")
compile(text,str(target),'exec');target.write_text(text,encoding='utf8')
print(json.dumps(dict(prepared=True,product_changed=False,reason='At150percent details-open hides the left control panel; restore its visible layout before targeting controls.')))
