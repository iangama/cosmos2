"""Extend the existing Atlas controls with the six additional planet destinations."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'output/is6-planet-catalog-product0.23.1/app/ui'
STAGE = ROOT / 'output/is6-planet-navigation-staging'


def change(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Expected one UI source anchor: ' + old)
    return text.replace(old, new)


def main():
    target = STAGE / 'ui'
    if target.exists():
        raise FileExistsError('Preserve prepared navigation UI')
    target.mkdir()
    scene = json.loads((STAGE / 'planet_scene.json').read_text(encoding='utf8'))
    bodies = {node: item for node, item in scene['bodies'].items() if item['kind'] in ('planet', 'moon')}
    extra = {node: item for node, item in bodies.items() if 'texture' in item}
    search = {
        'Mercury': 'planeta rochoso sol mercúrio mercury',
        'Venus': 'planeta rochoso sol vênus venus',
        'Mars': 'planeta rochoso sol marte mars',
        'Jupiter': 'planeta gasoso sol júpiter jupiter',
        'Uranus': 'planeta gigante gelado sol urano uranus',
        'Neptune': 'planeta gigante gelado sol netuno neptune',
    }
    views = {}
    info = {}
    for node, item in bodies.items():
        radius = max(item['radii_m'])
        info[node] = dict(name=item['name'], target=item['target'], radius_m=radius,
                          search=search.get(node, 'lua terra moon' if node == 'Moon' else
                                            'planeta sol terra earth' if node == 'Earth' else 'planeta gasoso sol saturno saturn'))
        if node not in extra:
            continue
        image = item['texture']
        label = format(radius / 1000, ',.3f').rstrip('0').rstrip('.')
        label = label.replace(',', '_').replace('.', ',').replace('_', '.')
        views[node] = dict(anchor=node, position=[0, -4*radius, 2.5*radius], name=item['name'],
                           radius=label+' km', measure='RAIO EQUATORIAL DE REFERÊNCIA',
                           surface='Mapa visual OpenSpace',
                           description='Centro físico JPL e forma de referência PCK00011. Mapa visual fixo; época de aquisição desconhecida.')
        info[node]['content'] = f'Mapa visual fixo OpenSpace: {image["width"]} × {image["height"]} pixels. Época de aquisição desconhecida.'
    order = ['Mercury', 'Venus', 'Earth', 'Moon', 'System', 'Mars',
             'Jupiter', 'Saturn', 'Uranus', 'Neptune', 'Galaxy']
    definition = 'const planetInfo = ' + json.dumps(info, ensure_ascii=False, indent=2) + ';\n'
    definition += 'const planetViews = ' + json.dumps(views, ensure_ascii=False, indent=2) + ';\n'
    definition += 'const physicalTargets = Object.keys(planetInfo);\n'
    definition += 'const targetOrder = ' + json.dumps(order) + ';\n'
    (target / 'planet-definitions.js').write_text(definition, encoding='utf8')

    app = (BASE / 'app.js').read_text(encoding='utf8')
    app = change(app, 'function script(code) {', 'Object.assign(views, planetViews);\nfunction script(code) {')
    app = app.replace("['Earth','Moon','Saturn'].includes", 'physicalTargets.includes')
    app = change(app, "navigate('visit',{target,smooth:$('smooth-flight').checked})",
                 "navigate('visit',{target,smooth:$('smooth-flight').checked,sunlit:Boolean(planetViews[target])})")
    app = change(app, "({Moon:'301',Saturn:'699'}[selectedTarget]||'399')",
                 "(planetInfo[selectedTarget]?.target||'399')")
    (target / 'app.js').write_text(app, encoding='utf8')

    nav = (BASE / 'navigation.js').read_text(encoding='utf8')
    start = "const kindLabels={Earth:'planeta sol terra earth',Moon:'lua satélite sol terra lua moon',Saturn:'planeta gasoso sol saturno saturn',System:'sistema sol terra lua',Galaxy:'galáxia via láctea milky way'};"
    nav = change(nav, start,
                 "const kindLabels=Object.fromEntries(Object.entries(planetInfo).map(([node,item])=>[node,item.search]));\n"
                 "Object.assign(kindLabels,{System:'sistema sol terra lua',Galaxy:'galáxia via láctea milky way'});")
    nav = nav.replace("['Earth','Moon','System','Saturn','Galaxy'].indexOf", 'targetOrder.indexOf')
    nav = nav.replace("['Earth','Moon','Saturn'].includes", 'physicalTargets.includes')
    nav = change(nav, "limits[selectedTarget]||''", "limits[selectedTarget]||planetInfo[selectedTarget]?.content||''")
    nav = change(nav, "for(const target of ['Earth','Moon','Saturn'])", 'for(const target of physicalTargets)')
    nav = change(nav, "radius={Earth:6378137,Moon:1737400,Saturn:60268000}[target]",
                 'radius=planetInfo[target].radius_m')
    (target / 'navigation.js').write_text(nav, encoding='utf8')

    index = (BASE / 'index.html').read_text(encoding='utf8')
    index = change(index, '<script src="app.js"></script>',
                   '<script src="planet-definitions.js"></script><script src="app.js"></script>')
    tree_old = '<button data-tree-target="Earth">↳ Terra</button><button data-tree-target="Moon">↳ ↳ Lua</button><button data-tree-target="Saturn">↳ Saturno</button>'
    tree = ''.join('<button data-tree-target="'+node+'">'+('↳ ↳ ' if node == 'Moon' else '↳ ')+item['name']+'</button>'
                   for node, item in bodies.items())
    index = change(index, tree_old, tree)
    index = change(index, 'Recorte local · 2 planetas, 1 lua e modelo galáctico',
                   'Oito planetas, Lua e modelo galáctico')
    def button(node):
        item = bodies[node]
        kind = 'planeta rochoso' if node in ('Mercury', 'Venus', 'Mars') else 'gigante gasoso' if node == 'Jupiter' else 'gigante gelado'
        return ('      <button class="destination" data-target="'+node+'" data-kind="planet"><span class="planet '+node.lower()+
                '"></span><span><b>'+item['name']+'</b><small>Sol › '+item['name']+' · '+kind+
                '</small></span><span class="arrow">↗</span></button>\n')
    anchor = '      <button class="destination active" data-target="Earth"'
    index = change(index, anchor, button('Mercury')+button('Venus')+anchor)
    anchor = '      <button class="destination" data-target="Saturn"'
    index = change(index, anchor, button('Mars')+button('Jupiter')+anchor)
    anchor = '      <button class="destination" data-target="System"'
    index = change(index, anchor, button('Uranus')+button('Neptune')+anchor)
    index = index.replace('Tempo do Atlas · 1950–2050', 'Tempo do Atlas · 1995–2049')
    index = change(index, 'min="1950" max="2050.999"', 'min="1995" max="2049.997"')
    index = change(index, 'Época UTC de 1950 a 2050, por exemplo', 'Época UTC de 01/01/1995 a 30/12/2049, por exemplo')
    index = change(index, 'JPL · DE442s + SAT441', 'JPL · centros físicos')
    index = change(index, 'Sol/Terra/Lua/Saturno · estados geométricos.<br>1950–2050 · rotações IAU gerais.<br>Terra/Lua NASA; Saturno OpenSpace · AMNH.',
                   'Oito planetas e Lua · estados geométricos.<br>1995–2049 · rotações IAU gerais.<br>Mapas fixos NASA/OpenSpace · fontes na ficha.')
    (target / 'index.html').write_text(index, encoding='utf8')
    css = (BASE / 'style.css').read_text(encoding='utf8')
    css += '\n.mercury{background:radial-gradient(circle at 35% 35%,#d1c8b9,#81786f 55%,#292728)}'
    css += '.venus{background:radial-gradient(circle at 35% 35%,#f0dfb9,#c6a475 55%,#51433a)}'
    css += '.mars{background:radial-gradient(circle at 35% 35%,#e6ad86,#b06b4e 55%,#472d2b)}'
    css += '.jupiter{background:linear-gradient(12deg,#514137,#ccae90 25%,#a4775e 38%,#e6cdb0 52%,#976a53 65%,#d5b595 80%,#554437)}'
    css += '.uranus{background:radial-gradient(circle at 35% 35%,#b3e2e2,#6aadb9 55%,#294555)}'
    css += '.neptune{background:radial-gradient(circle at 35% 35%,#729dd8,#345a9b 55%,#182843)}\n'
    (target / 'style.css').write_text(css, encoding='utf8')
    content = (BASE / 'content.html').read_text(encoding='utf8')
    first = '<option value="399">Terra · NAIF399</option>'
    content = change(content, first, ''.join('<option value="'+item['target']+'">'+item['name']+' · NAIF'+item['target']+'</option>'
                    for node, item in extra.items())+first)
    (target / 'content.html').write_text(content, encoding='utf8')
    content_js = (BASE / 'content.js').read_text(encoding='utf8')
    content_js = change(content_js, "if(['10','399','301'].includes(body))",
                        "if(['10','199','299','399','301','499','599','699','799','899'].includes(body))")
    (target / 'content.js').write_text(content_js, encoding='utf8')
    print('Eight-planet Atlas UI prepared')


if __name__ == '__main__':
    main()
