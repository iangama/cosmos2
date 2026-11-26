
File:            aareadme.txt
Creation Date:   2006-08-04
Revised:         2020-04-11 (NJB)
Revised:         2021-06-25 (NJB)
Revised:         2022-12-14 (BVS)
Revised:         2022-12-27 (NJB) (BVS)
Revised:         2022-01-18 (NJB) (BVS)
Revised:         2023-06-03 (NJB)
Revised:         2023-06-25 (BVS)
Revised:         2024-08-28 (NJB)
Revised:         2024-11-19 (NJB)
Revised:         2025-08-26 (NJB)
Revised:         2026-08-08 (NJB)
Revised:         2026-09-28 (NJB)
Revised:         2026-10-03 (NJB)
Authors:         Nat Bachman (JPL/NAIF)
                 Boris Semenov (JPL/NAIF)



Contents of path pub/naif/generic_kernels/pck
=============================================


Binary Earth PCKs
-----------------

   The following kernels provide Earth orientation data taking
   into account

      Precession
      Nutation
      Nutation corrections
      UT1-TAI
      Polar motion

   See the comment areas of these kernels (using the SPICE utility
   COMMNT) for additional documentation.


   High accuracy EOP-based kernel, updated at least twice per week:

      earth_000101_yymmdd_yymmdd.bpc
      earth_latest_high_prec.bpc

   The first two dates in the first file name are the file's coverage start
   and stop times. The third date in that file name is the epoch of the
   last datum in the source EOP file: earth orientation from this date
   forward is predicted.

   The second file is a copy of the first. The name of this file remains
   unchanged.


   Low accuracy, long term predict kernel. The extended predict region of this
   kernel---the time interval following the end of the predict region of the
   input EOP file---does not estimate changes in UT1-TAI. The dates in the
   file name are the file's coverage start year, the epoch of last datum, 
   and the coverage stop year:

      earth_2026_260806_2126_predict.bpc


   High accuracy, historical kernel. The dates in the file name are  
   the start time and stop time, which is also the epoch of last datum.

      earth_620120_260806.bpc


   Combined high accuracy historical and low-accuracy predict kernel. 
   The dates in the file name are the coverage start year, the epoch of 
   the last datum, and the coverage stop year.

      earth_1962_260806_2126_combined.bpc


Binary Lunar PCKs
-----------------

   DE440 version
   -------------

   DE440 based kernel, providing orientation of Lunar Principal Axis (PA)
   reference frame:

      moon_pa_de440_200625.bpc

   Reference:

   [1]  Ryan S. Park, et al, "The JPL Planetary and Lunar Ephemerides
        DE440 and DE441," The Astronomical Journal, Volume 161, Number 3.
        2021 AJ 161 105.

        URL:

           https://iopscience.iop.org/article/10.3847/1538-3881/abd414/meta

   The data source for this kernel was the NAVIO file

      de440.nio

   The approximate time coverage is

      1550-2650

   This kernel is to be used with the lunar frame kernel

      moon_de440_220930.tf

   This frame kernel is located in the path

      pub/naif/generic_kernels/fk/satellites

   See the cited frame kernel for a detailed discussion of lunar reference
   frames and associated SPICE kernels.


   DE-421 version
   --------------

   DE-421 based kernel, providing orientation of Lunar Principal Axis (PA)
   reference frame:

      moon_pa_de421_1900-2050.bpc

   The data source for this kernel was the NAVIO file

      de421.nio

   The approximate time coverage is indicated by the dates in the
   file name.

   This kernel is to be used with the lunar frame kernel

      moon_080317.tf

   This frame kernel is located in the path

      pub/naif/generic_kernels/fk/satellites

   See the cited frame kernel for a detailed discussion of lunar reference
   frames and associated SPICE kernels.


   Version preceding DE-421
   ------------------------

   DE-418 based kernel, providing orientation of Lunar Principal Axis (PA)
   reference frame:

      moon_pa_de418_1950-2050.bpc

   The data source for this kernel was the NAVIO file

      de418.nio

   The approximate time coverage is indicated by the dates in the
   file name.

   This kernel is to be used with the lunar frame kernel

      moon_071218.tf

   This frame kernel is located in the path

      pub/naif/generic_kernels/fk/satellites

   See the cited frame kernel for a detailed discussion of lunar reference
   frames and associated SPICE kernels.


