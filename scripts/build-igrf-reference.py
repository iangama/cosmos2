"""Compile the original BGS routine with locally extracted GNU Fortran packages."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT=Path(__file__).resolve().parents[1];base=ROOT/'.tooling/fortran'
for deb in sorted(base.glob('*.deb')):
    subprocess.run(['dpkg-deb','-x',str(deb),str(base)],check=True)
original=(ROOT/'.upstream/igrf14/igrf14.f').read_text()
start=original.lower().index('\n      subroutine igrf14syn')+1
(ROOT/'.upstream/igrf14/reference-subroutine.f').write_text(original[start:])
driver='''program reference
 implicit none
 integer :: ios,isv,itype
 real(8) :: year,alt,colat,lon,x,y,z,f
 do
  read(*,*,iostat=ios) isv,year,itype,alt,colat,lon
  if(ios/=0) exit
  call igrf14syn(isv,year,itype,alt,colat,lon,x,y,z,f)
  write(*,'(4(es25.17,1x))') x,y,z,f
 end do
end program reference
'''
(ROOT/'.upstream/igrf14/reference-driver.f90').write_text(driver)
compiler=base/'usr/bin/x86_64-linux-gnu-gfortran-13'
version=subprocess.run([str(compiler),'--version'],check=True,capture_output=True,text=True).stdout.splitlines()[0]
flags=['-B'+str(base/'usr/lib/gcc/x86_64-linux-gnu/13')+'/',
       '-B/usr/lib/gcc/x86_64-linux-gnu/13/','-O2','-std=legacy','-static-libgfortran']
subprocess.run([str(compiler),*flags,str(ROOT/'.upstream/igrf14/reference-subroutine.f'),
                str(ROOT/'.upstream/igrf14/reference-driver.f90'),'-o',str(base/'igrf-reference')],check=True)
record={'compiler':version,'flags':flags,'packages':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in base.glob('*.deb')},
        'source_sha256':hashlib.sha256((ROOT/'.upstream/igrf14/igrf14.f').read_bytes()).hexdigest(),
        'executable_sha256':hashlib.sha256((base/'igrf-reference').read_bytes()).hexdigest(),
        'scope':'Local extracted Ubuntu compiler packages; no system install. System GCC13 linker/runtime support. BGS original subroutine, own stream wrapper; static Fortran runtime.'}
(ROOT/'evidence/igrf-reference-build.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
