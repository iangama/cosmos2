'use strict';
(()=>{
  const el=id=>document.getElementById('spatial-'+id),openButton=document.getElementById('open-spatial');
  const state={snapshot:null,pending:false,polling:false,cancelling:false,error:'',message:'',formArtifact:null};
  window.spatialInstrument=state;
  const planes={XY:[[1,0,0],[0,1,0],[0,0,1]],XZ:[[1,0,0],[0,0,1],[0,-1,0]],YZ:[[0,1,0],[0,0,1],[1,0,0]]};
  const fmt=v=>Number(v).toLocaleString('pt-BR',{maximumSignificantDigits:8,notation:v!==0&&(Math.abs(v)<1e-4||Math.abs(v)>=1e8)?'scientific':'standard'});
  const sourceGuard=()=>{const p=appState?.physics;return p?{system_id:p.system_id,edit_token:p.edit_token,revision:p.revision,time:p.time,frame:p.contract.frame}:null;};
  function accept(value){
    const old=state.snapshot;
    if(old&&old.guard.session_id===value.guard.session_id&&value.guard.revision<old.guard.revision)return;
    state.snapshot=value;
  }
  function form(config){
    el('inner').value=config.inner_radius_boundary_units;el('outer').value=config.outer_radius_boundary_units;
    el('amplification').value=config.vertical_amplification;el('resolution').value=config.radial_count;
    el('plane').value=Object.keys(planes).find(k=>JSON.stringify(planes[k])===JSON.stringify(config.orientation))||'XY';
  }
  function render(){
    const s=state.snapshot,a=s?.artifact,active=Boolean(s?.active),busy=state.pending||Boolean(s?.busy),p=appState?.physics;
    document.body.classList.toggle('spatial-active',active||Boolean(s?.recovery_required));
    window.cosmosSpatialActive=active;
    el('active').hidden=!active&&!s?.recovery_required;el('caption').hidden=!active;el('create').hidden=active;el('recompute').hidden=!active;
    el('start').hidden=active||appState?.mode==='experiment'&&p?.paused&&p.bodies.length===4;
    el('copy').disabled=busy||pending||appState?.mode!=='atlas'||!atlasState;
    const ready=appState?.mode==='experiment'&&p?.paused&&p.bodies.length===4;
    el('config-fields').disabled=busy||!ready||Boolean(s?.recovery_required);el('body').disabled=active||busy;
    el('probe-fields').disabled=busy;el('storage-fields').disabled=busy;
    el('load-saved').hidden=active;el('load-saved').disabled=busy||!ready||!s?.checkpoint_available;
    el('leave').disabled=busy;el('load').disabled=busy||!s?.checkpoint_available;
    const tx=s?.transaction;el('cancel').hidden=!tx?.cancellable;el('cancel').disabled=state.cancelling;
    el('status').textContent=tx?`Preparando malha · ${fmt(tx.elapsed_s)} s · ${tx.cancellable?'cancelamento disponível':'confirmando vista'}`:active?'Vista confirmada · sondas independentes da ampliação':s?.recovery_required?'Restauração pendente; feche a vista para recuperar.':'Escolha o corpo e abra uma referência espacial.';
    el('error').textContent=state.error||s?.error||'';
    const bodies=p?.bodies||[];
    if(!active&&el('body').dataset.identities!==bodies.map(b=>b.id).join(',')){
      el('body').replaceChildren(...bodies.map(b=>new Option(b.name,b.id)));el('body').dataset.identities=bodies.map(b=>b.id).join(',');
    }
    if(!a)return;
    if(state.formArtifact!==a.id){
      form(a.configuration);el('body').value=a.source.body_id;state.formArtifact=a.id;
      for(const id of ['radial','reference'])el(id).max=a.configuration.radial_count-1;
      el('radial').value=a.view.selected_radial_index;el('azimuth').value=a.view.selected_azimuth_index;el('reference').value=a.view.reference_radial_index;
    }
    el('visible').checked=a.view.visible;el('visible').disabled=busy;
    const x=a.sample,m=x.metric,d=x.radial_distance,c=x.static_clock_comparison,src=a.source;
    el('reading').textContent=`Anel ${a.view.selected_radial_index}/${a.configuration.radial_count-1} · setor ${a.view.selected_azimuth_index}/95\nRaio areal: ${fmt(x.radius_m)} m\nr / Rref: ${fmt(x.radius_m/src.Rref_m)}\nCompactação rs/r: ${fmt(m.compactness)}\ng_rr: ${fmt(m.metric_rr)}\nK: ${fmt(m.Kretschmann_m_inverse4)} m⁻⁴\ndτ/dt∞: ${fmt(m.static_clock_ratio)}\nDéficit do relógio: ${fmt(m.static_clock_deficit)}\nDistância própria: ${fmt(d.proper_length_m)} m\nExcesso sobre Δr: ${fmt(d.proper_length_excess_m)} m\nReceptor: anel ${a.view.reference_radial_index}\nν recebida / ν emitida: ${fmt(c.received_over_emitted_frequency)}\nΔν/ν emitida: ${fmt(c.fractional_frequency_shift)}\nPosição física relativa (m): ${x.physical_position_relative_m.map(fmt).join('; ')}\nPosição exibida relativa (m): ${x.displayed_position_relative_m.map(fmt).join('; ')}`;
    el('source').textContent=`${src.name} · ${src.reference_id}\nÉpoca UTC: ${src.epoch.utc}\nGM: ${fmt(src.GM_m3_s2)} m³/s²\nRref: ${fmt(src.Rref_m)} m\nReferencial: GALACTIC\nPCK: ${src.boundary_provenance.file}\nArtefato: ${a.id}\nSHA256: ${a.sha256}`;
    el('caption-source').textContent=`${src.name} · ${src.epoch.utc}`;
    el('caption-scale').textContent=`${a.configuration.inner_radius_boundary_units}–${a.configuration.outer_radius_boundary_units} Rref · plano ${el('plane').value}\nAltura do desenho ×${fmt(a.configuration.vertical_amplification)} · ${a.view.visible?'visível':'oculta'}`;
    const selection=el('branches').value,branchSignature=JSON.stringify(s.branches);
    if(el('branches').dataset.signature!==branchSignature){
      el('branches').replaceChildren(...(s.branches||[]).map(b=>new Option(b.valid?b.name:b.name+' · inválido',b.id)));
      el('branches').dataset.signature=branchSignature;
      if([...el('branches').options].some(o=>o.value===selection))el('branches').value=selection;
    }
    el('branch-load').disabled=busy||!el('branches').value;
  }
  async function poll(){
    if(state.polling)return;state.polling=true;
    try{const response=await fetch('/api/spatial/state');if(!response.ok)throw Error('Servidor da malha indisponível.');accept(await response.json());render();}
    catch(error){if(!el('panel').hidden){state.error=error.message;render();}}finally{state.polling=false;}
  }
  async function send(command,extra={}){
    if(state.pending||state.snapshot?.busy||!state.snapshot)return;
    state.pending=true;state.error='';state.message='';render();
    try{
      const response=await fetch('/api/spatial/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command,guard:state.snapshot.guard,...extra})});
      const value=await response.json();if(!response.ok||!value.ok)throw Error(value.error||'A malha não foi confirmada.');
      accept(value.spatial);
      if(command==='set_view'){const v=value.spatial.artifact.view;el('radial').value=v.selected_radial_index;el('azimuth').value=v.selected_azimuth_index;el('reference').value=v.reference_radial_index;}
      if(['save','branch_create','export'].includes(command))el('storage-status').textContent=command==='export'?'Exportado para: '+value.result.path:command==='branch_create'?'Ramo salvo: '+value.result.branch.name:'Vista salva com as sondas e a referência exatas.';
      return value;
    }catch(error){state.error=error.message;}finally{state.pending=false;await poll();render();}
  }
  el('form').onsubmit=event=>{
    event.preventDefault();if(!el('form').reportValidity())return;
    const a=Number(el('inner').value),b=Number(el('outer').value);
    if(a>=b){state.error='O raio externo deve ser maior que o interno.';render();return;}
    const configuration={inner_radius_boundary_units:a,outer_radius_boundary_units:b,radial_count:Number(el('resolution').value),azimuth_sectors:96,orientation:planes[el('plane').value],vertical_amplification:Number(el('amplification').value)};
    if(state.snapshot?.active)send('configure',{configuration});else send('create',{source_guard:sourceGuard(),body_id:el('body').value,configuration});
  };
  el('sample').onclick=()=>{
    for(const id of ['radial','azimuth','reference'])if(!el(id).reportValidity())return;
    send('set_view',{view:{...state.snapshot.artifact.view,selected_radial_index:Number(el('radial').value),selected_azimuth_index:Number(el('azimuth').value),reference_radial_index:Number(el('reference').value)}});
  };
  el('visible').onchange=()=>send('set_view',{view:{...state.snapshot.artifact.view,visible:el('visible').checked}});
  el('load-saved').onclick=()=>send('load_saved',{source_guard:sourceGuard()});
  for(const [id,cmd]of [['save','save'],['load','load'],['leave','leave'],['export','export']])el(id).onclick=()=>send(cmd);
  el('branch-create').onclick=()=>{if(el('branch-name').reportValidity())send('branch_create',{name:el('branch-name').value});};
  el('branch-load').onclick=()=>send('branch_load',{branch_id:el('branches').value});
  el('cancel').onclick=async()=>{
    const id=state.snapshot?.transaction?.id;if(!id||state.cancelling)return;state.cancelling=true;render();
    try{const response=await fetch('/api/spatial/cancel',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({transaction_id:id})});const value=await response.json();if(!response.ok||!value.ok)throw Error(value.error||'Cancelamento não confirmado.');accept(value.spatial);state.error='Preparação cancelada; vista anterior preservada.';}catch(error){state.error=error.message;}finally{state.cancelling=false;render();}
  };
  el('copy').onclick=async()=>{await command({utc:atlasState.epoch.utc},'Cena solar pausada pronta.','/api/solar/experiment');await poll();};
  function open(){el('panel').hidden=false;openButton.setAttribute('aria-expanded','true');el('panel-close').focus();poll();}
  function close(){el('panel').hidden=true;openButton.setAttribute('aria-expanded','false');openButton.focus();}
  openButton.onclick=open;el('panel-close').onclick=close;
  el('panel').addEventListener('keydown',event=>{if(event.key==='Escape'){event.preventDefault();event.stopPropagation();close();}});
  setInterval(poll,500);poll();
})();
