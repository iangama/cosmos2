PDS_VERSION_ID       = PDS3                                                   
RECORD_TYPE          = STREAM                                                 
                                                                              
^TEXT                = "AAREADME.TXT"                                         
OBJECT               = TEXT                                                   
  PUBLICATION_DATE   = 2024-12-30                                             
  NOTE               = "AAREADME.TXT describes this volume."                  
END_OBJECT           = TEXT                                                   
END                                                                           
                              Volume JNOFGM_1001                              
                                                                              
               Juno Magnetometer Calibrated (L-3) Jupiter Archive             
                                                                              
==============================================================================
Brief Volume Description                                                      
==============================================================================
                                                                              
This volume contains calibrated CODMAC L-3 (RDR) Magnetometer (FGM) data      
the Juno Jupiter orbital phases, and Jupiter magnetic-field model             
coefficients for published models produced by the Juno MAG team based upon    
Juno observations.                                                            
                                                                              
All data are stored in the 'DATA' branch of the directory tree. The           
calibrated magnetic field data are in the 'JUPITER' directory and are         
provided in ASCII formatted 'Standard Time Series' files (*.sts). The         
model coefficients are provided in the 'MODEL' directory. All data            
files are accompanied by detached PDS labels (*.lbl) which describe the       
content and format of the data files.                                         
                                                                              
Detailed descriptions of the data processing and file and volume formats      
is provided in the Software Interface Specification (SIS), and SIS Addendum.  
Information about the field model data is provided in SIS Addendum 2.         
Copies of these documents are provided in the DOCUMENT/ directory of this     
volume.                                                                       
                                                                              
SPICE kernels used in processing the data files (and documented in the        
labels) are archived by the NAIF Node of the PDS.                             
                                                                              
Users of these data are encouraged to acknowledge both the PDS and the        
principal investigators of the instruments whose data is used in analysis     
in all publications.                                                          
                                                                              
==============================================================================
File Naming Convention                                                        
==============================================================================
Convention:                                                                   
   fgm_jno_LL_CCYYDDDxx_vVV.ext                                               
Where:                                                                        
   fgm - Fluxgate Magnetometer three character instrument abbreviation        
   jno - Juno                                                                 
    LL - CODMAC Data level, for example, l3 for level 3                       
    CC - The century portion of a date, 20                                    
    YY - The year of century portion of a date, 00-99                         
   DDD - The day of year, 001-366                                             
    xx - Coordinate system of data (se = Solar equatorial, ser = Solar        
         equatorial resampled, pc = Planetocentric, ss = Sun-State,           
         pl = Payload)                                                        
   [mm]- [Optional satellite identifier: GA = Ganymede, EA = Europa, IO = Io] 
     v - separator to denote Version number                                   
    VV - version                                                              
   ext - file extension (sts = Standard Time Series (ASCII) file, lbl = Label 
         file)                                                                
Example:                                                                      
   fgm_jno_l3_2014055se_v00.sts                                               
                                                                              
==============================================================================
Volume Set Information                                                        
==============================================================================
                                                                              
This volume is part of the Juno Magnetometer Calibrated Data volume set. This 
volume set includes the following volumes:                                    
                                                                              
    Volume ID     Description                                                 
    ----------------------------------------------------------                
    JNOFGM_1000   Juno Magnetometer Calibrated Cruise Archive                 
    JNOFGM_1001   Juno Magnetometer Calibrated Jupiter Archive                
                                                                              
==============================================================================
File Formats                                                                  
==============================================================================
                                                                              
The data files on this volume are ASCII formatted tables. These files include 
an attached Object Definition Language (ODL) header. The PDS label contains   
information describing                                                        
                                                                              
A data set description, instrument description, and other PDS documents       
are in .CAT files in the CATALOG directory.  In more recent versions of the   
Microsoft Windows operating system the .CAT by default is reserved as         
'Security Catalog.'  The .CAT files contained in this volume are ASCII text   
files, and can be read by any form of text editor.                            
                                                                              
Additional documentation is generally located in the DOCUMENT directory.      
                                                                              
==============================================================================
Errata                                                                        
==============================================================================
                                                                              
Every effort has been made to assure that the data and documentation are of   
the best possible quality. However, mistakes are inevitable. There is a file  
called ERRATA.TXT found at the root level of this volume which contains a list
of known deficiencies or caveats associated with data on this volume at the   
time this volume was produced.                                                
                                                                              
                                                                              
==============================================================================
Volume Contents and Structure                                                 
==============================================================================
                                                                              
This section describes the volume structure and naming conventions. Below is  
a tree diagram of the volume, followed by a description of the directory      
function and key files in each directory.                                     
                                                                              
 JNOFGM_1001 (root directory)                                                 
   |                                                                          
   |- AAREADME.TXT  Describes volume contents, and organization (this file)   
   |                                                                          
   |- ERRATA.TXT    Describes known deficiencies or caveats in the data or    
   |                on this volume.                                           
   |                                                                          
   |- VOLDESC.CAT   High level description of volume contents.                
   |                                                                          
   |                                                                          
   |- [catalog]  PDS catalog files containing information describing the      
   |             data, instrument, instrument personnel, relevant references, 
   |             the spacecraft, and mission.                                 
   |                                                                          
   |- [data]     Contains the data divided into separate subdirectories by    
   |             type, coordinate system, and date.                           
   |                                                                          
   |- [document] Contains documents related to the data and archive           
   |                                                                          
   |- [index]    Contains a list of all data products on this volume.         
   |                                                                          
                                                                              
============================================================================  
Contacts                                                                      
============================================================================  
                                                                              
This volume was produced for the Planetary Data System (PDS) at the           
Planetary Plasma Interactions (PPI) node. The data, and associated metadata   
were supplied by Dr. Jack Connerney and Monte Kaelberer of NASA's             
Goddard Space Flight Center (GSFC). The volume was assembled at the PPI       
node, by Joseph N. Mafi.                                                      
                                                                              
                                                                              
For questions or problems regarding the volume, please contact Joe Mafi at    
the PDS PPI node:                                                             
                                                                              
  Email             jmafi@igpp.ucla.edu                                       
  Telephone         310-206-6073                                              
                                                                              
For question regarding the data, please contact Monte Kaelberer at GSFC:      
                                                                              
  Email             Monte.S.Kaelberer@nasa.gov                                
  Telephone         301-286-0560                                              
                                                                              
For questions regarding PDS Standards or other archives available from the    
PDS, please contact PDS Operator at the PDS Engineering Node (at JPL):        
                                                                              
  Email             pds_operator@jpl.nasa.gov                                 
  Telephone         818-354-4321                                              
                                                                              
The PDS assumes no legal liability for errors on this volume. All users are   
encouraged to verify the correctness of the data prior to submitting any      
publications or other work based on these data. Please report errors on this  
volume to the PDS-PPI node through the ERRATA reporting procedures described  
in the errata.txt file.                                                       
