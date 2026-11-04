# Solar Models, ICE-2023 / SF-III.

---

> Developed by Y. Herrera (herrera@ice.csic.es), and A. Serenelli (aldos@ice.csic.es)

> Institute of Space Sciences (ICE - CSIC),
> Barcelona, Spain.

---

## Introduction

  This package contains data from a variety of up-to-date Solar Models as well as a routine to generate variations of them in a Linear Solar Model (LSM) approximation. The provided data includes the solar inner structure for several physical variables and abundances for chemical species of interest, as well as neutrino outflows and distributions from different sources and their correlation matrices.

  
  The available Solar Models differ in the proposed solar composition, and were all computed with a modified version of *GarStEC*, using the latest prescription for nuclear reaction rates and opacity data from the upcoming Solar Fusion Cross-sections III review article (SF-III), and references therein. The proposed solar compositions are (in chronological order):

   - "GS98" &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;::  Grevesse & Sauval (1998), Space Sci. Rev., 85, 161.
   - "AGSS09" &nbsp;::  Asplund et al. (2009), ARA&A, 47, 481.
   - "C11" &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;::  Caffau et al. (2011), Sol. Phys., 268, 255.
   - "AAG21" &nbsp;&nbsp;::  Asplund et al. (2021), A&A 653, A141.
   - "MB22m" &nbsp;::  Magg et al. (2022), A&A 661, A140. (Meteoritic)
   - "MB22p" &nbsp;&nbsp;::  Magg et al. (2022), A&A 661, A140. (Photospheric)

---

## Package contents


### `SolarModels/` directory

Contains solar models data files for each proposed solar composition. 

- `struct+nu_` files ::
Radial profiles of several physical variables of interest, with a grid step of 5`x`10<sup>-4</sup> *R_sun*. Tabulated variables are:

    + *R_sun, M_sun, L_sun*: radial coordinate, mass coordinate and luminosity in solar units;
        
    + *logR, logT, logP, logRho*: logarithms of radial coordinate (cm), temperature (K), pressure  (g&nbsp;cm<sup>-1</sup>&nbsp;s<sup>-2</sup>), and mass density (g&nbsp;cm<sup>-3</sup>);
        
    + *Csound*: sound speed in cm&nbsp;s<sup>-1</sup>;
     
    + *nu_\**: normalized neutrino generation distributions for each source (pp, pep, hep, 7Be, 8B, 13N, 15O, 17F) in number fraction per second;
    
    + *log_ne*: logarithm of free electron density in units of N<sub>A</sub>&nbsp;cm<sup>-3</sup>;
    
    + Elemental/isotopic mass fractions of several species of interest.

- `fluxes_` files ::
Neutrino fluxes (number per second) and their correlation matrices.

- `Cs_obs.dat` ::
Solar sound speed profile from helioseismic inversion of BiSON data (used by the variations routine to calculate deviations from solar data).



### `PLD/` directory

Partial logarithmic derivatives (PLDs) of certain quantities with respect to nuclear reaction rates, elements abundances and other input solar parameters, for each proposed solar composition.

- `pwrlaws_` files :
    PLDs of neutrino fluxes, surface He, and convective zone base location

- `dlc_dlz_` files :
    PLDs of sound speed profiles.

    
###  `SSM-variations` script

 This routine calculates variations of some predicted quantities of interest, for all the available Solar Models, with respect to desired input variations in nuclear reaction rates, solar composition, and other solar parameters.  The predicted quantities include: neutrino fluxes, surface He mass fraction, the location of the base of the convective envelope, as well as sound speed profile variations.
 
  It comes in two versions:

- `SSM-variations.ipynb`: *Jupyter Notebook* that requires *Jupyter Lab*  to open or edit (see: https://jupyter.org/install), with *IRKernel* to run (see: https://irkernel.github.io/installation/).
- `SSM-variations.R`: standalone *R* script that can be edited with any plain text editor and requires only a basic *R* installation to run (which is also required for _IRkernel_). For installation, see: https://cran.r-project.org/bin

 You may open any of them for more details and further instructions.


---
