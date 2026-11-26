"""Isolated canonical massless cloud; not installed in Session or renderer."""
import math
import rebound
MAX_TEST_PARTICLES=10000

def make(count=10000):
    if type(count) is not int or not 1<=count<=MAX_TEST_PARTICLES:raise ValueError('Cloud count1..10000 required')
    sim=rebound.Simulation();sim.G=1.;sim.integrator='ias15';sim.integrator.epsilon=1e-9;sim.add(m=1.)
    for i in range(count):
        radius=1.+3.*i/max(1,count-1);angle=(i*math.pi*(3.-math.sqrt(5.)))%(2.*math.pi);speed=math.sqrt(1./radius)
        sim.add(m=0.,x=radius*math.cos(angle),y=radius*math.sin(angle),vx=-speed*math.sin(angle),vy=speed*math.cos(angle))
    sim.N_active=1;sim.testparticle_type=0
    return sim
