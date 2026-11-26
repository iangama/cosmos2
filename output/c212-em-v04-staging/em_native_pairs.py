"""Bounded float64 wrapper for pinned, stateless MSVC scalar pair helper ABI1."""
from pathlib import Path
import ctypes
import hashlib
import json
import numpy as np
from em_particles import DomainExit

ROOT=Path(__file__).resolve().parent
_library=None
def library():
    global _library
    if _library is None:
        receipt=json.loads((ROOT/'build-receipt.json').read_text(encoding='utf-8-sig'))
        for name,key in (('cosmos2_em_pair.dll','dll_sha256'),('pair_kernel.cpp','cpp_sha256')):
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=receipt[key]:raise RuntimeError('EM native helper hash mismatch: '+name)
        dll=ctypes.CDLL(str(ROOT/'cosmos2_em_pair.dll'))
        dll.c2em_pair_abi.argtypes=[];dll.c2em_pair_abi.restype=ctypes.c_int
        if receipt['abi']!=1 or dll.c2em_pair_abi()!=1:raise RuntimeError('Unsupported EM native helper ABI')
        array=np.ctypeslib.ndpointer(dtype=np.float64,flags='C_CONTIGUOUS')
        dll.c2em_pair_geometry.argtypes=[ctypes.c_int]+[array]*7;dll.c2em_pair_geometry.restype=ctypes.c_int
        dll.c2em_pair_crossing.argtypes=[ctypes.c_int]+[array]*3;dll.c2em_pair_crossing.restype=ctypes.c_int
        _library=dll
    return _library

def checked_status(status,operation):
    if status==0:return
    if status==2:raise DomainExit('Pair '+operation+' enters declared exclusion')
    if status==3:raise DomainExit('Unrepresentable pair '+operation)
    raise RuntimeError('EM native helper '+operation+' refused ABI/buffer/allocation: '+str(status))

def geometry(position,coupling,exclusion):
    x=np.ascontiguousarray(position,dtype=np.float64)
    if x.ndim!=2 or x.shape[1]!=3 or not 1<=len(x)<=128 or not np.isfinite(x).all():raise ValueError('Bounded finite N×3 positions required')
    pairs=len(x)*(len(x)-1)//2
    c=np.ascontiguousarray(coupling,dtype=np.float64);e=np.ascontiguousarray(exclusion,dtype=np.float64)
    if c.shape!=(pairs,) or e.shape!=(pairs,):raise ValueError('Pair-buffer population mismatch')
    force=np.empty_like(x);delta=np.empty((pairs,3));radius=np.empty(pairs);energy=np.empty(pairs)
    checked_status(library().c2em_pair_geometry(len(x),x,c,e,force,delta,radius,energy),'geometry')
    return force,delta,radius,energy

def crossing(start,end,exclusion):
    a=np.ascontiguousarray(start,dtype=np.float64);b=np.ascontiguousarray(end,dtype=np.float64);e=np.ascontiguousarray(exclusion,dtype=np.float64)
    if a.ndim!=2 or a.shape[1]!=3 or not 0<=len(a)<=8128 or b.shape!=a.shape or e.shape!=(len(a),):raise ValueError('Pair drift-buffer population mismatch')
    checked_status(library().c2em_pair_crossing(len(a),a,b,e),'drift')
