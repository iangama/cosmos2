# SPDX-License-Identifier: LGPL-3.0-or-later
# Scalar EXCOR7 and electron polarization adapted from MESA26.4.1 Skye.
# Copyright (C) 2022 The MESA Team. Cosmos2 modifications (2026): SI neutral
# mixture, full composition derivatives, classical Caillol OCP coefficients,
# no trace cutoff, no quantum-ion terms, no phase extrapolation or blending.
# See THIRD-PARTY.md and LICENSE-LGPL-3.0.txt in this directory.
"""Nonmagnetic fully ionized Coulomb mixture: ii/ie/ee/mixing Helmholtz terms."""
from pathlib import Path
import hashlib
import math
import sys
import numpy as np
from scipy import constants
import is5_jet as ad

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').is_file())
sys.path.insert(0, str(ROOT/'output/is5-thermal-staging'))
import is5_eos as ideal

HERE = Path(__file__).resolve().parent
K, MU = ideal.K, ideal.MU
BOHR = constants.physical_constants['Bohr radius'][0]
COULOMB = constants.elementary_charge**2/(4*math.pi*constants.epsilon_0)
FILES = [Path(__file__), HERE/'is5_jet.py', HERE/'THIRD-PARTY.md', HERE/'LICENSE-LGPL-3.0.txt', HERE/'LICENSE-GPL-3.0.txt',
         ROOT/'IS-5-COULOMB-MISTURA-CONTRATO-PREVIO.md',
         *[ROOT/'output/is5-coulomb-research-20261028'/n for n in
           ['eos22.f', 'mesa26.4.1-skye_coulomb.f90', 'mesa26.4.1-skye_coulomb_liquid.f90', 'pccdr2009.pdf', 'pc2013.pdf']]]
IMPORTED = None


def generation():
    global IMPORTED
    current = {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in FILES}
    if IMPORTED is None:
        IMPORTED = current
    if current != IMPORTED:
        raise ValueError('Restart after Coulomb mixture source or reference changes')
    return dict(schema=1, id='is5:PC-classical-ion-Coulomb-mixture-polarizable', version='0.1.0',
                source_sha256=dict(IMPORTED), ideal_generation=ideal.generation(),
                constants=dict(k_B_J_K=K, atomic_mass_kg=MU, Bohr_radius_m=BOHR,
                               Coulomb_energy_length_J_m=COULOMB, screening_fit_xr_times_rs=.0140047,
                               exchange_fit_theta_times_Gamma_over_rs=.543),
                scope='Classical Caillol OCP + PC electron polarization + EXCOR7 +2009 polarizable mixing fit; no quantum ions, partial ionization, magnetic fields, solids or hydro.')


def ocp_free(g, op=ad):
    """Integral of PC2000/2009 Caillol u_ii/Gamma; stable weak-Gamma form."""
    a1, a2, b1, b2, b3, b4 = -.907347, .62849, .0045, 170., -8.4e-5, .0037
    a3 = -math.sqrt(3)/2-a1/math.sqrt(a2)
    value = g.v if isinstance(g, ad.Jet) else float(g)
    if value < 1e-3:
        # Algebraic series of x*sqrt(1+x²)-asinh(x), sqrt(g)-atan(sqrt(g)),
        # and x-log1p(x). Preserve powers that dominate DH rather than subtracting.
        s = g/a2
        coefficient = 1.
        first = 0*g
        for j in range(10):
            if j:
                coefficient *= (-.5-(j-1))/j
            first += 2*coefficient*s**(j+1.5)/(2*j+3)
        fa = a1*a2*first+2*a3*sum((-1)**j*g**(j+1.5)/(2*j+3) for j in range(10))
        fb = b1*b2*sum((-1)**j*(g/b2)**j/j for j in range(2, 12))+.5*b3*op.log1p(g*g/b4)
    else:
        fa = a1*(op.sqrt(g*(g+a2))-a2*op.asinh(op.sqrt(g/a2)))+2*a3*(op.sqrt(g)-op.atan(op.sqrt(g)))
        fb = b1*(g-b2*op.log1p(g/b2))+.5*b3*op.log1p(g*g/b4)
    return fa+fb


