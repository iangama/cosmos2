{
  "assets": [
    "${USER_ASSETS}/cosmos2/atlas.asset",
    "${USER_ASSETS}/cosmos2/atmosphere.asset",
    "${USER_ASSETS}/cosmos2/galaxy.asset",
    "${COSMOS2}/output/is6-planet-navigation-staging/planet_scene.asset",
    "${COSMOS2}/output/is6-principal-moons-navigation-staging/moon_scene.asset"
  ],
  "camera": {
    "type": "setNavigationState",
    "anchor": "Earth",
    "aim": "",
    "frame": "Root",
    "position": {
      "x": 17674090.653605793,
      "y": -1566585.5066504919,
      "z": 18170644.716643292
    },
    "up": {
      "x": 0,
      "y": 0,
      "z": 1
    },
    "yaw": 0
  },
  "delta_times": [
    1,
    60,
    3600,
    86400
  ],
  "meta": {
    "name": "Cosmos2 — planetas e luas",
    "author": "Cosmos2",
    "description": "Sol, oito planetas e sete luas; centros físicos geométricos e rotações IAU gerais,1995–2049.",
    "version": "0.25.1"
  },
  "time": {
    "type": "absolute",
    "value": "2026-10-11T12:00:00",
    "is_paused": true
  },
  "version": {
    "major": 1,
    "minor": 5
  }
}
