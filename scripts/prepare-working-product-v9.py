"""Preserve the tested candidate and fix first-job control restoration in a new revision."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]
PARENT=ROOT/'output/original-flow-hotfix-product0.28.3'
TARGET=ROOT/'output/original-flow-hotfix-product0.28.4'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    assert not TARGET.exists()
    proof=json.loads((ROOT/'evidence/working-orbits-ui-20261121a.json').read_text())
    assert proof['completed'] and not proof['accepted'] and sum(not r['passed'] for r in proof['checks'])==1
    parent=json.loads((PARENT/'build-manifest.json').read_text())
    assert all(sha(PARENT/n)==seal for n,seal in parent['files_sha256'].items())
    for folder in ['app','data']:shutil.copytree(PARENT/folder,TARGET/folder,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    js=TARGET/'app/ui/forces.js';text=js.read_text()
    before='  }catch(error){\n    if(error.cancelled&&response)'
    assert text.count(before)==1
    js.write_text(text.replace(before,'  }catch(error){\n    if(response)renderResult();\n    if(error.cancelled&&response)'),encoding='utf8')
    files={p.relative_to(TARGET).as_posix():sha(p) for folder in ['app','data'] for p in (TARGET/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    assert [n for n in files if files[n]!=parent['files_sha256'][n]]==['app/ui/forces.js']
    manifest=dict(parent,candidate='0.28.4',files_sha256=files,
      preparation_parent_manifest_sha256=sha(PARENT/'build-manifest.json'),preparation_script_sha256=sha(Path(__file__)),
      scope=parent['scope']+' Revision0.28.4 also restores confirmed-result controls after cancellation/error. All backend bytes identical to HTTP-accepted0.28.3; only forces.js differs.')
    (TARGET/'build-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(prepared=True,candidate='0.28.4',backend_identical=True,selected=False)))


if __name__=='__main__':main()
