"""Write the predeclared spatial-metric fixtures before executing the model."""
from pathlib import Path
import hashlib
import json
import math

ROOT=Path(__file__).resolve().parents[1]


def main():
    folder=ROOT/'output/is6-spatial-fixtures-20261101a'
    if folder.exists():raise FileExistsError('Preserve fixtures')
    folder.mkdir();c=299792458;samples=[];intervals=[]
    gm=c*c/2
    for u in [1e-18,1e-12,1e-9,1e-6,1e-3,.1,.5,.9,.99]:
        samples.append(dict(source=dict(GM_m3_s2=gm,material_radius_m=0),radius_m=1/u))
    for gm in [1.,3.986004354360959e14,1.3271244004193938e20,1e26]:
        rs=2*gm/(c*c)
        for factor in [1000.,1e6]:
            r=factor*rs
            if 1<=r<=1e20:samples.append(dict(source=dict(GM_m3_s2=gm,material_radius_m=0),radius_m=r))
    for a,b in [(1.01,2.),(2.,8.),(1e6,8e6)]:
        p=dict(GM_m3_s2=c*c/2,material_radius_m=0)
        intervals.append(dict(source=p,inner_m=a,outer_m=b))
        intervals.append(dict(source=p,inner_m=a,outer_m=a*(1+1e-9)))
    angle=math.pi/7;co,si=math.cos(angle),math.sin(angle)
    bases=[[[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]],[[1.,0.,0.],[0.,0.,1.],[0.,-1.,0.]],
           [[0.,1.,0.],[0.,0.,1.],[1.,0.,0.]],[[co,si,0.],[-si,co,0.],[0.,0.,1.]]]
    result=dict(schema=1,accepted=False,samples=samples,intervals=intervals,bases=bases,
                flat_source=dict(GM_m3_s2=0.,material_radius_m=0.),centers=[[0.,0.,0.],[1e9,-2e9,3e9]],
                radial_counts=[33,65,129,257],azimuth_sectors=96,amplifications=[0.,1.,1000.],
                coordinate_precision='Reference consumes the effective binary64 inputs.',
                contract_sha256=hashlib.sha256((ROOT/'IS-6-MALHA-ESPACIAL-CONTRATO-PREVIO.md').read_bytes()).hexdigest())
    (folder/'fixtures-before-execution.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(prepared=True,accepted=False,samples=len(samples),intervals=len(intervals),folder=str(folder))))


if __name__=='__main__':main()