Generic text PCKs
-----------------

   These kernels contain orientation data for planets, natural satellites,
   the Sun, and selected asteroids. The latest files, released December
   27, 2022, are:

      pck00011.tpc
      pck00011_n0066.tpc

   Reading the Mars system orientation data in pck00011.tpc *requires*
   SPICE Toolkit version N0067 (current as of December 2022) or later.

   The file pck00011_n0066.tpc is compatible with SPICE Toolkit versions
   N0066 and earlier. In this file, orientation data for Phobos has been
   modified slightly in order to be usable by these earlier Toolkit versions.
   Kernel variables for the Mars system have been modified, but only the
   orientation of Phobos is affected. See the documentation in the file for
   details. All other data in the file match those in pck00011.tpc.

   Most data in both files are from article

      Archinal, B.A., Acton, C.H., A'Hearn, M.F., Conrad, A.,
      Consolmagno, G.J., Duxbury, T., Hestroffer, D., Hilton,
      J.L., Kirk, R.L., Klinoner, S.A., McCarthy, D.,
      Meech, K., Oberst, J., Ping., J., Seidelmann, P.K., Tholen,
      D.J., Thomas, P.C., and Williams, I.P., "Report of the IAU
      Working Group on Cartographic Coordinates and Rotational
      Elements: 2015," Celestial Mechanics and Dynamical Astronomy
      130, Article number 22 (2018).
      DOI: https://doi.org/10.1007/s10569-017-9805-5

   This article presents data for some bodies, including Mercury, Mars
   and its satellites, and Neptune, that are very different from
   those of the previous IAU WGCCRE report. NAIF recommends careful
   inspection of the data prior to use.

   The preceding version of the generic text PCK file is

      pck00010.tpc

   which was released September 21, 2011. Most data in that file are from
   the article

      Archinal, B.A., A'Hearn, M.F., Bowell, E., Conrad, A.,
      Consolmagno, G.J., Courtin, R., Fukushima, T.,
      Hestroffer, D., Hilton, J.L., Krasinsky, G.A.,
      Neumann, G., Oberst, J., Seidelmann, P.K., Stooke, P.,
      Tholen, D.J., Thomas, P.C., and Williams, I.P.
      "Report of the IAU Working Group on Cartographic Coordinates
      and Rotational Elements: 2009."

   All of these kernels are text files; see the documentation in the files for
   details concerning the files' contents.

   WARNING:

     Mars system orientation data in the PCK files pck00011*.tpc listed
     above are incompatible with corresponding data from older PCK files.

     Loading either of the pck00011*.tpc files, and then loading older
     PCK files, including

         mars_iau2000_v0.tpc
         pck00010.tpc

     will make Mars system orientation data from the later loaded files
     unusable. After this sequence of kernel loads, calls to SPICE APIs
     that require the orientation of Mars, Phobos, or Deimos, for example
     calls to the SPICE APIs PXFORM or SXFORM, will cause the error
     SPICE(INSUFFICIENTANGLES) to be signaled.

     Mars system orientation data in the file pck00011.tpc cannot be
     used with SPICE Toolkit versions earlier than N0067.

   The text PCK

      mars_iau2000_v1.tpc

   is provided to work around this compatibility problem. See the
   section "Mars system text PCKs" below.


Mars system text PCKs
---------------------

   PCKs containing data for the Mars Konopliv 2026 orientation model 
   described in the article

      Alex. S. Konopliv, Ryan S. Park, Sebastien Le Maistre, 
      Marie Yseboodt, and Rose-Marie Baland, "Updated Mars 
      Orientation and Gravity Field and Indication of Decadal 
      Changes in Rotation Rate." The Planetary Science Journal, 
      2026, DOI: 10.3847/PSJ/ae9ba7.

   which is available at the URL 

      https://iopscience.iop.org/article/10.3847/PSJ/ae9ba7

   were released October 3, 2026. These files are

      mars_konopliv_2026_v1.tpc 
      mars_konopliv_2026_n0066_v1.tpc 

   These kernels also contain data for rotation models for Phobos 
   and Deimos, and triaxial ellipsoid radii for all three bodies. 
   The satellite rotation data are copied from the PCKs 

      pck00011.tpc 
      pck00011_n0066.tpc 

   respectively, with the exception that the typo described in 
   the "Errata" section below has been corrected. See the notes above 
   regarding these latter PCKs.

   The Mars PCKs inherit the interoperability limitations of the generic 
   PCKs pck00011*.tpc; these limitations are described in the 
   "Generic text PCKs" section above. 
   
   A new PCK file 

      mars_rotation_reset_v1.tpc 

   has been provided to mitigate problems arising from loading PCKs
   containing incompatible Mars system rotation models. 

   See the comments in the Mars Konopliv 2026 PCKs and in this file,
   in the section "Mars rotation reset PCK."

   The file

      mars_iau2000_v1.tpc

   was released on January 12, 2023.

   This file contains data only for Mars and its natural satellites.
   Orientation data in this file are identical to those in

      mars_iau2000_v0.tpc
      pck00010.tpc

   Body shape data in this file are identical to those in

      pck00011.tpc
      pck00011_n0066.tpc

   This file was created to work around compatibility problems
   with Mars system orientation data in the files pck00011*.tpc
   listed above.

   This update of mars_iau2000_v0.tpc contains variables that enable
   Mars system orientation data in this file to be safely used when
   this file is loaded after either pck00011.tpc or pck00011_n0066.tpc.

   After this file is loaded, it is safe to load other, older PCKs
   and use the Mars system orientation data from those files, even
   if one of the pck00011*.tpc files had been loaded before this file.

   This kernel may be used by any SPICE Toolkit version.


