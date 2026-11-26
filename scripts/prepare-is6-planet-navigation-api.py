"""Reuse the existing navigation implementation with the expanded body model."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / 'output/is6-planet-navigation-staging'
BASE = ROOT / 'output/is6-planet-catalog-product0.23.1/app'


def change(text, before, after):
    if text.count(before) != 1:
        raise ValueError('Expected one navigation source anchor: ' + before)
    return text.replace(before, after)


def main():
    target = STAGE / 'planet_navigation.py'
    if target.exists():
        raise FileExistsError('Preserve prepared navigation API')
    source = (BASE / 'navigation.py').read_text(encoding='utf8')
    source = change(source, 'from atlas import ROOT, states, normalize_epoch',
                    'from planet_atlas import ROOT, states, normalize_epoch, BODIES, BODY_NODES, NODES, START_UTC, END_UTC')
    source = change(source, "ANCHORS={'Sun','Earth','Moon','Saturn','MilkyWayVolume','CosmosFreeAnchor'}",
                    '''for node in BODY_NODES:
    if node not in DESTINATIONS:
        radius = max(BODIES[node]['radii_m'])
        DESTINATIONS[node] = (node, [0, -4*radius, 2.5*radius])
ANCHORS = set(NODES) | {'MilkyWayVolume', 'CosmosFreeAnchor'}
POSITION_QUERY = ','.join(node+'=openspace.worldPosition('+json.dumps(node)+')' for node in NODES)
ROTATION_QUERY = ','.join(node+'=openspace.worldRotation('+json.dumps(node)+')' for node in BODY_NODES)''')
    source = change(source,
                    "radii={'Earth':[6378137,6378137,6356752.314245],'Moon':[1737400]*3,'Saturn':[60268000,60268000,54364000]}",
                    "radii={node:BODIES[node]['radii_m'] for node in BODY_NODES}")
    positions = 'positions={Sun=openspace.worldPosition("Sun"),Earth=openspace.worldPosition("Earth"),Moon=openspace.worldPosition("Moon"),Saturn=openspace.worldPosition("Saturn")}'
    rotations = 'rotations={Earth=openspace.worldRotation("Earth"),Moon=openspace.worldRotation("Moon"),Saturn=openspace.worldRotation("Saturn")}'
    source = change(source, positions, "positions={'+POSITION_QUERY+'}")
    source = change(source, rotations, "rotations={'+ROTATION_QUERY+'}")
    source = source.replace("target not in {'Earth','Moon','Saturn'}", 'target not in BODY_NODES')
    source = change(source, "radius={'Earth':6378137,'Moon':1737400,'Saturn':60268000}[target]",
                    "radius=max(BODIES[target]['radii_m'])")
    source = change(source, "atlas.SPICE.str2et('1950-01-01T00:00:00')", 'atlas.SPICE.str2et(START_UTC)')
    source = change(source, "atlas.SPICE.str2et('2050-12-31T23:59:59')", 'atlas.SPICE.str2et(END_UTC)')
    ast.parse(source)
    target.write_text(source, encoding='utf8')
    print('Expanded navigation source prepared')


if __name__ == '__main__':
    main()
