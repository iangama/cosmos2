"""Prepare the six-moon scene and extend the accepted Atlas controls in separate staging."""
import ast
import copy
import hashlib
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'output/is6-planet-navigation-product0.24.0/app'
STAGE=ROOT/'output/is6-principal-moons-navigation-staging'
MODEL=ROOT/'output/is6-principal-moons-model-20261111a'
NEW=['Io','Europa','Ganymede','Callisto','Enceladus','Titan']
PARENTS={node:'Jupiter' if node in NEW[:4] else 'Saturn' for node in NEW}
ORDER=['Mercury','Venus','Earth','Moon','System','Mars','Jupiter',*NEW[:4],
       'Saturn','Enceladus','Titan','Uranus','Neptune','Galaxy']
sys.path.insert(0,str(BASE))
import atlas
lua=SourceFileLoader('moons_scene_lua',str(ROOT/'scripts/prepare-is6-planet-navigation-scene.py')).load_module().lua
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def change(text,before,after):
    if text.count(before)!=1:raise ValueError('Expected one source anchor: '+before)
    return text.replace(before,after)


def main():
    if STAGE.exists():raise FileExistsError('Preserve prepared moon scene')
    model=json.loads((MODEL/'catalog-data.json').read_text())
    assert json.loads((ROOT/'evidence/is6-principal-moons-verification-20261111a.json').read_text())['accepted']
    assert json.loads((ROOT/'evidence/is6-principal-moons-horizons-20261111b.json').read_text())['accepted']
    visual_path=ROOT/'evidence/is6-principal-moons-visuals-20261111a.json'
    visuals=json.loads(visual_path.read_text());assert visuals['completed'] and set(visuals['maps'])==set(NEW)
    assert all(v['all_pixels_decoded'] and sha(ROOT/v['path'])==v['sha256'] for v in visuals['maps'].values())
    STAGE.mkdir();ui=STAGE/'ui';ui.mkdir()
    scene=copy.deepcopy(json.loads((BASE/'planet_scene.json').read_text()))
    old_nodes=set(scene['bodies']);assert len(old_nodes)==10
    atlas.initialize();nodes=[]
    for item in model['bodies']:
        node=item['node']
        if node not in NEW:continue
        radii=(atlas.SPICE.bodvrd(item['naif_id'],'RADII',3)[1]*1000).tolist()
        texture=visuals['maps'][node]
        scene['bodies'][node]=dict(name=item['name'],target=item['naif_id'],kind='moon',radii_m=radii,
            frame=item['rotation_frame'],texture=texture,parent=PARENTS[node])
        nodes.append(dict(Identifier=node,Transform=dict(
            Translation=dict(Type='SpiceTranslation',Target=item['naif_id'],Observer='0',Frame='GALACTIC'),
            Rotation=dict(Type='SpiceRotation',SourceFrame=item['rotation_frame'],DestinationFrame='GALACTIC')),
            Renderable=dict(Type='RenderableGlobe',Radii=radii,PerformShading=True,LightSourceNode='Sun',
                Layers=dict(ColorLayers=[dict(Identifier='ReferenceMap',Name='Mapa visual OpenSpace',
                    FilePath='__ROOT__/'+texture['path'],Enabled=True)])),GUI=dict(Name=item['name'],Path='/Cosmos2/Luas')))
    assert len(nodes)==6 and len(scene['bodies'])==16
    paths=[item['relative_kernel'] for item in model['bodies'] if item['node'] in NEW]
    lines=['asset.require(openspace.absPath("${COSMOS2}/output/is6-planet-navigation-staging/planet_scene.asset"))',
        'local project = openspace.absPath("${COSMOS2}")',
        'local kernels = '+lua(['__ROOT__/'+p for p in paths]).replace('"__ROOT__/','project .. "/'),
        'local nodes = '+lua(nodes).replace('"__ROOT__/','project .. "/'),
        'asset.onInitialize(function() openspace.spice.loadKernel(kernels);for _,node in ipairs(nodes) do openspace.addSceneGraphNode(node) end end)',
        'asset.onDeinitialize(function() for index=#nodes,1,-1 do openspace.removeSceneGraphNode(nodes[index].Identifier) end;openspace.spice.unloadKernel(kernels) end)',
        'asset.meta={Name="Cosmos2 principal moons",Author="Cosmos2 / JPL / OpenSpace",Description="Geometric moon centers, original fixed maps and general IAU rotations."}']
    asset=STAGE/'moon_scene.asset';asset.write_text('\n'.join(lines)+'\n',encoding='utf8')
    profile=json.loads((ROOT/'output/is6-planet-navigation-staging/atlas.profile').read_text())
    profile['assets'].append('${COSMOS2}/output/is6-principal-moons-navigation-staging/moon_scene.asset')
    profile['meta'].update(name='Cosmos2 — planetas e luas',version='0.25.0',
        description='Sol, oito planetas e sete luas; centros físicos geométricos e rotações IAU gerais,1995–2049.')
    profile_path=STAGE/'atlas.profile';profile_path.write_text(json.dumps(profile,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    cfg=(ROOT/'config/cosmos2.cfg').read_text()+'\nProfile = project .. "/output/is6-principal-moons-navigation-staging/atlas.profile"\nPerProfileCache = false\n'
    (STAGE/'cosmos2.cfg').write_text(cfg,encoding='utf8')
    scene.update(scene_asset=dict(path=asset.relative_to(ROOT).as_posix(),sha256=sha(asset)),
        profile_sha256=sha(profile_path),recipe_sha256=sha(Path(__file__)),
        foundation_scene_sha256=sha(BASE/'planet_scene.json'),visual_acquisition_sha256=sha(visual_path))
    (STAGE/'planet_scene.json').write_text(json.dumps(scene,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    provider=(MODEL/'is6_principal_moons_catalog.py').read_text()
    (STAGE/'is6_principal_moons_catalog.py').write_text(provider,encoding='utf8')
    adapter=(BASE/'planet_atlas.py').read_text().replace('import is6_planet_catalog_v2 as catalogue','import is6_principal_moons_catalog as catalogue')
    adapter=adapter.replace('pinned eight-planet scene.','pinned scene of eight planets and seven moons.').replace('as dez posições','as dezesseis posições')
    (STAGE/'moon_atlas.py').write_text(adapter,encoding='utf8')
    nav=(BASE/'planet_navigation.py').read_text().replace('from planet_atlas import','from moon_atlas import')
    (STAGE/'moon_navigation.py').write_text(nav,encoding='utf8')
    for p in STAGE.glob('*.py'):ast.parse(p.read_text())

    definitions=(BASE/'ui/planet-definitions.js').read_text()
    match=re.search(r'const planetInfo = (\{.*?\});\nconst planetViews = (\{.*?\});\nconst physicalTargets',definitions,re.S)
    assert match;info,views=[json.loads(v) for v in match.groups()]
    for node in NEW:
        item=scene['bodies'][node];image=item['texture'];radius=max(item['radii_m'])
        name=item['name'];parent='Júpiter' if PARENTS[node]=='Jupiter' else 'Saturno'
        info[node]=dict(name=name,target=item['target'],radius_m=radius,
            search=('lua satélite '+name+' '+node+' '+parent+' '+PARENTS[node]).lower(),
            content=f'Mapa visual fixo OpenSpace: {image["width"]} × {image["height"]} pixels. Época de aquisição desconhecida.')
        number=format(radius/1000,',.3f').rstrip('0').rstrip('.').replace(',','_').replace('.',',').replace('_','.')
        views[node]=dict(anchor=node,position=[0,-4*radius,2.5*radius],name=name,radius=number+' km',
            measure='MAIOR SEMIEIXO DE REFERÊNCIA',surface='Mapa visual OpenSpace',
            description='Lua de '+parent+'. Centro físico JPL, forma PCK00011 e mapa fixo; época de aquisição desconhecida.')
    definitions='const planetInfo = '+json.dumps(info,ensure_ascii=False,indent=2)+';\n'
    definitions+='const planetViews = '+json.dumps(views,ensure_ascii=False,indent=2)+';\n'
    definitions+='const physicalTargets = Object.keys(planetInfo);\nconst targetOrder = '+json.dumps(ORDER)+';\n'
    (ui/'planet-definitions.js').write_text(definitions,encoding='utf8')
    for name in ['app.js','navigation.js','style.css','content.html','content.js','planet-catalog.html','planet-catalog.js','index.html']:
        (ui/name).write_bytes((BASE/'ui'/name).read_bytes())
    index=(ui/'index.html').read_text(encoding='utf8')
    for parent in ['Jupiter','Saturn']:
        children=[n for n in NEW if PARENTS[n]==parent]
        tree=''.join('<button data-tree-target="'+n+'">↳ ↳ '+info[n]['name']+'</button>' for n in children)
        anchor=re.search(r'<button data-tree-target="'+parent+r'">.*?</button>',index).group(0)
        index=change(index,anchor,anchor+tree)
        buttons=''
        for node in children:
            parent_name=info[parent]['name']
            buttons+='\n      <button class="destination" data-target="'+node+'" data-kind="moon"><span class="planet '+node.lower()+'"></span><span><b>'+info[node]['name']+'</b><small>Sol › '+parent_name+' › '+info[node]['name']+' · lua</small></span><span class="arrow">↗</span></button>'
        anchor=re.search(r'<button class="destination[^"\n]*" data-target="'+parent+r'".*?</button>',index).group(0)
        index=change(index,anchor,anchor+buttons)
    index=index.replace('Oito planetas, Lua e modelo galáctico','Oito planetas, sete luas e modelo galáctico').replace('Oito planetas e Lua · estados geométricos.','Oito planetas e sete luas · estados geométricos.')
    (ui/'index.html').write_text(index,encoding='utf8')
    css=(ui/'style.css').read_text()+('\n.io{background:radial-gradient(circle at 35% 35%,#e7d78e,#b79c58 55%,#463b25)}'
        '.europa{background:radial-gradient(circle at 35% 35%,#eee7cb,#b2a382 55%,#494134)}'
        '.ganymede{background:radial-gradient(circle at 35% 35%,#c5b7a2,#847665 55%,#34312d)}'
        '.callisto{background:radial-gradient(circle at 35% 35%,#b5afa3,#736e61 55%,#2c2b28)}'
        '.enceladus{background:radial-gradient(circle at 35% 35%,#eef5f5,#acb9bd 55%,#46535b)}'
        '.titan{background:radial-gradient(circle at 35% 35%,#d9bd85,#96774d 55%,#43382b)}\n')
    (ui/'style.css').write_text(css,encoding='utf8')
    content=(ui/'content.html').read_text()
    options=''.join('<option value="'+info[n]['target']+'">'+info[n]['name']+' · NAIF'+info[n]['target']+'</option>' for n in NEW)
    content=re.sub(r'(<select id="reference-body">)(.*?)(</select>)',lambda m:m[1]+m[2]+options+m[3],content,flags=re.S)
    content=content.replace('Catálogo dos oito planetas','Catálogo de planetas e luas')
    (ui/'content.html').write_text(content,encoding='utf8')
    content_js=(ui/'content.js').read_text()
    content_js=change(content_js,"if(['10','199','299','399','301','499','599','699','799','899'].includes(body))",
        'if('+json.dumps([b['naif_id'] for b in model['bodies']])+'.includes(body))')
    (ui/'content.js').write_text(content_js,encoding='utf8')
    catalogue=(ui/'planet-catalog.js').read_text().replace('Sol, oito planetas e Lua na época consultada.','Sol, oito planetas e sete luas na época consultada.')
    (ui/'planet-catalog.js').write_text(catalogue,encoding='utf8')
    atlas.SPICE.kclear()
    print(json.dumps(dict(prepared=True,new_globes=6,bodies=16,destinations=15)),flush=True)


if __name__=='__main__':main()
