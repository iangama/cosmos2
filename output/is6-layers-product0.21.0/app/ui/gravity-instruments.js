'use strict';
let instrumentGuard=null,instrumentIdentity=null,instrumentOptions='',instrumentBodyOptions='';
function instrumentMode(){
  const follows=$('instrument-mode').value==='follow';
  $('instrument-body-field').hidden=!follows;$('instrument-exclusion-field').hidden=!follows;
  $('instrument-coordinates-note').textContent=follows?'Deslocamento em metros a partir do corpo, nos eixos inerciais.':'Coordenadas fixas em metros no referencial do experimento.';
}
function loadInstrumentDefinition(){
  const selected=appState?.physics?.instruments?.probes.find(p=>p.id===$('instrument-selection').value);
  if(!selected){instrumentGuard=null;return;}
  $('instrument-name').value=selected.name;$('instrument-mode').value=selected.mode;
  const point=selected.mode==='fixed'?selected.position_m:selected.offset_m;
  point.forEach((v,k)=>$('instrument-coordinate-'+k).value=String(v));
  if(selected.mode==='follow'){$('instrument-body').value=selected.body_id;$('instrument-exclude').checked=selected.exclude_followed_source;}
  instrumentMode();instrumentGuard=null;
}
function updateGravityInstruments(p,preview){
  const config=p.instruments;if(!config)return;
  const identity=p.system_id+':'+p.edit_token;
  if(instrumentIdentity!==identity){instrumentIdentity=identity;instrumentGuard=null;$('instrument-selection').value='';instrumentOptions='';}
  const options=JSON.stringify(config.probes.map(r=>[r.id,r.name]));
  if(options!==instrumentOptions){
    const prior=$('instrument-selection').value;
    $('instrument-selection').replaceChildren(new Option('Criar nova sonda',''),...config.probes.map(r=>new Option(r.name,r.id)));
    if(config.probes.some(r=>r.id===prior))$('instrument-selection').value=prior;
    instrumentOptions=options;
  }
  const bodies=JSON.stringify(p.bodies.map(b=>[b.id,b.name]));
  if(bodies!==instrumentBodyOptions){
    const prior=$('instrument-body').value;$('instrument-body').replaceChildren(...p.bodies.map(b=>new Option(b.name,b.id)));
    if(p.bodies.some(b=>b.id===prior))$('instrument-body').value=prior;
    instrumentBodyOptions=bodies;
  }
  const guardCurrent=instrumentGuard&&instrumentGuard.system_id===p.system_id&&instrumentGuard.edit_token===p.edit_token&&instrumentGuard.revision===p.revision&&instrumentGuard.expected_time===p.time&&instrumentGuard.instruments_revision===config.revision;
  $('instrument-fields').disabled=pending||!guardCurrent;
  $('prepare-instrument').disabled=pending;
  $('remove-instrument').disabled=pending||!$('instrument-selection').value;
  $('measure-instruments').disabled=pending||!config.probes.length;
  $('clear-instruments').disabled=pending||!preview;
  $('export-instruments').disabled=pending||!preview;
  const stale=preview&&(preview.system_id!==p.system_id||preview.edit_token!==p.edit_token||preview.revision!==p.revision||preview.time!==p.time||preview.instruments_revision!==config.revision);
  $('instruments-status').textContent=preview?(stale?'LEITURA CONGELADA: o estado mudou desde a medição.\n':'Leitura do estado atual confirmado.\n')+'t='+(preview.time*p.physical_scale.time_unit_s/3600).toPrecision(7)+' h · '+preview.frame+'\n'+config.probes.length+'/16 sondas.':'Definições salvas com a sessão. '+config.probes.length+'/16 sondas; prepare para criar ou editar.';
  const output=$('instruments-readings');output.replaceChildren();
  const vector=v=>v.map(x=>x.toExponential(5)).join(' / ');
  for(const reading of preview?.readings||[]){
    const row=document.createElement('p');
    row.textContent=reading.definition.name+' · '+(reading.available?'g: '+vector(reading.acceleration_m_s2)+' m/s²\n|g|: '+reading.acceleration_norm_m_s2.toExponential(5)+' m/s² · Φ: '+reading.potential_J_kg.toExponential(5)+' J/kg\nT x/y/z (s⁻²):\n'+reading.tidal_tensor_s_2.map(vector).join('\n')+(reading.excluded_source_ids.length?'\nFonte própria excluída explicitamente.':''):'Indisponível: '+reading.reason);
    output.append(row);
  }
  const selected=$('instrument-selection').value;
  $('view-instrument').disabled=pending||!preview?.render?.readings.some(r=>r.id===selected);
}
$('instrument-mode').onchange=()=>{[0,1,2].forEach(k=>$('instrument-coordinate-'+k).value=$('instrument-mode').value==='follow'?'0':String([1.7e10,-9e9,3e9][k]));instrumentMode();};
$('instrument-selection').onchange=()=>{loadInstrumentDefinition();if(appState?.physics)updateGravityInstruments(appState.physics,appState.instruments_preview);};
$('prepare-instrument').onclick=async()=>{
  await command({command:'pause'},'Experimento pausado para configurar as sondas.');
  const p=appState?.physics;if(!p?.paused)return;
  instrumentGuard={...editGuard(p),instruments_revision:p.instruments.revision};
  updateGravityInstruments(p,appState.instruments_preview);
};
$('instrument-form').onsubmit=async event=>{
  event.preventDefault();if(pending||!instrumentGuard)return;
  const selection=$('instrument-selection').value,mode=$('instrument-mode').value;
  const point=[0,1,2].map(k=>Number($('instrument-coordinate-'+k).value));
  const definition={name:$('instrument-name').value,mode,...(selection?{id:selection}:{}),...(mode==='fixed'?{position_m:point}:{body_id:$('instrument-body').value,offset_m:point,exclude_followed_source:$('instrument-exclude').checked})};
  const result=await command({...instrumentGuard,command:'configure_instruments',operation:selection?'update':'create',definition},'Definição salva. A evolução física permanece igual.');
  if(result?.ok){const probes=appState.physics.instruments.probes;$('instrument-selection').value=selection||probes[probes.length-1].id;loadInstrumentDefinition();updateGravityInstruments(appState.physics,appState.instruments_preview);}
};
$('remove-instrument').onclick=async()=>{
  await command({command:'pause'},'Experimento pausado.');const p=appState?.physics,id=$('instrument-selection').value;if(!p?.paused||!id)return;
  await command({...editGuard(p),instruments_revision:p.instruments.revision,command:'configure_instruments',operation:'remove',id},'Sonda removida; sua identidade não será reutilizada.');instrumentGuard=null;
};
$('measure-instruments').onclick=async()=>{
  await command({command:'pause'},'Experimento pausado para medir as sondas.');const p=appState?.physics;if(!p?.paused)return;
  await command({...editGuard(p),instruments_revision:p.instruments.revision,command:'sample_instruments'},'Leituras confirmadas no mesmo instante.');
};
$('clear-instruments').onclick=()=>command({command:'clear_instrument_readings'},'Leituras e marcas limpas. As definições e a física foram preservadas.');
$('view-instrument').onclick=()=>{
  const render=appState?.instruments_preview?.render?.readings.find(r=>r.id===$('instrument-selection').value);if(!render)return;
  const d=render.view_distance_m;script('openspace.navigation.setNavigationState({Anchor='+JSON.stringify(render.scene_node)+',ReferenceFrame="LabRoot",Position={0,'+(-d)+','+(d*.6)+'},Up={0,0,1}})');
};
$('export-instruments').onclick=async()=>{
  const result=await command({command:'export_instruments'},'Definições e leituras exportadas.');
  if(result?.ack?.export_file)$('notice').textContent='Exportado: '+result.ack.export_file;
};
instrumentMode();
