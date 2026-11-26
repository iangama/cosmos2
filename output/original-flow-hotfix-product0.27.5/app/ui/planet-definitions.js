const planetInfo = {
  "Mercury": {
    "name": "Mercúrio",
    "target": "199",
    "radius_m": 2440530.0,
    "search": "planeta rochoso sol mercúrio mercury",
    "content": "Mapa visual fixo OpenSpace: 11520 × 5760 pixels. Época de aquisição desconhecida."
  },
  "Venus": {
    "name": "Vênus",
    "target": "299",
    "radius_m": 6051800.0,
    "search": "planeta rochoso sol vênus venus",
    "content": "Mapa visual fixo OpenSpace: 1800 × 900 pixels. Época de aquisição desconhecida."
  },
  "Earth": {
    "name": "Terra",
    "target": "399",
    "radius_m": 6378137,
    "search": "planeta sol terra earth"
  },
  "Moon": {
    "name": "Lua",
    "target": "301",
    "radius_m": 1737400,
    "search": "lua satélite sol terra lua moon"
  },
  "Mars": {
    "name": "Marte",
    "target": "499",
    "radius_m": 3396190.0,
    "search": "planeta rochoso sol marte mars",
    "content": "Mapa visual fixo OpenSpace: 8192 × 4096 pixels. Época de aquisição desconhecida."
  },
  "Jupiter": {
    "name": "Júpiter",
    "target": "599",
    "radius_m": 71492000.0,
    "search": "planeta gasoso sol júpiter jupiter",
    "content": "Mapa visual fixo OpenSpace: 4096 × 2048 pixels. Época de aquisição desconhecida."
  },
  "Saturn": {
    "name": "Saturno",
    "target": "699",
    "radius_m": 60268000.0,
    "search": "planeta gasoso sol saturno saturn"
  },
  "Uranus": {
    "name": "Urano",
    "target": "799",
    "radius_m": 25559000.0,
    "search": "planeta gigante gelado sol urano uranus",
    "content": "Mapa visual fixo OpenSpace: 2048 × 1024 pixels. Época de aquisição desconhecida."
  },
  "Neptune": {
    "name": "Netuno",
    "target": "899",
    "radius_m": 24764000.0,
    "search": "planeta gigante gelado sol netuno neptune",
    "content": "Mapa visual fixo OpenSpace: 3000 × 1500 pixels. Época de aquisição desconhecida."
  },
  "Io": {
    "name": "Io",
    "target": "501",
    "radius_m": 1829400.0,
    "search": "lua satélite io io júpiter jupiter",
    "content": "Mapa visual fixo OpenSpace: 4096 × 2048 pixels. Época de aquisição desconhecida."
  },
  "Europa": {
    "name": "Europa",
    "target": "502",
    "radius_m": 1562600.0,
    "search": "lua satélite europa europa júpiter jupiter",
    "content": "Mapa visual fixo OpenSpace: 4096 × 2048 pixels. Época de aquisição desconhecida."
  },
  "Ganymede": {
    "name": "Ganimedes",
    "target": "503",
    "radius_m": 2631200.0,
    "search": "lua satélite ganimedes ganymede júpiter jupiter",
    "content": "Mapa visual fixo OpenSpace: 1800 × 900 pixels. Época de aquisição desconhecida."
  },
  "Callisto": {
    "name": "Calisto",
    "target": "504",
    "radius_m": 2410300.0,
    "search": "lua satélite calisto callisto júpiter jupiter",
    "content": "Mapa visual fixo OpenSpace: 1800 × 900 pixels. Época de aquisição desconhecida."
  },
  "Enceladus": {
    "name": "Encélado",
    "target": "602",
    "radius_m": 256600.00000000003,
    "search": "lua satélite encélado enceladus saturno saturn",
    "content": "Mapa visual fixo OpenSpace: 8192 × 4096 pixels. Época de aquisição desconhecida."
  },
  "Titan": {
    "name": "Titã",
    "target": "606",
    "radius_m": 2575150.0,
    "search": "lua satélite titã titan saturno saturn",
    "content": "Mapa visual fixo OpenSpace: 4040 × 2020 pixels. Época de aquisição desconhecida."
  }
};
const planetViews = {
  "Mercury": {
    "anchor": "Mercury",
    "position": [
      0,
      -9762120.0,
      6101325.0
    ],
    "name": "Mercúrio",
    "radius": "2.440,53 km",
    "measure": "RAIO EQUATORIAL DE REFERÊNCIA",
    "surface": "Mapa visual OpenSpace",
    "description": "Centro físico JPL e forma de referência PCK00011. Mapa visual fixo; época de aquisição desconhecida."
  },
  "Venus": {
    "anchor": "Venus",
    "position": [
      0,
      -24207200.0,
      15129500.0
    ],
    "name": "Vênus",
    "radius": "6.051,8 km",
    "measure": "RAIO EQUATORIAL DE REFERÊNCIA",
    "surface": "Mapa visual OpenSpace",
    "description": "Centro físico JPL e forma de referência PCK00011. Mapa visual fixo; época de aquisição desconhecida."
  },
  "Mars": {
    "anchor": "Mars",
    "position": [
      0,
      -13584760.0,
      8490475.0
    ],
    "name": "Marte",
    "radius": "3.396,19 km",
    "measure": "RAIO EQUATORIAL DE REFERÊNCIA",
    "surface": "Mapa visual OpenSpace",
    "description": "Centro físico JPL e forma de referência PCK00011. Mapa visual fixo; época de aquisição desconhecida."
  },
  "Jupiter": {
    "anchor": "Jupiter",
    "position": [
      0,
      -285968000.0,
      178730000.0
    ],
    "name": "Júpiter",
    "radius": "71.492 km",
    "measure": "RAIO EQUATORIAL DE REFERÊNCIA",
    "surface": "Mapa visual OpenSpace",
    "description": "Centro físico JPL e forma de referência PCK00011. Mapa visual fixo; época de aquisição desconhecida."
  },
  "Uranus": {
    "anchor": "Uranus",
    "position": [
      0,
      -102236000.0,
      63897500.0
    ],
    "name": "Urano",
    "radius": "25.559 km",
    "measure": "RAIO EQUATORIAL DE REFERÊNCIA",
    "surface": "Mapa visual OpenSpace",
    "description": "Centro físico JPL e forma de referência PCK00011. Mapa visual fixo; época de aquisição desconhecida."
  },
  "Neptune": {
    "anchor": "Neptune",
    "position": [
      0,
      -99056000.0,
      61910000.0
    ],
    "name": "Netuno",
    "radius": "24.764 km",
    "measure": "RAIO EQUATORIAL DE REFERÊNCIA",
    "surface": "Mapa visual OpenSpace",
    "description": "Centro físico JPL e forma de referência PCK00011. Mapa visual fixo; época de aquisição desconhecida."
  },
  "Io": {
    "anchor": "Io",
    "position": [
      0,
      -7317600.0,
      4573500.0
    ],
    "name": "Io",
    "radius": "1.829,4 km",
    "measure": "MAIOR SEMIEIXO DE REFERÊNCIA",
    "surface": "Mapa visual OpenSpace",
    "description": "Lua de Júpiter. Centro físico JPL, forma PCK00011 e mapa fixo; época de aquisição desconhecida."
  },
  "Europa": {
    "anchor": "Europa",
    "position": [
      0,
      -6250400.0,
      3906500.0
    ],
    "name": "Europa",
    "radius": "1.562,6 km",
    "measure": "MAIOR SEMIEIXO DE REFERÊNCIA",
    "surface": "Mapa visual OpenSpace",
    "description": "Lua de Júpiter. Centro físico JPL, forma PCK00011 e mapa fixo; época de aquisição desconhecida."
  },
  "Ganymede": {
    "anchor": "Ganymede",
    "position": [
      0,
      -10524800.0,
      6578000.0
    ],
    "name": "Ganimedes",
    "radius": "2.631,2 km",
    "measure": "MAIOR SEMIEIXO DE REFERÊNCIA",
    "surface": "Mapa visual OpenSpace",
    "description": "Lua de Júpiter. Centro físico JPL, forma PCK00011 e mapa fixo; época de aquisição desconhecida."
  },
  "Callisto": {
    "anchor": "Callisto",
    "position": [
      0,
      -9641200.0,
      6025750.0
    ],
    "name": "Calisto",
    "radius": "2.410,3 km",
    "measure": "MAIOR SEMIEIXO DE REFERÊNCIA",
    "surface": "Mapa visual OpenSpace",
    "description": "Lua de Júpiter. Centro físico JPL, forma PCK00011 e mapa fixo; época de aquisição desconhecida."
  },
  "Enceladus": {
    "anchor": "Enceladus",
    "position": [
      0,
      -1026400.0000000001,
      641500.0000000001
    ],
    "name": "Encélado",
    "radius": "256,6 km",
    "measure": "MAIOR SEMIEIXO DE REFERÊNCIA",
    "surface": "Mapa visual OpenSpace",
    "description": "Lua de Saturno. Centro físico JPL, forma PCK00011 e mapa fixo; época de aquisição desconhecida."
  },
  "Titan": {
    "anchor": "Titan",
    "position": [
      0,
      -10300600.0,
      6437875.0
    ],
    "name": "Titã",
    "radius": "2.575,15 km",
    "measure": "MAIOR SEMIEIXO DE REFERÊNCIA",
    "surface": "Mapa visual OpenSpace",
    "description": "Lua de Saturno. Centro físico JPL, forma PCK00011 e mapa fixo; época de aquisição desconhecida."
  }
};
const physicalTargets = Object.keys(planetInfo);
const targetOrder = ["Mercury", "Venus", "Earth", "Moon", "System", "Mars", "Jupiter", "Io", "Europa", "Ganymede", "Callisto", "Saturn", "Enceladus", "Titan", "Uranus", "Neptune", "Galaxy"];
