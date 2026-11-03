"""One bounded local calculation; exits if its owning worker disappears."""
from pathlib import Path
import argparse
import ctypes
import json
import os
import sys
import threading
import time


def watch_parent(parent_pid):
    if sys.platform == 'win32':
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.argtypes=[ctypes.c_uint32,ctypes.c_int,ctypes.c_uint32]
        kernel.OpenProcess.restype=ctypes.c_void_p
        kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint32]
        kernel.CloseHandle.argtypes=[ctypes.c_void_p]
        handle=kernel.OpenProcess(0x00100000,False,parent_pid)
        if not handle:os._exit(3)
        while kernel.WaitForSingleObject(handle,100)==258:
            pass
        kernel.CloseHandle(handle)
        os._exit(3)
    else:
        while os.getppid()==parent_pid:
            time.sleep(.1)
        os._exit(3)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--request',type=Path,required=True)
    parser.add_argument('--parent-pid',type=int,required=True)
    args=parser.parse_args()
    if args.parent_pid<=0:raise ValueError('Owning worker pid required')
    threading.Thread(target=watch_parent,args=(args.parent_pid,),daemon=True).start()
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
        Store.atomic(result,dict(ok=True,run=run.payload))
    except Exception as error:
        Store.atomic(result,dict(ok=False,error=str(error)[:2000]))


if __name__=='__main__':main()
