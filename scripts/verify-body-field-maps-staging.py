"""Check maps/cut sampling and generate independent scientific figures from saved views."""
from pathlib import Path
import copy
import hashlib
import json
import math
import sys
import traceback
import zipfile

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'output/is3-body-view-product/app'
STAGE=ROOT/'output/is3-body-maps-staging'
sys.path[:0]=[str(STAGE),str(APP)]
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import body_field_maps as maps
from body_registry import digest

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    folder=ROOT/'output/is3-body-maps-check-20261024a'
    receipt=ROOT/'evidence/is3-body-maps-check-20261024a.json'
    if folder.exists() or receipt.exists():raise FileExistsError('Preserve map evidence.')
    storage=ROOT/'output/is3-body-view-product/gravity-sessions'
    candidates=[storage/'latest.json',*storage.glob('branches/*/latest.json')]
    fixtures={}
    for path in candidates:
        m=json.loads(path.read_text(encoding='utf-8'));v=m.get('body_field_view')
        if v and v['layer']:
            assert m['manifest_sha256']==digest({k:v for k,v in m.items() if k!='manifest_sha256'})
            reading=v['layer']['reading'];fixtures.setdefault(reading['body_reference_id'],(path,reading))
    assert set(fixtures)=={'sol:naif:399','sol:naif:599'}
    paths=[STAGE/'body_field_maps.py',Path(__file__).resolve(),ROOT/'IS-3-MAPAS-CONTRATO.md']
    paths += [APP/name for name in ['body_field_lines.py','body_field_geometry.py','geomagnetism.py','jrm33.py','jrm33-coefficients.json']]
    paths += [path for path,_ in fixtures.values()]
    hashes={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    owner=sha(ROOT/'user/sessions/latest.json');folder.mkdir()
    with zipfile.ZipFile(folder/'executed-sources-and-fixtures.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for path in paths:archive.write(path,path.relative_to(ROOT).as_posix())
    report={'schema':1,'accepted':False,'completed':False,'source_sha256':hashes,'models':[],
            'image_review':'pending; scientific tests do not accept the generated images.'}
    original=maps.Model.field;calls=0
    def guarded_field(self,position):
        nonlocal calls
        assert self.clearance(position)>=0,'External provider sample attempted.'
        calls+=1
        return original(self,position)
    maps.Model.field=guarded_field
    try:
        for _,(fixture,reading) in sorted(fixtures.items()):
            before=calls;result=maps.build(reading);model=maps.Model(reading)
            shell,cut=result['shell'],result['cut'];rows=shell['samples']
            assert len(rows)==19 and all(len(row)==37 for row in rows)
            assert len(cut['samples'])==65 and all(len(row)==65 for row in cut['samples'])
            seam=max(abs(a-b) for row in rows for a,b in zip(row[0]['field_model_T'],row[-1]['field_model_T']))
            pole=max(abs(a-b) for row in [rows[0],rows[-1]] for p in row for a,b in zip(row[0]['field_model_T'],p['field_model_T']))
            assert seam<=2e-18 and pole<=2e-18
            maximum_plane=maximum_norm=0.;valid=0
            matrix=np.asarray(result['body_to_render']);assert abs(np.linalg.det(matrix)-1)<1e-12
            for row in rows+cut['samples']:
                for p in row:
                    if p is None:continue
                    valid+=1;assert model.clearance(p['position_model_m'])>=0
                    norm=math.hypot(*p['field_model_T']);maximum_norm=max(maximum_norm,abs(norm-math.hypot(*p['field_render_T'])))
                    assert norm==p['field_norm_T']
            assert maximum_norm<=2e-18
            axis=cut['u_axis_model'];normal=[-axis[1],axis[0],0.]
            for row in cut['samples']:
                for p in row:
                    if p is not None:maximum_plane=max(maximum_plane,abs(sum(x*y for x,y in zip(p['position_model_m'],normal))))
            assert maximum_plane/model.radius<=1e-10 and cut['masked_cells']>0
            for iz,z in enumerate(cut['z_m']):
                for ix,u in enumerate(cut['u_m']):
                    expected=model.clearance([u*axis[0],u*axis[1],z])>=0
                    assert (cut['samples'][iz][ix] is not None)==expected
            probes=reading['field_ITRF93_T' if model.name=='IGRF14' else 'field_SystemIII_T']
            assert max(abs(a-b) for a,b in zip(probes,result['probe']['field_model_T']))<=2e-18
            data=folder/(model.name+'-maps.json');data.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
            fig,(ax,cut_ax)=plt.subplots(1,2,figsize=(12,5),constrained_layout=True)
            shell_values=np.array([[p['field_norm_T']*1e6 for p in row] for row in rows])
            im=ax.pcolormesh(shell['east_longitude_deg'],shell['latitude_deg'],shell_values,shading='nearest',cmap='viridis')
            fig.colorbar(im,ax=ax,label='|B interno| (µT)');ax.set(xlabel='Longitude leste (°)',ylabel='Latitude (°)',title=model.name+' · casca amostrada')
            points=cut['samples'];values=np.ma.masked_invalid(np.array([[np.nan if p is None else p['field_norm_T']*1e6 for p in row] for row in points]))
            cut_ax.set_facecolor('#eeeeee');im=cut_ax.pcolormesh(np.array(cut['u_m'])/model.radius,np.array(cut['z_m'])/model.radius,values,shading='nearest',cmap='viridis')
            fig.colorbar(im,ax=cut_ax,label='|B interno| (µT)');cut_ax.set(xlabel='u / raio de referência',ylabel='z / raio de referência',title='Corte meridional · fora do domínio em cinza',aspect='equal')
            fig.suptitle(model.name+' · grau '+str(model.degree)+' · '+reading['epoch']['utc']+'\nComponente interna de modelo; grade finita, sem incerteza local propagada',fontsize=10)
            figures=[]
            for ext in ['png','pdf','svg']:
                path=folder/(model.name+'-maps.'+ext);fig.savefig(path,dpi=160);figures.append({'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path)})
            plt.close(fig)
            report['models'].append({'model':model.name,'degree':model.degree,'fixture':fixture.relative_to(ROOT).as_posix(),
                'seam_error_T':seam,'pole_error_T':pole,'rotation_norm_error_T':maximum_norm,'plane_error_R':maximum_plane/model.radius,
                'valid_cells':valid,'masked_cut_cells':cut['masked_cells'],'provider_calls':calls-before,
                'data':{'path':data.relative_to(ROOT).as_posix(),'sha256':sha(data)},'figures':figures})
        refusals=0
        earth=fixtures['sol:naif:399'][1];jupiter=fixtures['sol:naif:599'][1]
        for source,changes in [(earth,{'kind':'unknown'}),(earth,{'field_ITRF93_T':[0.,0.,0.]}),
                               (earth,{'coordinates':{**earth['coordinates'],'altitude_m':True}}),
                               (earth,{'coordinates':{**earth['coordinates'],'altitude_m':1000001.}}),
                               (earth,{'coordinates':{**earth['coordinates'],'latitude_deg':float('nan')}}),
                               (jupiter,{'degree':True}),(jupiter,{'degree':30}),
                               (jupiter,{'coordinates':{**jupiter['coordinates'],'radius_m':0.}}),
                               (jupiter,{'coordinates':{**jupiter['coordinates'],'longitude_east_deg':-1.}})]:
            try:maps.build({**copy.deepcopy(source),**changes})
            except (ValueError,KeyError,TypeError):refusals+=1
            else:raise AssertionError('Invalid map request accepted.')
        assert refusals==9
        assert all(sha(ROOT/name)==value for name,value in hashes.items()) and sha(ROOT/'user/sessions/latest.json')==owner
        report.update(accepted=True,completed=True,refusals=refusals,source_and_owner_preserved=True,
            scope='Sampled frozen model shell/cut and selected probe in staging; native UI/persistence/performance and manual figure review require separate evidence.')
    except Exception:report['failure']=traceback.format_exc()
    finally:
        maps.Model.field=original
        receipt.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'accepted':report['accepted'],'models':len(report['models']),'refusals':report.get('refusals'),'failure':report.get('failure')}))
    return 0 if report['accepted'] else 1


if __name__=='__main__':raise SystemExit(main())
