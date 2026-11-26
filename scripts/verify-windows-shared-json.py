"""Concurrent atomic-replacement fixture for control/status IPC; scientific samples untouched."""
import argparse
import hashlib
import json
from pathlib import Path
import threading
import traceback
import zipfile

from collect_expanded_residency_v4 import atomic
from windows_shared_json import read_json

ROOT=Path(__file__).resolve().parents[1]
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label',required=True);args=parser.parse_args()
    assert args.label and all(ch in 'abcdefghijklmnopqrstuvwxyz0123456789-' for ch in args.label)
    folder=ROOT/f'output/is6-shared-json-fixture-{args.label}';out=ROOT/f'evidence/is6-shared-json-fixture-{args.label}.json'
    assert not folder.exists() and not out.exists();folder.mkdir()
    sources={p.relative_to(ROOT).as_posix():sha(p) for p in [Path(__file__),ROOT/'scripts/windows_shared_json.py',ROOT/'scripts/collect_expanded_residency_v4.py']}
    with zipfile.ZipFile(folder/'executed-sources.zip','x',zipfile.ZIP_DEFLATED) as archive:
        for name in sources:archive.write(ROOT/name,name)
    answer=dict(accepted=False,completed=False,source_sha256=sources,reads=0,writes=0,refusals=[],scope='Windows IPC replacement/reader concurrency only; no process/GPU measurement, no retry or deletion of scientific data.')
    done=threading.Event();failures=[];path=folder/'control.json'
    def payload(index):return dict(index=index,text='Terra / Júpiter / Titã',items=[index]*200)
    atomic(path,payload(0))
    def writer():
        try:
            for index in range(1,1001):atomic(path,payload(index));answer['writes']=index
        except Exception:failures.append(traceback.format_exc())
        finally:done.set()
    thread=threading.Thread(target=writer)
    try:
        thread.start();previous=-1
        while not done.is_set() or answer['reads']<1000:
            value=read_json(path);assert value==payload(value['index']) and value['index']>=previous;previous=value['index'];answer['reads']+=1
        thread.join();assert not failures and answer['writes']==1000 and read_json(path)==payload(1000),failures
        path.write_text('{broken')
        try:read_json(path)
        except json.JSONDecodeError:answer['refusals'].append('Malformed committed JSON rejected without retry')
        else:raise AssertionError('Malformed JSON accepted')
        assert all(sha(ROOT/name)==seal for name,seal in sources.items())
        answer.update(accepted=True,completed=True)
    except Exception:answer['failure']=traceback.format_exc()
    finally:
        if thread.is_alive():thread.join(timeout=10)
        out.write_text(json.dumps(answer,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in answer.items() if k!='source_sha256'},ensure_ascii=False),flush=True)
    return 0 if answer['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
