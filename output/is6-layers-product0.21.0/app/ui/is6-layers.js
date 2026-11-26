'use strict';
(()=>{
  const el=id=>document.getElementById('layers-'+id),opener=document.getElementById('open-layers');
  const state={snapshot:null,pending:false,polling:false,cancelling:false,error:'',body:null,readingFile:false,previewFile:null,importMessage:''};
  window.layerInstrument=state;
  const fmt=v=>Number(v).toLocaleString('pt-BR',{maximumSignificantDigits:8,notation:v!==0&&(Math.abs(v)<1e-4||Math.abs(v)>=1e8)?'scientific':'standard'});
  const sourceGuard=()=>{const p=appState?.physics;return p?{system_id:p.system_id,edit_token:p.edit_token,revision:p.revision,time:p.time,frame:p.contract.frame}:null;};
  function accept(snapshot){
    const old=state.snapshot;
    if(old&&old.guard.session_id===snapshot.guard.session_id&&snapshot.guard.revision<old.guard.revision)return;
    state.snapshot=snapshot;
  }
  function render(){
    const s=state.snapshot,a=s?.artifact,active=Boolean(s?.active),busy=state.pending||state.readingFile||Boolean(s?.busy),locked=active||busy||Boolean(s?.recovery_required),p=appState?.physics;
    const ready=appState?.mode==='experiment'&&p?.paused&&p.bodies.length===4;
    document.body.classList.toggle('layers-active',locked);window.cosmosLayersActive=locked;
    for(const button of document.querySelectorAll('header nav button:not(#open-layers):not(#open-stellar-reference),#home')){
      if(locked){if(!button.dataset.layersLocked){button.dataset.layersDisabled=String(button.disabled);button.dataset.layersLocked='1';}button.disabled=true;}
      else if(button.dataset.layersLocked){button.disabled=button.dataset.layersDisabled==='true';delete button.dataset.layersLocked;delete button.dataset.layersDisabled;}
    }
    el('start').hidden=ready||active;el('copy').disabled=busy||pending||appState?.mode!=='atlas'||!atlasState;
    el('form').hidden=active||Boolean(s?.recovery_required);el('fields').disabled=busy||!ready;
    el('load-saved').hidden=active||Boolean(s?.recovery_required);el('load-saved').disabled=busy||!ready||!s?.checkpoint_available;
    el('active').hidden=!active;el('leave').hidden=!active&&!s?.recovery_required;el('leave').disabled=busy;
    el('caption').hidden=!active;el('visibility').disabled=busy||Boolean(s?.recovery_required);
    el('storage-fields').disabled=busy||!active||Boolean(s?.recovery_required);el('load').disabled=busy||!s?.checkpoint_available;
    const branchSelection=el('branches').value,branchSignature=JSON.stringify(s?.branches||[]);
    if(el('branches').dataset.signature!==branchSignature){
      const options=(s?.branches||[]).map(b=>{const o=new Option(b.name+(b.valid?'':' · inválido'),b.id);o.disabled=!b.valid;return o;});
      el('branches').replaceChildren(...options);el('branches').dataset.signature=branchSignature;
      if([...el('branches').options].some(o=>o.value===branchSelection))el('branches').value=branchSelection;
    }
    el('branch-load').disabled=busy||!el('branches').value||Boolean(el('branches').selectedOptions[0]?.disabled);
    const preview=s?.import_preview,file=el('import-file').files[0];
    el('import-fields').disabled=busy||Boolean(s?.recovery_required);
    el('import-preview').disabled=busy||!file;
    el('import-commit').disabled=busy||!preview?.valid||!file||state.previewFile!==file;
    el('import-cancel').hidden=!preview;el('import-cancel').disabled=busy;
    if(preview&&state.previewFile===file){
      const bodyName={'sol:naif:399':'Terra','sol:naif:599':'Júpiter'}[preview.body_reference_id]||preview.body_reference_id;
      el('import-reading').textContent=`${bodyName} · ${preview.epoch.utc}\n${preview.magnetic_model}\nMalha ${preview.visible.spatial?'visível':'oculta'} · amostra magnética ${preview.visible.magnetic?'visível':'oculta'}\n${preview.changes.join('\n')}\n${preview.valid?'Pronto para criar um novo ramo.':'A vista mudou. Valide o arquivo novamente.'}`;
    }else el('import-reading').textContent=state.importMessage||(file?'Arquivo selecionado: '+file.name+'. Valide para conferir a origem.':'Escolha um arquivo composto para conferir sua origem.');
    const tx=s?.transaction;el('cancel').hidden=!tx?.cancellable;el('cancel').disabled=state.cancelling;
    el('status').textContent=tx?`Preparando camadas · ${fmt(tx.elapsed_s)} s · ${tx.cancellable?'cancelamento disponível':'confirmando vista'}`:s?.recovery_required?'Restauração pendente; feche as camadas para recuperar.':active?(a?.archived?'Referência arquivada · cópia orbital atual preservada':'Referências congeladas na mesma fase · órbita preservada'):'Escolha o corpo e as coordenadas da amostra.';
    el('error').textContent=state.error||s?.error||'';
    const bodies=(p?.bodies||[]).filter(b=>['sol:naif:399','sol:naif:599'].includes(b.reference_id));
    if(!active&&el('body').dataset.identities!==bodies.map(b=>b.id).join(',')){
      el('body').replaceChildren(...bodies.map(b=>new Option(b.name+' · '+(b.reference_id==='sol:naif:399'?'IGRF14':'JRM33 grau 13'),b.id)));
      el('body').dataset.identities=bodies.map(b=>b.id).join(',');state.body=null;
    }
    const body=bodies.find(b=>b.id===el('body').value),jovian=body?.reference_id==='sol:naif:599';
    el('longitude').min=jovian?'0':'-180';el('longitude').max=jovian?'360':'180';
    el('altitude-label').hidden=jovian;el('altitude').disabled=jovian;
    el('radius-label').hidden=!jovian;el('radius').disabled=!jovian;
    if(body&&body.id!==state.body){el('latitude').value=jovian?'0':'-23.55';el('longitude').value=jovian?'0':'-46.63';state.body=body.id;}
    if(!a)return;
    el('spatial-visible').checked=a.visible.spatial;el('magnetic-visible').checked=a.visible.magnetic;
    const x=a.spatial_sample,m=x.metric,b=a.magnetic,terrestrial=b.body_reference_id==='sol:naif:399',field=terrestrial?b.field_ITRF93_T:b.field_SystemIII_T;
    el('spatial-reading').textContent=`Raio da sonda: ${fmt(x.radius_m)} m\nCurvatura K: ${fmt(m.Kretschmann_m_inverse4)} m⁻⁴\ndτ/dt∞: ${fmt(m.static_clock_ratio)}\nDéficit do relógio: ${fmt(m.static_clock_deficit)}\nDistância própria: ${fmt(x.radial_distance.proper_length_m)} m\nAltura do desenho ×200 · exterior 1–3 Rref`;
    el('magnetic-reading').textContent=`${b.provenance.model}\nB: ${field.map(fmt).join('; ')} T\n|B|: ${fmt(Math.hypot(...field))} T\nComponentes em ${terrestrial?'ITRF93':'System III'}\n${terrestrial?'Latitude geodética':'Latitude planetocêntrica'}: ${fmt(b.coordinates.latitude_deg??b.coordinates.latitude_planetocentric_deg)}°\nLongitude leste: ${fmt(b.coordinates.longitude_deg??b.coordinates.longitude_east_deg)}°\n${terrestrial?'Altitude: '+fmt(b.coordinates.altitude_m)+' m':'Raio: '+fmt(b.coordinates.radius_m)+' m'}\nPosição exibida: metros · GALACTIC`;
    el('source').textContent=`${a.source.name} · ${a.source.body_reference_id}\nÉpoca: ${a.source.epoch.utc}\nGM: ${fmt(a.source.source_configuration.GM_m3_s2)} m³/s²\nRref: ${fmt(a.source.source_configuration.material_radius_m)} m\n${b.uncertainty_reason}\nArtefato: ${a.id}\nSHA256: ${a.sha256}`;
    if(a.origin)el('source').textContent+=`\nImportado de ${a.origin.source_format}\nSHA256 original: ${a.origin.source_sha256}`;
    el('caption-source').textContent=a.source.name+' · '+a.source.epoch.utc+(a.archived?' · referência arquivada':'');
    el('caption-visible').textContent=`Malha ${a.visible.spatial?'visível':'oculta'} · referência magnética ${a.visible.magnetic?'visível':'oculta'}`;
  }
  async function poll(){
    if(state.polling)return;state.polling=true;
    try{const response=await fetch('/api/layers/state');if(!response.ok)throw Error('Servidor de camadas indisponível.');accept(await response.json());render();}
    catch(error){if(!el('panel').hidden){state.error=error.message;render();}}finally{state.polling=false;}
  }
  async function send(command,extra={}){
    if(state.pending||state.snapshot?.busy||!state.snapshot)return;
    state.pending=true;state.error='';render();
    try{
      const upload=['import_preview','import_commit'].includes(command);
      const endpoint=upload?'/api/layers/'+command.replace('_','-'):'/api/layers/command';
      const payload=upload?{guard:state.snapshot.guard,...extra}:{command,guard:state.snapshot.guard,...extra};
      const response=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
      const value=await response.json();if(!response.ok||!value.ok)throw Error(value.error||'As camadas não foram confirmadas.');
      accept(value.layers);document.getElementById('notice').textContent=value.layers.active?'Camadas confirmadas · órbita preservada.':'Camadas encerradas · cena restaurada.';
      if(command==='import_preview')document.getElementById('notice').textContent='Arquivo validado. Confira a origem antes de importar.';
      if(command==='import_cancel'){state.previewFile=null;state.importMessage='Prévia cancelada.';document.getElementById('notice').textContent=state.importMessage;}
      if(command==='import_commit'){
        state.previewFile=null;el('branches').value=value.result.record.id;
        state.importMessage='Novo ramo importado: '+value.result.record.name;
        document.getElementById('notice').textContent='Ramo importado: '+value.result.record.name+'. Abra as camadas e escolha Restaurar ramo.';
      }
      if(command==='save')el('storage-status').textContent='Referências e visibilidades salvas.';
      if(command==='branch_create')el('storage-status').textContent='Ramo salvo: '+value.result.record.name;
      if(command==='export')el('storage-status').textContent='Exportado para: '+value.result.path;
      if(['load','load_saved','branch_load'].includes(command)){
        el('storage-status').textContent='Referência arquivada restaurada; cópia orbital atual preservada.';
        document.getElementById('notice').textContent='Referência arquivada restaurada · órbita atual preservada.';
      }
      return value;
    }catch(error){state.error=error.message;document.getElementById('notice').textContent=error.message;}
    finally{state.pending=false;await poll();render();}
  }
  el('import-file').onchange=()=>{state.previewFile=null;state.importMessage='';render();};
  async function importFile(commit){
    const file=el('import-file').files[0];
    if(!file||state.readingFile||state.pending||state.snapshot?.busy)return;
    if(commit&&(!state.snapshot?.import_preview?.valid||state.previewFile!==file))return;
    if(commit&&!el('import-name').reportValidity())return;
    state.readingFile=true;state.error='';render();
    try{
      if(!file.size||file.size>8*1024*1024)throw Error('Escolha um arquivo JSON de até 8 MiB.');
      const bytes=await file.arrayBuffer();
      const source_text=new TextDecoder('utf-8',{fatal:true,ignoreBOM:true}).decode(bytes);
      state.readingFile=false;
      const response=await send(commit?'import_commit':'import_preview',commit?{preview_id:state.snapshot.import_preview.id,source_text,name:el('import-name').value}:{source_text});
      if(response&&!commit)state.previewFile=file;
    }catch(error){state.error=error.message;}
    finally{state.readingFile=false;render();}
  }
  el('import-preview').onclick=()=>importFile(false);
  el('import-commit').onclick=()=>importFile(true);
  el('import-cancel').onclick=()=>{if(state.snapshot?.import_preview)send('import_cancel',{preview_id:state.snapshot.import_preview.id});};
  el('body').onchange=render;
  el('form').onsubmit=event=>{
    event.preventDefault();if(!el('form').reportValidity())return;
    const body=appState.physics.bodies.find(b=>b.id===el('body').value),jovian=body?.reference_id==='sol:naif:599';
    const latitude=Number(el('latitude').value),longitude=Number(el('longitude').value);
    const magnetic=jovian?{model:'JRM33',radius_m:Number(el('radius').value)*71492000,latitude_deg:latitude,longitude_east_deg:longitude,degree:13}:{model:'IGRF14',latitude_deg:latitude,longitude_deg:longitude,altitude_m:Number(el('altitude').value)};
    send('create',{source_guard:sourceGuard(),body_id:body.id,magnetic,configuration:{inner_radius_boundary_units:1,outer_radius_boundary_units:3,radial_count:65,azimuth_sectors:96,orientation:[[1,0,0],[0,1,0],[0,0,1]],vertical_amplification:200}});
  };
  for(const id of ['spatial-visible','magnetic-visible'])el(id).onchange=()=>send('set_visibility',{visible:{spatial:el('spatial-visible').checked,magnetic:el('magnetic-visible').checked}});
  el('leave').onclick=()=>send('leave');
  el('load-saved').onclick=()=>send('load_saved',{source_guard:sourceGuard()});
  for(const [id,operation] of [['save','save'],['load','load'],['export','export']])el(id).onclick=()=>send(operation);
  el('branch-create').onclick=()=>{if(el('branch-name').reportValidity())send('branch_create',{name:el('branch-name').value});};
  el('branch-load').onclick=()=>{if(el('branches').value)send('branch_load',{branch_id:el('branches').value});};
  el('branches').onchange=render;
  el('copy').onclick=async()=>{await command({utc:atlasState.epoch.utc},'Cena solar pausada pronta.','/api/solar/experiment');await poll();};
  el('cancel').onclick=async()=>{
    const id=state.snapshot?.transaction?.id;if(!id||state.cancelling)return;state.cancelling=true;render();
    try{const response=await fetch('/api/layers/cancel',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({transaction_id:id})});const value=await response.json();if(!response.ok||!value.ok)throw Error(value.error||'Cancelamento não confirmado.');accept(value.layers);state.error='Preparação cancelada; cena preservada.';}
    catch(error){state.error=error.message;}finally{state.cancelling=false;render();}
  };
  function open(){el('panel').hidden=false;opener.setAttribute('aria-expanded','true');el('panel-close').focus();poll();}
  function close(){el('panel').hidden=true;opener.setAttribute('aria-expanded','false');opener.focus();}
  opener.onclick=open;el('panel-close').onclick=close;
  el('panel').addEventListener('keydown',event=>{if(event.key==='Escape'){event.preventDefault();event.stopPropagation();close();}});
  setInterval(poll,500);poll();
})();
