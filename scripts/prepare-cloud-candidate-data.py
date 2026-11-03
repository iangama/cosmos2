"""Give the isolated staged app its normal read-only scientific input layout."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

assert sys.platform=='win32'
ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'data';link=ROOT/'output/c211-cloud-product/data'
assert source.is_dir() and (link.parent/'app/server.py').is_file()
if not link.exists():
    subprocess.run(['cmd.exe','/c','mklink','/J',str(link),str(source)],check=True,capture_output=True)
assert link.samefile(source),'Do not overwrite an unrelated staged data directory'
report={'status':'candidate_scientific_data_layout_prepared','method':'Windows directory junction to the existing project data; no copied or changed scientific inputs',
    'source':str(source),'staged_link':str(link),'same_directory_identity':True,
    'mass_table_sha256':hashlib.sha256((link/'science/ame2020-mass-original.txt').read_bytes()).hexdigest(),
    'app_sources_changed':False,'scope':'The staged forces modules use app-parent/data just as the installed app does. This prepares the test environment; installed app already has this layout.'}
(ROOT/'evidence/cloud-candidate-data-layout-check.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
