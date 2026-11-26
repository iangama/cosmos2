"""I static sampler with explicit identity and worker phase fences; keep2s bound."""
from pathlib import Path
import ast
import hashlib
import json
ROOT=Path(__file__).resolve().parents[1];I=ROOT/'output/c212-em-framing-product'
dest=ROOT/'evidence/em-framing-static-sampler-prepared.json';assert not dest.exists()
outputs={}
def change(s,a,b):assert s.count(a)==1,a;return s.replace(a,b)
source=(I/'app/em_slice.py').read_text();source=change(source,"VERSION='0.2.2'","VERSION='0.3.0'")
source=change(source,'maximum_segments=4096,budget_s=2.):','maximum_segments=4096,budget_s=2.,provider=None):')
source=change(source,'        samples=[];batches=[]','        provider_identity=provider.begin(initial) if provider is not None else None\n        samples=[];batches=[]')
source=change(source,"if ack.get('type')!='ack' or ack.get('paused')", "if ack.get('type')!=('sample_ack' if provider is not None else 'ack') or ack.get('paused')")
source=change(source,"'version':VERSION,'level_mode'","'version':VERSION,'provider':provider_identity,'level_mode'")
ast.parse(source);outputs[I/'app/em_slice.py']=source
source=(I/'app/em_laboratory.py').read_text();source=change(source,'from em_native import NativeEM','from em_native import NativeEM\nfrom em_static_sampler import StaticSampler')
source=change(source,"        try:layer=sample_slice(self._current,self._worker,self.command_lock,grid,settings['levels_V'])", "        provider=StaticSampler(self._current,self._worker)\n        try:layer=sample_slice(self._current,provider.query,self.command_lock,grid,settings['levels_V'],provider=provider)")
ast.parse(source);outputs[I/'app/em_laboratory.py']=source
source=(ROOT/'scripts/em-framing-sampler/em_static_sampler.py').read_text();ast.parse(source);outputs[I/'app/em_static_sampler.py']=source
for p,s in outputs.items():p.write_text(s)
report={'status':'I_verified_static_helper_reads_and_worker_phase_fences_prepared','source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in outputs},
        'scope':'App-only frozen reads via already verified helper ABI1, all sources, declared provider generation; snapshot fences per <=128point batch. Phase/core/worker bytes unchanged,2s numeric budget unchanged. Scalar equivalence, coherence, failure atomicity and live/native profiles pending.'}
dest.write_text(json.dumps(report,indent=2)+'\n');print(report['status'],flush=True)
