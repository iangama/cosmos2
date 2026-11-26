"""Per-property origin, units and explicit unknowns for the initial solar Atlas."""
import copy
from atlas_import import gm_data
from physics import PHYSICAL_SCALE

TEXTURES = {
    'Earth': [('data/textures/earth.jpg', 'NASA Blue Marble'),
              ('data/textures/earth-night.jpg', 'NASA / luzes noturnas')],
    'Moon': [('data/textures/moon.png', 'LRO WAC')],
    'Saturn': [('data/textures/saturn-openspace.jpg', 'OpenSpace · mapa visual sem época confirmada')],
}
LABELS = {'10': 'GMS', '399': 'GM3', '301': 'GMM'}


def records(body, epoch, provenance):
    from packages import store
    packages = store().manifest['packages']
    images = {item['path']: dict(item, package_id=p['id']) for p in packages for item in p['files']}
    kernels = provenance['kernels_sha256']
    ephemeris = {'title': 'JPL DE442s', 'url': 'https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de442s.bsp',
                 'file': 'data/spice/de442s.bsp', 'sha256': kernels['data/spice/de442s.bsp'], 'package_id': 'solar:de442s'}
    pck = {'title': 'NAIF PCK00011 · rotações IAU gerais', 'url': 'https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/pck00011.tpc',
           'file': 'data/spice/pck00011.tpc', 'sha256': kernels['data/spice/pck00011.tpc'], 'package_id': 'solar:de442s'}
    ephemerides=[ephemeris]
    model='JPL DE442s'
    if body['scene_node']=='Saturn':
        model='SAT441 (699→6) + DE442s (6→0)'
        ephemerides.append({'title':'JPL SAT441 · subconjunto699 de SAT459',
                            'url':'https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/satellites/sat459.bsp',
                            'file':'data/spice/saturn-center-sat441.bsp',
                            'sha256':kernels['data/spice/saturn-center-sat441.bsp'],'package_id':'solar:saturn'})

    def property(id, label, value, unit, status, origin, sources, frame=None, at=None, uncertainty=None, note=None):
        return {'id': id, 'label': label, 'value': copy.deepcopy(value), 'unit': unit,
                'status': status, 'origin': origin, 'sources': sources,
                'frame': frame, 'epoch': copy.deepcopy(at),
                'uncertainty': {'value': uncertainty, 'status': 'unknown' if uncertainty is None else 'known'},
                'note': note}

    label=LABELS.get(body['naif_id'])
    gm = gm_data()[label] if label else None
    gm_source = {'title': 'Parâmetros publicados DE442 · ' + label,
                 'url': gm['source'], 'file': 'data/spice/de442_tech-comments.txt',
                 'sha256': gm['source_sha256'], 'line': gm['source_line'], 'package_id': 'solar:de442s'} if gm else None
    result = [
        property('position', 'Posição', body['position_m'], 'm', 'model_calculated', 'Estado geométrico '+model,
                 ephemerides, 'SSB / J2000-ICRF', epoch, note='Simultâneo na época TDB; sem atraso de luz. Incerteza da fonte não propagada.'),
        property('velocity', 'Velocidade', body['velocity_m_s'], 'm/s', 'model_calculated', 'Derivada do estado '+model,
                 ephemerides, 'SSB / J2000-ICRF', epoch, note='Incerteza da fonte não fornecida neste recorte.'),
    ]
    if gm:result += [
        property('GM', 'Parâmetro gravitacional GM', gm['value'], 'm³/s²', 'model_parameter',
                 'Parâmetro publicado do modelo DE442', [gm_source], note='Origem: ' + gm['raw_value_km3_s2'] + ' km³/s²; resolução de impressão não é incerteza.'),
        property('mass', 'Massa derivada GM/G', gm['value'] / PHYSICAL_SCALE['G_m3_kg_s2'], 'kg', 'inferred_from_model',
                 'Conversão GM/G usando G CODATA2022', [gm_source, {'title': 'NIST CODATA2022 · G',
                 'url': 'https://physics.nist.gov/cuu/pdf/wall_2022.pdf', 'file': 'data/science/canonical-units.json', 'package_id': 'physics:canonical-units'}],
                 note='Incerteza total desconhecida: a contribuição de G não inclui a incerteza ausente de GM.'),
    ]
    if gm:
        result[-1]['known_uncertainty_contribution_from_G_only_kg'] = result[-1]['value'] * PHYSICAL_SCALE['G_standard_uncertainty'] / PHYSICAL_SCALE['G_m3_kg_s2']
    else:
        for id,label,unit in [('GM','Parâmetro gravitacional GM','m³/s²'),('mass','Massa derivada GM/G','kg')]:
            result.append(property(id,label,None,unit,'unknown','Parâmetro do planeta não curado',[],note='GM6 é do sistema saturniano; não substitui GM do planeta699.'))
    shape = body['shape']
    local_shape = {'title': 'Forma adotada no perfil Cosmos2', 'file': 'user/data/assets/cosmos2/atlas.asset',
                   'sha256': provenance['code_sha256']['user/data/assets/cosmos2/atlas.asset']}
    if shape:
        shape_value = shape.get('radii_m', shape.get('radius_m'))
        sources = [local_shape]
        if body['scene_node'] == 'Earth':
            sources.append({'title': 'NGA WGS84', 'url': 'https://earth-info.nga.mil/?action=wgs84&dir=wgs84'})
        if body['scene_node']=='Saturn':sources.append(pck)
        result.append(property('shape', 'Semieixos do elipsoide' if isinstance(shape_value, list) else 'Raio da esfera adotada',
                               shape_value, 'm', 'adopted_reference_shape', shape.get('model', 'Esfera de referência do perfil'),
                               sources, body['body_frame'], note='Forma de referência adotada para o globo; não relevo, não raio de colisão do laboratório.'))
    else:
        result.append(property('shape', 'Forma de referência', None, 'm', 'unknown', 'Forma não cadastrada no Atlas inicial', []))
    result.append(property('orientation', 'Orientação do corpo → J2000', body['body_to_j2000'], '1',
                           'model_calculated' if body['body_to_j2000'] else 'unknown', 'Rotação IAU geral do PCK' if body['body_to_j2000'] else 'Orientação não cadastrada',
                           [pck] if body['body_to_j2000'] else [],
                           body['body_frame'] + ' → J2000' if body['body_frame'] else None,
                           epoch if body['body_to_j2000'] else None,
                           note='Matriz por linhas. Não é orientação ITRF precisa ou orientação lunar de kernel binário.'))
    textures = [{'path': path, 'credit': credit, 'sha256': images[path]['sha256'],
                 'source_url': images[path]['source_url'], 'package_id': images[path]['package_id'],
                 'acquisition_epoch': None} for path, credit in TEXTURES.get(body['scene_node'], [])]
    result.append(property('texture', 'Imagem de superfície', textures or None, 'image',
                           'illustrative_map' if body['scene_node']=='Saturn' else 'surface_imagery' if textures else 'unknown', 'Mapa visual OpenSpace; origem observacional/época não confirmadas; não evolução atmosférica' if body['scene_node']=='Saturn' else 'Imagem fixada; não recalculada com a época do Atlas' if textures else 'Imagem não cadastrada',
                           [{'title': t['credit'], 'url': t['source_url'], 'file': t['path'], 'sha256': t['sha256'], 'package_id': t['package_id']} for t in textures],
                           body['body_frame'], note='Datas de aquisição ausentes neste recorte; textura não é estado físico ou imagem de observador com tempo de luz.'))
    return result
