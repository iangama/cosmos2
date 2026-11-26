"""Hash-verified ABI1 helper; private outputs become immutable only on success."""
from pathlib import Path
import ctypes
import hashlib
import json
import math
import numpy as np
from em_fields import K_E, MU_0, SPEED_LIMIT_M_S
from em_particles import DomainExit

BASE = Path(__file__).resolve().parent
receipt = json.loads((BASE/'build-receipt.json').read_text(encoding='utf-8-sig'))
assert receipt['schema'] == receipt['abi'] == 1
for name, key in (('cloud_kernel.cpp', 'cpp_sha256'), ('CMakeLists.txt', 'cmake_sha256'),
                  ('cosmos2_em_cloud.dll', 'dll_sha256')):
    if hashlib.sha256((BASE/name).read_bytes()).hexdigest() != receipt[key]:
        raise RuntimeError('EM cloud helper differs from build receipt: '+name)
_dll = ctypes.CDLL(str(BASE/'cosmos2_em_cloud.dll'))
_dll.c2em_cloud_abi.restype = ctypes.c_int
assert _dll.c2em_cloud_abi() == 1
_dll.c2em_cloud_avx2.restype = ctypes.c_int
if _dll.c2em_cloud_avx2() != 1:
    raise RuntimeError('This experimental helper requires AVX2 and OS AVX state support')
_array = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
_int, _double = ctypes.c_int, ctypes.c_double
_bad = ctypes.POINTER(_int)
_dll.c2em_cloud_fields.argtypes = [_int, _int, _array, _array, _array, _array,
                                  _double, _double, _int, _int, _array, _array, _array, _bad]
_dll.c2em_cloud_fields.restype = _int
_dll.c2em_cloud_step.argtypes = [_int, _int, _array, _array, _array, _array, _array, _array, _array,
                                _double, _double, _double, _double, _int, _int, _int,
                                _array, _array, _array, _array, _bad]
_dll.c2em_cloud_step.restype = _int

def immutable(value):
    a = np.ascontiguousarray(value, dtype='<f8')
    return np.frombuffer(a.tobytes(), dtype='<f8').reshape(a.shape)

def pack(model):
    sources = [[*s.position_m, s.exclusion_radius_m, s.charge_C, *s.magnetic_moment_A_m2]
               for s in model.sources]
    return (len(sources), immutable(sources or [[0.]*8]),
            immutable(model.uniform_E_V_m), immutable(model.uniform_B_T))

def threads(value):
    if type(value) is not int or not 1 <= value <= 8:
        raise ValueError('Explicit native thread count1..8 required')
    return value

def checked(code, bad):
    if code:
        messages = {1: 'Invalid native cloud buffers or scalar domain',
                    2: 'Drift or field sample reaches excluded source',
                    3: 'Unrepresentable native cloud arithmetic',
                    4: 'Cloud positions outside finite1e17m component domain',
                    5: 'Cloud trial exceeds0.01c', 6: 'Cloud gyro angle exceeds0.1rad per step',
                    7: 'Native cloud scratch allocation failed'}
        raise DomainExit(messages.get(code, 'Unknown native helper failure')+'; particle index '+str(bad.value))

def evaluate(packed, x, *, potential=True, thread_count=8):
    n = len(x)
    e, b, phi = np.empty_like(x), np.empty_like(x), np.empty(n)
    count, sources, e0, b0 = packed
    bad = _int(-1)
    code = _dll.c2em_cloud_fields(n, count, x, sources, e0, b0, K_E, MU_0/(4*math.pi),
                                 int(potential), threads(thread_count), e, b, phi, ctypes.byref(bad))
    checked(code, bad)
    return e, b, phi if potential else None

def step(packed, x, v, q, mass, dt, electric, magnetic, *, thread_count=8):
    n = len(x)
    outx, outv, work, kinetic = np.empty_like(x), np.empty_like(v), np.empty(n), np.empty(n)
    count, sources, e0, b0 = packed
    bad = _int(-1)
    code = _dll.c2em_cloud_step(n, count, x, v, q, mass, sources, e0, b0,
                              K_E, MU_0/(4*math.pi), dt, SPEED_LIMIT_M_S,
                              int(electric), int(magnetic), threads(thread_count),
                              outx, outv, work, kinetic, ctypes.byref(bad))
    checked(code, bad)
    return outx, outv, work, kinetic
