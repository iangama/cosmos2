"""Deterministic synthetic SI clouds; prescribed sources have no reaction."""
import math
import numpy as np
from cloud_core import System, Phase
from em_fields import Model, Source, MU_0

NAMES = ('electric', 'helix', 'crossed', 'dipole', 'coulomb')


def create(name, count):
    if type(count) is not int or not 1 <= count <= 10000:
        raise ValueError('Cloud population must be an integer in1..10000')
    i = np.arange(count)
    theta = i * (math.pi * (3 - math.sqrt(5)))
    x = np.column_stack((.4*np.cos(theta), .4*np.sin(theta), .4*(i+.5)/count-.2))
    v = np.column_stack((np.ones(count), .1*np.sin(theta), np.full(count, .3)))
    if name == 'electric':
        model = Model(uniform_E_V_m=(.1, 0, 0))
    elif name == 'helix':
        model = Model(uniform_B_T=(0, 0, 1))
    elif name == 'crossed':
        model = Model(uniform_E_V_m=(.2, 0, 0), uniform_B_T=(0, 0, 1))
    elif name == 'dipole':
        model = Model((Source('synthetic-dipole', (0, 0, 0), 1, 0,
                              (0, 0, .1*4*math.pi/MU_0)),))
        x[:, 0] += 3
        v[:, 0] = 0
        v[:, 1] = .5
        v[:, 2] = .1
    elif name == 'coulomb':
        model = Model((Source('synthetic-fixed-charge', (0, 0, 0), .2, 1e-9),))
        x[:, 0] += 3
        v[:, 0] = 0
        v[:, 1] = .5
        v[:, 2] = .1
    else:
        raise ValueError('Unknown synthetic EM cloud preset')
    return (System.uniform(model, count, 1., 1.), Phase(x, v), .002,
            {'electric_acting': True, 'magnetic_acting': True})
