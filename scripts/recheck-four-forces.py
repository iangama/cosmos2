"""Reexecute existing scientific checks with preserved receipts and source identity.

This does not launch the renderer or certify an integrated planetary model.
Run using the project's Windows Python so the same numerical dependencies apply.
"""
from pathlib import Path
import argparse
import datetime as dt
import hashlib
import importlib.metadata
import json
import platform
import shutil
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SUITE = [
    ("forces", "forces-check"),
    ("em-readings", "em-readings-check"),
    ("fusion", "fusion-check"),
    ("decays", "decays-check"),
    ("cno", "cno-check"),
    ("force-persistence", "force-persistence-check"),
    ("science-contracts", "science-contracts-check"),
    ("nuclei", "nuclei-check"),
    ("nuclear-energies", "nuclear-energies-check"),
    ("igrf", "igrf-check"),
    ("dipole", "dipole-check"),
    ("gravity-probe", "gravity-probe-check"),
    ("atlas", "atlas-check"),
    ("atlas-import", "atlas-import-check"),
]


def sha(path):
    return hashlib.file_digest(path.open("rb"), "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    if not args.label or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in args.label):
        parser.error("Use lowercase letters, digits and hyphens for the label.")
    directory = ROOT / "output" / ("four-forces-recheck-" + args.label)
    directory.mkdir(exist_ok=False)
    before = directory / "previous-receipts"
    after = directory / "executed-receipts"
    before.mkdir()
    after.mkdir()
    files = sorted(set(
        list((ROOT / "app").glob("*.py"))
        + [ROOT / "scripts" / ("verify-" + name + ".py") for name, _ in SUITE]
        + [Path(__file__).resolve()]
    ))
    source_hashes = {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p) for p in files}
    for _, receipt in SUITE:
        path = ROOT / "evidence" / (receipt + ".json")
        if path.exists():
            shutil.copy2(path, before / path.name)
    owner = ROOT / "user/sessions/latest.json"
    owner_before = sha(owner) if owner.exists() else None
    archive = directory / "executed-scientific-sources.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for path in files:
            z.write(path, str(path.relative_to(ROOT)))
    report = {
        "schema": 1,
        "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "runtime": {name: importlib.metadata.version(name) for name in
                    ["numpy", "scipy", "rebound", "spiceypy", "pynucastro"]},
        "scope": "Existing root scientific benches and read-only local JPL fixtures; no native UI, J performance or integrated four-body certification.",
        "source_sha256": source_hashes,
        "source_archive": str(archive.relative_to(ROOT)).replace("\\", "/"),
        "source_archive_sha256": sha(archive),
        "previous_receipts": str(before.relative_to(ROOT)).replace("\\", "/"),
        "owner_pointer_before_sha256": owner_before,
        "checks": [],
        "completed": False,
        "accepted": False,
    }
    manifest = ROOT / "evidence" / ("four-forces-recheck-" + args.label + ".json")
    if manifest.exists():
        raise FileExistsError(manifest)

    def persist():
        manifest.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    persist()
    for name, receipt in SUITE:
        started = time.perf_counter()
        log = directory / (name + ".log")
        item = {"name": name, "script": "scripts/verify-" + name + ".py"}
        try:
            with log.open("w", encoding="utf-8") as output:
                process = subprocess.run([sys.executable, "-Xutf8", str(ROOT / item["script"])],
                                         cwd=ROOT, stdout=output, stderr=subprocess.STDOUT,
                                         timeout=300, check=False)
            item["exit_code"] = process.returncode
            item["passed"] = process.returncode == 0
        except subprocess.TimeoutExpired:
            item.update(passed=False, error="Scientific check exceeded the 300-second execution bound.")
        item["wall_s"] = time.perf_counter() - started
        item["log"] = str(log.relative_to(ROOT)).replace("\\", "/")
        item["log_sha256"] = sha(log)
        path = ROOT / "evidence" / (receipt + ".json")
        if item["passed"]:
            if not path.is_file() or path.stat().st_mtime < started_wall:
                item.update(passed=False, error="Expected receipt was not rewritten by this run.")
            else:
                json.loads(path.read_text(encoding="utf-8"))
                shutil.copy2(path, after / path.name)
                item["receipt"] = str((after / path.name).relative_to(ROOT)).replace("\\", "/")
                item["receipt_sha256"] = sha(path)
        report["checks"].append(item)
        persist()
        print(json.dumps({k: item[k] for k in ("name", "passed", "wall_s")}), flush=True)
        if not item["passed"]:
            break
    report["source_unchanged"] = all(sha(ROOT / path) == digest for path, digest in source_hashes.items())
    report["owner_pointer_after_sha256"] = sha(owner) if owner.exists() else None
    report["owner_pointer_preserved"] = report["owner_pointer_after_sha256"] == owner_before
    report["completed"] = len(report["checks"]) == len(SUITE)
    report["accepted"] = (report["completed"] and all(c["passed"] for c in report["checks"])
                          and report["source_unchanged"] and report["owner_pointer_preserved"])
    report["finished_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    persist()
    print(json.dumps({k: report[k] for k in ["completed", "accepted", "owner_pointer_preserved", "source_unchanged"]}), flush=True)
    return 0 if report["accepted"] else 1


if __name__ == "__main__":
    started_wall = time.time()
    raise SystemExit(main())
