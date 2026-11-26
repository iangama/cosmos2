"""Resume after a transient incompletePNG; retain successful100percent casesC."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
target=ROOT/'scripts/verify-native-is6-dynamics16-v4.py';assert not target.exists()
text=(ROOT/'scripts/verify-native-is6-dynamics16-v3.py').read_text(encoding='utf8')
text=text.replace('except OSError:pass','except (OSError,SyntaxError):pass')
old='    folder.mkdir()'
new="    previous_path=ROOT/'evidence/is6-dynamics16-native-20261112c.json'\n    previous=json.loads(previous_path.read_text(encoding='utf8'))\n    assert len(previous['selections'])==16 and {s['scale'] for s in previous['selections']}=={'1'}\n    assert len({s['body'] for s in previous['selections']})==16 and previous['owner_view_restored']\n    assert len(previous['captures'])==2 and 'SyntaxError: broken PNG' in previous.get('failure','')\n    assert all(sha(ROOT/n)==s for n,s in previous['source_sha256'].items())\n    folder.mkdir()"
assert text.count(old)==1;text=text.replace(old,new)
text=text.replace("files += [Path(__file__),APP.parent/", "files += [previous_path,Path(__file__),APP.parent/")
old="            for scale in ['1','1.5']:"
new="            page.locator('#ui-scale').select_option('1')\n            page.evaluate('$(\"solar-panel\").open=true;if(document.body.classList.contains(\"details-open\"))$(\"panel-toggle\").click()')\n            titan=initial['bodies'][-1]\n            page.locator('#solar-body').select_option(titan['id']);click(page,'#solar-view-body');click(page,'#solar-sample')\n            page.wait_for_function('!pending&&solarReading?.body_id==='+json.dumps(titan['id']),timeout=70000)\n            capture(page,titan['name'].lower(),'1')\n            for scale in ['1.5']:"
assert text.count(old)==1;text=text.replace(old,new)
old="            result['checks']['all16_selection_camera_reading_both_scales']=True"
new="            assert len(result['selections'])==16 and {s['scale'] for s in result['selections']}=={'1.5'}\n            result['checks']['all16_selection_camera_reading_both_scales']=dict(previous_receipt=previous_path.relative_to(ROOT).as_posix(),previous_sha256=sha(previous_path),previous_cases=16,current_cases=16,PNG_readiness_correction='Retry SyntaxError as well as OSError while the native PNG writer finishes; original frames are never edited.')"
assert text.count(old)==1;text=text.replace(old,new)
compile(text,str(target),'exec');target.write_text(text,encoding='utf8')
print(json.dumps(dict(prepared=True,product_changed=False,resume='NativeC16selections100percent; capture-readiness retry fixed before continuing150percent.')))
