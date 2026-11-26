"""Prepare the small local Cosmos2 scene from identified upstream data."""
from pathlib import Path
import hashlib
import json
import shutil
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "textures"
FILES = {
    "earth.jpg": "solarsystem/planets/earth/earth/textures/1/earth_bluemarble.jpg",
    "earth-night.jpg": "solarsystem/planets/earth/earth/textures/1/earth_night.jpg",
    "moon.png": "solarsystem/planets/earth/moon/textures/2/WAC_GLOBAL_E000N0000_032P.png",
    "milkyway.jpg": "milkyway/milkyway/mellinger/textures/2/DarkUniverse_mellinger_4k.jpg",
}

def main():
    DATA.mkdir(parents=True, exist_ok=True)
    receipt = []
    for name, remote in FILES.items():
        url = "https://liu-se.cdn.openspaceproject.com/files/" + remote
        path = DATA / name
        if not path.exists():
            print("Downloading", name, flush=True)
            with urllib.request.urlopen(url, timeout=90) as response:
                content = response.read(256 * 1024 * 1024 + 1)
            if len(content) > 256 * 1024 * 1024:
                raise ValueError("Texture exceeds the 256 MiB budget")
            temporary = path.with_suffix(".partial")
            temporary.write_bytes(content)
            temporary.replace(path)
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        receipt.append(dict(file=str(path.relative_to(ROOT)), url=url,
                            bytes=path.stat().st_size, sha256=digest))
    (ROOT / "evidence" / "scene-data.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    shutil.copyfile(ROOT / "config" / "cosmos2.cfg", ROOT / ".runtime" / "cosmos2.cfg")
    print("Local scene data ready", flush=True)

if __name__ == "__main__":
    main()
