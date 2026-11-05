'use strict';
(()=>{
  const el=id=>document.getElementById('spatial-'+id),openButton=document.getElementById('open-spatial');
  const state={snapshot:null,pending:false,polling:false,cancelling:false,error:'',message:'',formArtifact:null,viewRevision:null,readingFile:false,selectedFile:null,previewFile:null,importMessage:'',selectedBranch:null};
  window.spatialInstrument=state;
  const text=(node,value)=>{if(node.textContent!==value)node.textContent=value;};
  const importFileSelected=()=>el('import-file').files[0]||state.selectedFile;
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
    const s=state.snapshot,a=s?.artifact,active=Boolean(s?.active),busy=state.pending||state.readingFile||Boolean(s?.busy),p=appState?.physics;
    document.body.classList.toggle('spatial-active',active||Boolean(s?.recovery_required));
    window.cosmosSpatialActive=active;
    el('active').hidden=!active&&!s?.recovery_required;el('caption').hidden=!active;el('create').hidden=active;el('recompute').hidden=!active;
    el('start').hidden=active||appState?.mode==='experiment'&&p?.paused&&p.bodies.length===4;
    el('copy').disabled=busy||pending||appState?.mode!=='atlas'||!atlasState;
    const ready=appState?.mode==='experiment'&&p?.paused&&p.bodies.length===4;
    el('config-fields').disabled=busy||!ready||Boolean(a?.origin)||Boolean(s?.recovery_required);
    el('archive-note').hidden=!a?.origin;el('body').disabled=active||busy;
    el('probe-fields').disabled=busy||!active;el('storage-fields').disabled=busy;
    for(const id of ['save','branch-create','export'])el(id).disabled=busy||!active;
    const file=importFileSelected(),preview=s?.import_preview;
    el('import-fields').disabled=busy||Boolean(s?.recovery_required);
    el('import-preview').disabled=busy||!file;
    el('import-commit').disabled=busy||!preview?.valid||!file||state.previewFile!==file;
    el('import-cancel').hidden=!preview;el('import-cancel').disabled=busy;
    text(el('import-selected'),file?'Arquivo: '+file.name:'');
    text(el('import-reading'),preview?`Sol · ${preview.epoch.utc}
Malha ${preview.configuration.inner_radius_boundary_units}–${preview.configuration.outer_radius_boundary_units} Rref · ${preview.configuration.radial_count}×${preview.configuration.azimuth_sectors}
Vista original: anel ${preview.view.selected_radial_index}, setor ${preview.view.selected_azimuth_index}, receptor ${preview.view.reference_radial_index} · ${preview.view.visible?'visível':'oculta'}
SHA256 original: ${preview.source_sha256}
${preview.valid?'Pronto para criar um novo ramo espacial.':'A vista mudou. Valide o arquivo novamente.'}`:state.importMessage||'Escolha uma referência espacial anterior para conferir a origem.');
    el('load-saved').hidden=active;el('load-saved').disabled=busy||!ready||!s?.checkpoint_available;
    el('leave').disabled=busy;el('load').disabled=busy||!active||!s?.checkpoint_available;
    const tx=s?.transaction;el('cancel').hidden=!tx?.cancellable;el('cancel').disabled=state.cancelling;
    text(el('status'),tx?`Preparando malha · ${fmt(tx.elapsed_s)} s · ${tx.cancellable?'cancelamento disponível':'confirmando vista'}`:active?'Vista confirmada · sondas independentes da ampliação':s?.recovery_required?'Restauração pendente; feche a vista para recuperar.':'Escolha o corpo e abra uma referência espacial.');
    text(el('error'),state.error||s?.error||'');
    const bodies=p?.bodies||[];
    if(!active&&el('body').dataset.identities!==bodies.map(b=>b.id).join(',')){
      el('body').replaceChildren(...bodies.map(b=>new Option(b.name,b.id)));el('body').dataset.identities=bodies.map(b=>b.id).join(',');
    }
    const selection=state.selectedBranch||el('branches').value,branchSignature=JSON.stringify(s?.branches);
    if(el('branches').dataset.signature!==branchSignature){
      el('branches').replaceChildren(...(s?.branches||[]).map(b=>new Option(b.valid?b.name:b.name+' · inválido',b.id)));
      el('branches').dataset.signature=branchSignature;
      if([...el('branches').options].some(o=>o.value===selection))el('branches').value=selection;
    }
    state.selectedBranch=null;
    const selected=(s?.branches||[]).find(b=>b.id===el('branches').value);
    el('branch-load').disabled=busy||!ready||!selected?.valid||Boolean(window.cosmosLayersActive);
    if(!a){state.formArtifact=null;state.viewRevision=null;return;}
    if(![...el('body').options].some(option=>option.value===a.source.body_id)){
      el('body').append(new Option(a.source.name,a.source.body_id));
      // Closing the archived reference rebuilds only current-phase choices.
      el('body').dataset.identities='';
    }
    if(state.formArtifact!==a.id){
      form(a.configuration);el('body').value=a.source.body_id;state.formArtifact=a.id;
      for(const id of ['radial','reference'])el(id).max=a.configuration.radial_count-1;
    }
    if(state.viewRevision!==s.guard.revision){
      el('radial').value=a.view.selected_radial_index;el('azimuth').value=a.view.selected_azimuth_index;el('reference').value=a.view.reference_radial_index;
      state.viewRevision=s.guard.revision;
    }
    el('visible').checked=a.view.visible;el('visible').disabled=busy;
    const x=a.sample,m=x.metric,d=x.radial_distance,c=x.static_clock_comparison,src=a.source;
    text(el('reading'),`Anel ${a.view.selected_radial_index}/${a.configuration.radial_count-1} · setor ${a.view.selected_azimuth_index}/95\nRaio areal: ${fmt(x.radius_m)} m\nr / Rref: ${fmt(x.radius_m/src.Rref_m)}\nCompactação rs/r: ${fmt(m.compactness)}\ng_rr: ${fmt(m.metric_rr)}\nK: ${fmt(m.Kretschmann_m_inverse4)} m⁻⁴\ndτ/dt∞: ${fmt(m.static_clock_ratio)}\nDéficit do relógio: ${fmt(m.static_clock_deficit)}\nDistância própria: ${fmt(d.proper_length_m)} m\nExcesso sobre Δr: ${fmt(d.proper_length_excess_m)} m\nReceptor: anel ${a.view.reference_radial_index}\nν recebida / ν emitida: ${fmt(c.received_over_emitted_frequency)}\nΔν/ν emitida: ${fmt(c.fractional_frequency_shift)}\nPosição física relativa (m): ${x.physical_position_relative_m.map(fmt).join('; ')}\nPosição exibida relativa (m): ${x.displayed_position_relative_m.map(fmt).join('; ')}`);
    text(el('source'),`${src.name} · ${src.reference_id}\nÉpoca UTC: ${src.epoch.utc}\nGM: ${fmt(src.GM_m3_s2)} m³/s²\nRref: ${fmt(src.Rref_m)} m\nReferencial: GALACTIC\nPCK: ${src.boundary_provenance.file}\nArtefato: ${a.id}\nSHA256: ${a.sha256}`+(a.origin?`\nOrigem importada: ${a.origin.source_format}\nSHA256 original: ${a.origin.source_sha256}\nVista original: anel ${a.origin.original_view.selected_radial_index}, setor ${a.origin.original_view.selected_azimuth_index}, receptor ${a.origin.original_view.reference_radial_index} · ${a.origin.original_view.visible?'visível':'oculta'}`:''));
    text(el('caption-source'),`${src.name} · ${src.epoch.utc}`);
    const confirmedPlane=Object.keys(planes).find(k=>JSON.stringify(planes[k])===JSON.stringify(a.configuration.orientation))||'orientado';
    text(el('caption-scale'),`${a.configuration.inner_radius_boundary_units}–${a.configuration.outer_radius_boundary_units} Rref · plano ${confirmedPlane}\nAltura do desenho ×${fmt(a.configuration.vertical_amplification)} · ${a.view.visible?'visível':'oculta'}`);

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
      const upload=['import_preview','import_commit'].includes(command);
      const endpoint=upload?'/api/spatial/'+command.replace('_','-'):'/api/spatial/command';
      const body={guard:state.snapshot.guard,...extra};if(!upload)body.command=command;
      const response=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
      const value=await response.json();if(!response.ok||!value.ok)throw Error(value.error||'A malha não foi confirmada.');
      accept(value.spatial);
      if(command==='import_preview')text(document.getElementById('notice'),'Arquivo espacial validado. Confira a origem antes de importar.');
      else if(command==='import_cancel'){state.previewFile=null;state.importMessage='Prévia cancelada.';text(document.getElementById('notice'),state.importMessage);}
      else if(command==='import_commit'){state.selectedBranch=value.result.record.branch.id;state.previewFile=null;state.importMessage='Ramo espacial importado. Escolha Restaurar ramo para abrir a malha.';text(document.getElementById('notice'),state.importMessage);}
      else text(document.getElementById('notice'),value.spatial.active?'Malha de '+value.spatial.artifact.source.name+' confirmada · órbita preservada.':'Vista espacial encerrada · órbita preservada.');
      if(command==='set_view'){const v=value.spatial.artifact.view;el('radial').value=v.selected_radial_index;el('azimuth').value=v.selected_azimuth_index;el('reference').value=v.reference_radial_index;}
      if(['save','branch_create','export'].includes(command))el('storage-status').textContent=command==='export'?'Exportado para: '+value.result.path:command==='branch_create'?'Ramo salvo: '+value.result.record.branch.name:'Vista salva com as sondas e a referência exatas.';
      return value;
    }catch(error){state.error=error.message;document.getElementById('notice').textContent=error.message;state.formArtifact=null;state.viewRevision=null;}finally{state.pending=false;await poll();render();}
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
  el('branch-load').onclick=()=>send('branch_load',{branch_id:el('branches').value,source_guard:sourceGuard()});
  el('cancel').onclick=async()=>{
    const id=state.snapshot?.transaction?.id;if(!id||state.cancelling)return;state.cancelling=true;render();
    try{const response=await fetch('/api/spatial/cancel',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({transaction_id:id})});const value=await response.json();if(!response.ok||!value.ok)throw Error(value.error||'Cancelamento não confirmado.');accept(value.spatial);state.error='Preparação cancelada; vista anterior preservada.';}catch(error){state.error=error.message;}finally{state.cancelling=false;render();}
  };
  el('copy').onclick=async()=>{await command({utc:atlasState.epoch.utc},'Cena solar pausada pronta.','/api/solar/experiment');await poll();};
  function open(){el('panel').hidden=false;openButton.setAttribute('aria-expanded','true');el('panel-close').focus();poll();}
  function close(){el('panel').hidden=true;openButton.setAttribute('aria-expanded','false');openButton.focus();}
  el('import-file').onchange=()=>{state.selectedFile=null;state.previewFile=null;state.importMessage='';render();};
  async function readImport(commit){
    const file=importFileSelected();
    if(!file||state.readingFile||state.pending||state.snapshot?.busy)return;
    if(commit&&(!state.snapshot?.import_preview?.valid||state.previewFile!==file))return;
    if(commit&&!el('import-name').reportValidity())return;
    state.readingFile=true;state.error='';render();
    try{
      if(!file.size||file.size>16*1024*1024)throw Error('Escolha um arquivo espacial JSON de até 16 MiB.');
      const bytes=await file.arrayBuffer();
      const source_text=new TextDecoder('utf-8',{fatal:true,ignoreBOM:true}).decode(bytes);
      state.readingFile=false;
      const response=await send(commit?'import_commit':'import_preview',commit?{preview_id:state.snapshot.import_preview.id,source_text,name:el('import-name').value}:{source_text});
      if(response&&!commit)state.previewFile=file;
    }catch(error){state.error=error.message;}
    finally{state.readingFile=false;render();}
  }
  el('import-preview').onclick=()=>readImport(false);
  el('import-commit').onclick=()=>readImport(true);
  el('import-cancel').onclick=()=>{if(state.snapshot?.import_preview)send('import_cancel',{preview_id:state.snapshot.import_preview.id});};
  window.openSpatialImport=file=>{
    if(file){state.selectedFile=file;state.previewFile=null;state.importMessage='';el('import-file').value='';}
    open();el('import-section').open=true;el('import-preview').focus();render();
  };
  openButton.onclick=open;el('panel-close').onclick=close;
  el('panel').addEventListener('keydown',event=>{if(event.key==='Escape'){event.preventDefault();event.stopPropagation();close();}});
  setInterval(poll,500);poll();
})();