def electron_polarization(z, ge, rs, op=ad):
    a = 1.11*z**.475
    b = .2+.078*math.log(z)**2
    nu = 1.16+.08*math.log(z)
    cdh = z/math.sqrt(3)*((1+z)**1.5-1-z**1.5)
    ctf = 18/175*(12/math.pi)**(2/3)*z**(7/3)*(1-z**(-1/3)+.2*z**(-.5))
    xr = .0140047/rs  # Rounded parameter used by the authors' FSCRliq8 fit.
    gr = op.sqrt(1+xr*xr)
    g1 = 1+.78*op.sqrt(ge/z)/(21+ge*(z/rs)**3)
    g2 = 1+(z-1)/9*(1+1/(.001*z*z+2*ge))*rs**3/(1+6*rs*rs)
    h = (1+.2*xr*xr)/(1+.18*xr*z**(-.25)+.37*z**(-.5)*xr*xr+.2*xr*xr)
    return -ge*(cdh*op.sqrt(ge)+ctf*a*ge**nu*g1*h)/(1+(b*op.sqrt(ge)+a*g2*ge**nu/rs)/gr)


def electron_exchange(rs, ge, op=ad):
    th = .543*rs/ge
    sqth = op.sqrt(th)
    t1, t2 = op.tanh(1/th), op.tanh(1/sqth)
    th2, th3, th4 = th*th, th**3, th**4
    a = .610887*(.75+3.04363*th2-.09227*th3+1.7035*th4)/(1+8.31051*th2+5.1105*th4)*t1
    b = sqth*t2*(.341308+12.070873*th2+1.148889*th4)/(1+10.495346*th2+1.326623*th4)
    d = sqth*t2*(.614925+16.996055*th2+1.489056*th4)/(1+10.10935*th2+1.22184*th4)
    e = th*t1*(.539409+2.522206*th2+.178484*th4)/(1+2.555501*th2+.146319*th4)
    c = (.872496+.025248*op.exp(-1/th))*e
    discr = op.sqrt(4*e-d*d)
    sqge = op.sqrt(ge)
    b2, b3 = b-c*d/e, a-c/e
    c3 = (d/e*b2-b3)/e
    s1 = -c/e*ge
    s2 = -2/e*b2*sqge
    s3 = c3*op.log1p(e*ge+d*sqge)
    s4 = 2/e/discr*(d*b3+(2-d*d/e)*b2)*(op.atan((2*e*sqge+d)/discr)-op.atan(d/discr))
    return s1+s2+s3+s4


def mixing_free(ge, y, z, op=ad):
    if len(set(z)) == 1:
        return 0*ge
    total = sum(y)
    mean = lambda power:sum(v*q**power for v, q in zip(y, z))/total
    z1, z2, z52, z53 = (mean(p) for p in (1, 2, 2.5, 5/3))
    z321 = sum(v*q*(q+1)**1.5 for v, q in zip(y, z))/total
    D = z2/z1**2
    alpha = D**(-.2)
    difference = z321-op.sqrt((z2+z1)**3/z1)
    delta = difference/z52
    a = (2.6*delta+14*delta**3)/(1-alpha)
    gp = a*(ge*z53)**alpha
    return difference*ge*op.sqrt(ge/3)/(1+gp)/(1+.0117*D*D*gp)**(1.5/alpha-1)


def free_energy_components(t, nb, y, z, op=ad):
    """Scalar formula; unconstrained number coordinates are needed by derivatives."""
    ye = sum(v*q for v, q in zip(y, z))
    ae = (3/(4*math.pi*nb*ye))**(1/3)
    rs = ae/BOHR
    ge = COULOMB/(ae*K*t)
    scale = nb*K*t
    return dict(ii=scale*sum(v*ocp_free(ge*q**(5/3), op) for v, q in zip(y, z)),
                ie=scale*sum(v*electron_polarization(q, ge, rs, op) for v, q in zip(y, z)),
                ee=scale*ye*electron_exchange(rs, ge, op),
                mix=scale*sum(y)*mixing_free(ge, y, z, op))


