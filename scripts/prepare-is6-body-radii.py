"""Curate the four adopted spherical exterior boundaries from the pinned PCK."""
from pathlib import Path
import hashlib
import json
import spiceypy as spice

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    target=ROOT/'output/is6-body-binding-staging';target.mkdir(exist_ok=True)
    path=target/'body-reference-radii.json'
    if path.exists():raise FileExistsError('Preserve radius catalog')
    pck=ROOT/'data/spice/pck00011.tpc'
    spice.furnsh(str(pck));rows=[]
    for identifier,name in [(10,'Sol'),(399,'Terra'),(301,'Lua'),(599,'Júpiter')]:
        dimension,values=spice.bodvcd(identifier,'RADII',3);assert dimension==3
        raw=values.tolist();radii=[x*1000 for x in raw]
        rows.append(dict(reference_id='sol:naif:'+str(identifier),naif_id=identifier,name=name,
                         raw_radii_km=raw,reference_semiaxes_m=radii,exterior_boundary_m=max(radii),
                         boundary_rule='maximum adopted PCK semiaxis; isolated spherical exterior reference',
                         uncertainty=None,uncertainty_status='not_provided'))
    catalog=dict(schema=1,kind='is6_adopted_spherical_reference_boundaries',bodies=rows,
                 provenance=dict(file='data/spice/pck00011.tpc',sha256=sha(pck),
                    source_url='https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/pck00011.tpc',
                    version='PCK00011,2022-12-27',spiceypy=spice.__version__,extractor='bodvcd RADII active kernelpool',
                    original_unit='km',SI_conversion=1000),
                 recipe_sha256=sha(Path(__file__)),contract_sha256=sha(ROOT/'IS-6-FONTE-CORPOS-CONTRATO-PREVIO.md'))
    path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(prepared=True,accepted=False,catalog=str(path),bodies=len(rows)),ensure_ascii=False))


if __name__=='__main__':main()
