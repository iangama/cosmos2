"""Single-threaded helper; an OS job owns its lifetime instead of a Python monitor."""
from pathlib import Path
import argparse
import json
import os


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--request',type=Path,required=True)
    parser.add_argument('--parent-pid',type=int,required=True)
    args=parser.parse_args()
    if args.parent_pid<=0 or os.getppid()!=args.parent_pid:raise ValueError('Calculation owner differs')
    from is5_coulomb_artifact import Run,Store,MAX_BYTES,ROOT
    path=args.request.resolve()
    if not path.is_relative_to((ROOT/'output').resolve()) or path.stat().st_size>MAX_BYTES:
        raise ValueError('Calculation request outside storage/budget')
    request=json.loads(path.read_text(encoding='utf-8'),object_pairs_hook=Store.unique)
    result=path.with_suffix('.result.json')
    try:
        if not isinstance(request,dict):raise ValueError('Calculation object required')
        if request.get('action')=='create' and set(request)=={'action','source_phase','configuration'}:
            run=Run.create(request['source_phase'],request['configuration'])
        elif request.get('action')=='restore' and set(request)=={'action','payload'}:
            run=Run.restore(request['payload'])
        else:raise ValueError('Exact calculation schema required')
        Store.atomic(result,dict(ok=True,run=run.payload,process_id=os.getpid()))
    except Exception as error:
        Store.atomic(result,dict(ok=False,error=str(error)[:2000],process_id=os.getpid()))


if __name__=='__main__':main()