def _validated(t, rho, fractions, mass_numbers, charges):
    t, rho = ideal.number(t), ideal.number(rho)
    if not 1e7 <= t <= 3e7 or not 1e4 <= rho <= 3e5:
        raise ValueError('Coulomb mixture outside declared T/density domain')
    if any(not isinstance(v, (list, tuple)) for v in (fractions, mass_numbers, charges)):
        raise ValueError('Explicit lists of Y/A/Z required')
    if not 1 <= len(fractions) <= 64 or len(fractions) != len(mass_numbers) or len(fractions) != len(charges):
        raise ValueError('Matching1–64 species required')
    if any(type(a) is not int or type(q) is not int or not 1 <= q <= min(a, 26) or a > 300 for a, q in zip(mass_numbers, charges)):
        raise ValueError('Integer1<=Z<=A<=300 with Z<=26 required')
    y = np.array([ideal.number(v) for v in fractions])
    aa, zz = np.array(mass_numbers), np.array(charges)
    if min(y) < -1e-20 or abs(float(aa@y)-1) > 1e-8:
        raise ValueError('Composition outside numerical residue or baryon tolerance')
    base = ideal.mixture(t, rho, float(sum(y)), float(zz@y))
    ne, nb = base['electron_density_m3'], rho/MU
    ae = (3/(4*math.pi*ne))**(1/3)
    rs, ge = ae/BOHR, COULOMB/(ae*K*t)
    th = .543*rs/ge
    present = y > 0
    gamma = ge*zz**(5/3)
    tpt = constants.hbar/(K*t)*np.sqrt(ne*zz*constants.elementary_charge**2/(constants.epsilon_0*aa*MU))
    wave = ideal.H/np.sqrt(2*math.pi*aa*MU*K*t)
    D = float(zz**2@y)*float(sum(y))/float(zz@y)**2
    if len(set(charges)) > 1 and D-1 < 1e-6:
        raise ValueError('Charge mixture too close to pure limit for composition derivatives')
    if max(gamma[present]) > 20 or max(tpt[present]) > .1 or max((nb*y*wave**3)[present]) > .01:
        raise ValueError('Classical liquid/ion quantum domain refused')
    if not .01 <= rs <= 2 or not .01 <= th <= 1e3 or base['fermi_relativity_pF_over_mec'] > .1 or base['thermal_relativity_kT_over_mec2'] > .01:
        raise ValueError('Electron parameter domain refused')
    diagnostics = dict(rs=rs, electron_Gamma=ge, electron_theta_fit=th,
                       ion_Gamma=gamma.tolist(), ion_Tp_over_T=tpt.tolist(), charge_variance_D=D,
                       negative_residue_indices=np.flatnonzero(y < 0).tolist())
    return t, rho, y, base, diagnostics


def correction(t, rho, fractions, mass_numbers, charges):
    t, rho, y, base, diagnostics = _validated(t, rho, fractions, mass_numbers, charges)
    dim = len(y)+2
    tj = ad.exp(ad.Jet.variable(math.log(t), 0, dim))
    nbj = ad.exp(ad.Jet.variable(math.log(rho/MU), 1, dim))
    yj = [ad.Jet.variable(float(v), i+2, dim) for i, v in enumerate(y)]
    parts = free_energy_components(tj, nbj, yj, charges)
    parts['sum'] = sum(parts.values())
    result = {}
    for name, jet in parts.items():
        result[name] = dict(free_energy_J_m3=jet.v, internal_energy_J_m3=jet.v-jet.g[0],
                            pressure_Pa=jet.g[1]-jet.v,
                            heat_capacity_J_m3_K=(jet.g[0]-jet.h[0, 0])/t,
                            du_dnumber_per_baryon_J_m3=(jet.g[2:]-jet.h[0, 2:]).tolist(),
                            neutral_chemical_potential_J=(jet.g[2:]/(rho/MU)).tolist())
        if not all(math.isfinite(v) for v in [jet.v, *jet.g, *jet.h.ravel()]):
            raise RuntimeError('Nonfinite Coulomb free energy derivative')
    return result, base, diagnostics


def evaluate(t, rho, fractions, mass_numbers, charges):
    parts, base, diagnostics = correction(t, rho, fractions, mass_numbers, charges)
    totals = {k:base[k]+parts['sum'][k] for k in ['pressure_Pa', 'internal_energy_J_m3', 'heat_capacity_J_m3_K']}
    z = np.array(charges)
    gradient = base['du_dions_per_baryon_J_m3']+z*base['du_delectrons_per_baryon_J_m3']
    totals['du_dnumber_per_baryon_J_m3'] = (gradient+np.array(parts['sum']['du_dnumber_per_baryon_J_m3'])).tolist()
    if any(not math.isfinite(totals[k]) or totals[k] <= 0 for k in ['pressure_Pa', 'internal_energy_J_m3', 'heat_capacity_J_m3_K']):
        raise RuntimeError('Invalid total Coulomb EOS thermodynamic quantity')
    return dict(temperature_K=t, density_kg_m3=rho, components=parts, ideal=base,
                total=totals, diagnostics=diagnostics, scientific_generation=generation())


generation()
