"""Declared charged/dipolar shell fixture; no production solver imports."""
import math
import numpy as np

def source_model():
    sources = []
    for k in range(128):
        z = 1-2*(k+.5)/128
        a = k*math.pi*(3-math.sqrt(5))
        r = math.sqrt(1-z*z)
        sources.append({'id': str(k), 'position_m': [8*r*math.cos(a), 8*r*math.sin(a), 8*z],
                        'exclusion_radius_m': .02, 'charge_C': (-1)**k*1e-12,
                        'magnetic_moment_A_m2': [1e4, -2e4, 3e4]})
    return {'sources': sources, 'uniform_E_V_m': [0., 0., 0.], 'uniform_B_T': [0., 0., 1.]}

def particles():
    i = np.arange(10000)
    a = i*math.pi*(3-math.sqrt(5))
    return (np.column_stack((.4*np.cos(a), .4*np.sin(a), .4*(i+.5)/10000-.2)),
            np.column_stack((np.ones(10000), .1*np.sin(a), np.zeros(10000))))
