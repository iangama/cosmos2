"""Five explicitly synthetic SI fixtures; no observed body identification."""
import math
from em_fields import Model,Source,K_E,MU_0
from em_particles import Phase
from em_mutual import System,Phase as MutualPhase
from em_experiment import Experiment

NAMES=('electric','helix','crossed','dipole','coulomb')
def create(name):
    if name=='coulomb':
        q=math.sqrt(1/K_E);e=.4;r=1-e;v=.5*math.sqrt((1+e)/(1-e))
        return Experiment('mutual_electrostatic',System(('positive','negative'),(q,-q),(1,1),(.01,.01)),
            MutualPhase(((-r,0,0),(r,0,0)),((0,-v,0),(0,v,0))),4*math.pi/4000,{'acting':True})
    if name=='electric':model=Model(uniform_E_V_m=(.1,0,0));phase=Phase((0,0,0),(1,0,.3))
    elif name=='helix':model=Model(uniform_B_T=(0,0,1));phase=Phase((0,0,0),(1,0,.3))
    elif name=='crossed':model=Model(uniform_E_V_m=(.2,0,0),uniform_B_T=(0,0,1));phase=Phase((0,0,0),(1,0,.3))
    elif name=='dipole':
        model=Model((Source('synthetic-dipole',(0,0,0),1.,0.,(0,0,.1*4*math.pi/MU_0)),))
        phase=Phase((3,0,0),(0,.5,.1))
    else:raise ValueError('Unknown synthetic EM preset')
    return Experiment('test_particle',model,phase,.002,{'electric_acting':True,'magnetic_acting':True},charge_C=1,mass_kg=1)
