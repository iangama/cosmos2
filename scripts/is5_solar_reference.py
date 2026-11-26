"""Strict, lossless numeric import of pinned B23 tables; no stellar evolution."""
from pathlib import Path
import hashlib
import math
import statistics
import zipfile

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'output/is5-solar-reference-staging/SolarModels_ICE2023_v1.2.zip'
EXPECTED_SHA='382037d76ed35c9b50a4094d3ada3c90284af025c3235b49cda9d932699f87d0'
COLUMNS=tuple('R_sun mass_sun L_sun logR logT logP logRho Csound dm nu_pp nu_pep nu_hep nu_7Be nu_8B nu_13N nu_15O nu_17F log_ne H1 He4 He3 C12 C13 N14 N15 O16 O17 O18 Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni'.split())
MODELS=('GS98','AGSS09','AAG21','C11','MB22m','MB22p')
COVERED={'H1':1,'He3':3,'He4':4,'C12':12,'C13':13,'N14':14,'N15':15,'O16':16,'O17':17}
NA=6.02214076e23


def original(model):
    if model not in MODELS:raise ValueError('Pinned solar model name required')
    raw=ARCHIVE.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=EXPECTED_SHA:raise ValueError('Original reference archive changed')
    name='SolarModels/struct+nu_SF3_'+model+'.dat'
    with zipfile.ZipFile(ARCHIVE) as z:return name,z.read(name)


def parse(raw):
    if not isinstance(raw,bytes):raise ValueError('Original table bytes required')
    lines=raw.decode('ascii').splitlines()
    if len(lines)!=2002 or tuple(lines[0].lstrip('# ').split())!=COLUMNS:raise ValueError('Original47-column/2001-row schema differs')
    rows=[]
    for line in lines[1:]:
        fields=line.split()
        if len(fields)!=47:raise ValueError('Incomplete solar row')
        values=[float(x) for x in fields]
        if not all(math.isfinite(x) for x in values):raise ValueError('Nonfinite reference value')
        rows.append(values)
    offsets=[row[3]-math.log10(row[0]) for row in rows if row[0]>0]
    radius_offset=statistics.median(offsets)
    flags=[];derived=[];last_radius=last_mass=-math.inf
    for i,row in enumerate(rows):
        d=dict(zip(COLUMNS,row));radius=d['R_sun'];mass=d['mass_sun'];lum=d['L_sun']
        if radius<=last_radius or abs(radius-i*.0005)>1e-12:raise ValueError('Solar radius grid differs')
        if mass<last_mass or not -1e-12<=mass<=1+5e-6 or (i>0 and mass<0):raise ValueError('Solar mass coordinate differs')
        if lum<0 and (i!=0 or abs(lum)>1e-12):raise ValueError('Negative reference luminosity beyond central residue')
        fractions=row[18:]
        if min(fractions)<0 or max(fractions)>1 or math.fsum(fractions)>1+5e-6:raise ValueError('Reference mass fractions differ')
        quality=[]
        if radius==0:quality.append('central_interpolation_residue')
        elif abs(d['logR']-math.log10(radius)-radius_offset)>.002:quality.append('inconsistent_log_radius')
        if any(d[c]<0 for c in COLUMNS[8:17]):quality.append('signed_auxiliary_source_values')
        T=10**d['logT'];rho=10**d['logRho']*1000;pressure=10**d['logP']*.1;ne=10**d['log_ne']*NA*1e6
        if min(T,rho,pressure,ne,d['Csound'])<=0:raise ValueError('Nonpositive converted structure variable')
        covered=math.fsum(d[n] for n in COVERED);uncovered=1-covered
        if uncovered<0:raise ValueError('Covered isotope mass exceeds total')
        eligible=1e7<T<1.6e7 and 1e4<=rho<=3e5 and not any(q in quality for q in ('central_interpolation_residue','inconsistent_log_radius'))
        derived.append(dict(temperature_K=T,density_kg_m3=rho,pressure_Pa=pressure,electron_density_m3=ne,
            sound_speed_m_s=d['Csound']*.01,absolute_radius_from_log_m=10**d['logR']*.01,
            covered_mass_fraction=covered,uncovered_mass_fraction=uncovered,
            covered_ions_per_baryon=math.fsum(d[n]/a for n,a in COVERED.items()),eligible=eligible))
        flags.append(quality);last_radius=radius;last_mass=mass
    return dict(columns=list(COLUMNS),raw_values=rows,derived=derived,flags=flags,
                log_radius_offset_median=radius_offset,scope='Original B23 reference values preserved; no renormalization or evolution.')


def load(model):
    name,raw=original(model)
    return dict(model=model,source_member=name,source_sha256=hashlib.sha256(raw).hexdigest(),**parse(raw))
