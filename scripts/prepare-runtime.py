#!/usr/bin/env python3
"""Obtain the official Windows runtime for the isolated C2-00 prototype."""
import hashlib
import json
from pathlib import Path
import time
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
URL = "https://data.openspaceproject.com/release/0.22.0/OpenSpace-0.22.0_minimal.zip"
EXPECTED_SIZE = 353588398


def main():
    cache = ROOT / ".cache"
    runtime = ROOT / ".runtime"
    evidence = ROOT / "evidence"
    for directory in (cache, runtime, evidence):
        directory.mkdir(exist_ok=True)
    archive = cache / "OpenSpace-0.22.0_minimal.zip"
    partial = archive.with_suffix(".zip.partial")
    if not archive.exists():
        request = urllib.request.Request(URL, headers={"User-Agent": "Cosmos2-C2-00"})
        started = time.monotonic()
        with urllib.request.urlopen(request, timeout=60) as response, partial.open("wb") as output:
            total = 0
            reported = 0
            while block := response.read(1024 * 1024):
                total += len(block)
                if total > EXPECTED_SIZE:
                    raise RuntimeError("Official archive changed size; inspect the release before continuing")
                output.write(block)
                if total - reported >= 32 * 1024 * 1024:
                    print(f"Downloaded {total // (1024 * 1024)} MiB", flush=True)
                    reported = total
        if partial.stat().st_size != EXPECTED_SIZE:
            raise RuntimeError("Incomplete archive; the original remains untouched")
        partial.replace(archive)
        print(f"Download finished in {time.monotonic() - started:.1f}s", flush=True)
    if archive.stat().st_size != EXPECTED_SIZE:
        raise RuntimeError("Archive size mismatch")
    digest = hashlib.file_digest(archive.open("rb"), "sha256").hexdigest()
    receipt_path = evidence / "runtime-acquisition.json"
    if receipt_path.exists():
        previous = json.loads(receipt_path.read_text())
        if previous["sha256"] != digest:
            raise RuntimeError("The archive no longer matches the previously acquired file")
    with zipfile.ZipFile(archive) as bundle:
        if sum(item.file_size for item in bundle.infolist()) > 3 * 1024**3:
            raise RuntimeError("Unexpected unpacked size")
        for item in bundle.infolist():
            target = (runtime / item.filename).resolve()
            if not target.is_relative_to(runtime.resolve()):
                raise RuntimeError("Unsafe archive path")
        bad = bundle.testzip()
        if bad:
            raise RuntimeError(f"Archive CRC failed: {bad}")
        # A completed acquisition is not unpacked again over a customized runtime.
        if not receipt_path.exists():
            bundle.extractall(runtime)
        receipt = {
            "version": "0.22.0", "url": URL, "bytes": archive.stat().st_size,
            "sha256": digest, "verification": "HTTPS acquisition, ZIP CRC, locally recorded SHA256; no publisher checksum supplied",
            "files": len(bundle.infolist()), "archive_roots": sorted({p.filename.split('/')[0] for p in bundle.infolist()}),
        }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2), flush=True)


if __name__ == "__main__":
    main()