Mars rotation reset PCK 
-----------------------

   The PCK file 

      mars_rotation_reset_v1.tpc 

   enables programs to load any of the PCKs 

      mars_konopliv_2026_v1.tpc 
      mars_konopliv_2026_n0066_v1.tpc
      pck00011.tpc 
      pck00011_n0066.tpc 

   and later load and use Mars system rotation models from 
   incompatible PCKs, without first unloading the kernels listed 
   above. This is done by loading the reset PCK after use of the 
   listed kernels, before loading any incompatible PCKs. See the 
   documentation in the reset PCK for details.


NORAD two-line element kernel
-----------------------------

   This kernel supports creation of SPK files containing
   type 10 (NORAD two-line element) segments:

      geophysical.ker

   See the MKSPK User's Guide for further information.


GM/mass kernels
---------------

   The file

      gm_de440.tpc

   gives "GM" (gravitational constant times mass) values for the
   sun, planets, planetary system barycenters, and selected satellites
   asteroids. These values are based on DE-440 and latest satellite
   ephemeris release memos. This file combines data from two PCKs
   provided to NAIF on 11/28/22 and 11/30/22 by Jon D. Giorgini,
   Solar System Dynamics group. See file comments for details.

   The file

      gm_de431.tpc

   gives "GM" (gravitational constant times mass) values for the
   sun, planets, planetary system barycenters, and selected satellites
   asteroids. These values are based on DE-431 and latest satellite
   ephemeris release memos. This file was provided to NAIF on 04/16/14
   by Jon D. Giorgini, Solar System Dynamics group.

   The file

      de-403-masses.tpc

   gives "GM" (gravitational constant times mass) values for the
   sun, planets, and planetary system barycenters.  These values
   are based on DE-403.

   The file

      Gravity.tpc

   contains data of uncertain provenance.  Use at your own risk.
   NAIFers:  consider deleting this file?


EARTH_FIXED Alias Kernel
------------------------

   This is a kernel used to map the reference frame alias
   EARTH_FIXED to a specific reference frame:

      earth_fixed.tf

   Using the alias EARTH_FIXED in code allows applications to
   select the earth-fixed frame to use at run time via the
   frame specification in this kernel.  The default association
   is with the frame

      IAU_EARTH

   The file contains instructions for changing the association to
   ITRF93.


Errata 
======

   Known errors in the PCKs provided in this directory as well as in
   the older PCKs provided in the a_old_versions/ subdirectory are
   listed below.

   
   pck00011.tpc
   ------------

   On line 1294 of pck00011.tpc the constant 

      12.711923222

   that appears in the expression for angle M5 should be 

      12.71192322

   The resulting error in the prime meridian angle of Phobos
   is at round-off level.


   pck00003.tpc 
   ------------

   On line 745 of this file, the term  
   
      +  1.75 sin (N)

   in the expression for the prime meridian angle of Neptune should be 

      -  1.75 sin (N)

   This is an error in the file's comments; it does not affect 
   computations performed by the SPICE Toolkit.


Getting help
============

   SPICE tutorials are available on the NAIF web site:

      http://naif.jpl.nasa.gov/naif/

   The following tutorials may be of particular interest:

      Intro to Kernel Files
      PCK (Planetary cartographic and physical constants)
      FK (Reference frame specifications)

   Also see the following Required Reading documents provided
   with the SPICE Toolkit:

      Frames
      Kernel
      PCK

   Many SPICE kernels contain internal documentation. Text kernels may
   be viewed with a text editor or web browser. Comments in binary
   kernels may be viewed using the SPICE utility COMMNT. Coverage of
   binary PCKs may be viewed using the SPICE utility SPACIT. See the
   COMMNT and SPACIT User's Guides (provided with the SPICE Toolkit)
   for details.