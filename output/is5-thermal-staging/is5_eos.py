"""Ionized ideal mixture: classical ions, nonrelativistic Fermi electrons, LTE photons."""
from pathlib import Path
import hashlib
import math
import numpy as np
from scipy import constants
from scipy.integrate import quad
from scipy.optimize import brentq
from scipy.special import expit
from is5_core import SPECIES, A, Z, number

K = constants.Boltzmann
H = constants.Planck
ME = constants.electron_mass
C = constants.speed_of_light
MU = constants.atomic_mass
ARAD = 4 * constants.Stefan_Boltzmann / C
GAMMA = {-0.5: math.sqrt(math.pi), 0.5: math.sqrt(math.pi)/2, 1.5: 3*math.sqrt(math.pi)/4}
IMPORTED = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def generation():
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != IMPORTED:
        raise ValueError('Restart after EOS source changes')
    return dict(schema=1, id='is5:ideal-ion-FD-electron-LTE-photon', version='0.1.0',
                code_sha256=IMPORTED, constants=dict(k_B_J_K=K,h_J_s=H,m_e_kg=ME,c_m_s=C,
                    atomic_mass_kg=MU,radiation_constant_J_m3_K4=ARAD),
                scope='No Coulomb, relativity, thermal pairs, partial ionization, transport or hydrostatic structure.')


def fermi(order, eta):
    """Normalized DLMF25.12.14; x=t² removes the integrable endpoint singularity."""
    eta=number(eta)
    if order not in GAMMA or not -40 <= eta <= 40:
        raise ValueError('Fermi order or chemical potential outside numerical domain')
    power=2*order+1
    # Scaling keeps the integral O(1) in the classical tail, preserving relative accuracy.
    if eta < 0:
        scale=math.exp(eta)
        def integrand(t):
            return 2*t**power*math.exp(-t*t)/(1+math.exp(eta-t*t))
    else:
        scale=1.
        def integrand(t):
            return 2*t**power*float(expit(eta-t*t))
    result,error=quad(integrand,0,math.sqrt(max(eta,0)+80),epsabs=1e-13,epsrel=3e-13,limit=120)
    value=result*scale/GAMMA[order]
    if not math.isfinite(value) or value <= 0 or error > 1e-10*result:
        raise RuntimeError('Fermi quadrature did not meet its error budget')
    return value


def mixture(temperature_K,density_kg_m3,ions_per_baryon,electrons_per_baryon):
    """Unconstrained number coordinates allow consistent composition derivatives."""
    t,rho,yi,ye=map(number,(temperature_K,density_kg_m3,ions_per_baryon,electrons_per_baryon))
    if not 1e7<=t<=3e7 or not 1e4<=rho<=3e5 or not 0<yi<=2 or not 0<ye<=2:
        raise ValueError('Thermal EOS outside10–30MK, density or ionized-composition domain')
    nb=rho/MU;ni=nb*yi;ne=nb*ye
    wavelength=H/math.sqrt(2*math.pi*ME*K*t)
    degeneracy=ne*wavelength**3/2
    eta=brentq(lambda q:fermi(.5,q)-degeneracy,-40,40,xtol=2e-12,rtol=2e-14)
    fm,f1,f3=(fermi(s,eta) for s in (-.5,.5,1.5))
    pe=ne*K*t*f3/f1
    ue=1.5*pe;ui=1.5*ni*K*t;ur=ARAD*t**4
    cv_e=1.5*ne*K*(2.5*f3/f1-1.5*f1/fm)
    du_dne=1.5*K*t*f1/fm
    cv=1.5*ni*K+cv_e+4*ARAD*t**3
    if cv<=0:
        raise RuntimeError('Nonpositive isochoric heat capacity')
    electron_radius=(3/(4*math.pi*ne))**(1/3)
    return dict(temperature_K=t,density_kg_m3=rho,baryon_density_m3=nb,ion_density_m3=ni,electron_density_m3=ne,
        electron_eta=eta,electron_thermal_wavelength_m=wavelength,degeneracy_ne_lambda3_over2=degeneracy,
        electron_number_relative_residual=abs(2*f1/wavelength**3-ne)/ne,
        pressure_Pa=ni*K*t+pe+ur/3,ion_pressure_Pa=ni*K*t,electron_pressure_Pa=pe,radiation_pressure_Pa=ur/3,
        internal_energy_J_m3=ui+ue+ur,ion_internal_energy_J_m3=ui,electron_internal_energy_J_m3=ue,radiation_internal_energy_J_m3=ur,
        heat_capacity_J_m3_K=cv,electron_heat_capacity_J_m3_K=cv_e,
        du_dions_per_baryon_J_m3=nb*1.5*K*t,du_delectrons_per_baryon_J_m3=nb*du_dne,
        thermal_relativity_kT_over_mec2=K*t/(ME*C*C),
        fermi_relativity_pF_over_mec=constants.hbar*(3*math.pi**2*ne)**(1/3)/(ME*C),
        electron_Coulomb_parameter=constants.elementary_charge**2/(4*math.pi*constants.epsilon_0*electron_radius*K*t))


def evaluate(temperature_K,density_kg_m3,number_per_baryon):
    if not isinstance(number_per_baryon,(list,tuple)) or len(number_per_baryon)!=len(SPECIES):
        raise ValueError('Ten nuclear number fractions required')
    y=np.array([number(v) for v in number_per_baryon])
    if np.min(y)<-1e-20 or abs(float(A@y)-1)>1e-8:
        raise ValueError('Composition outside declared abundance/conservation tolerance')
    value=mixture(temperature_K,density_kg_m3,float(np.sum(y)),float(Z@y))
    value['maximum_ion_Coulomb_parameter']=max(float(z)**(5/3)*value['electron_Coulomb_parameter'] for z,n in zip(Z,y) if n>0)
    return {**value,'scientific_generation':generation()}
