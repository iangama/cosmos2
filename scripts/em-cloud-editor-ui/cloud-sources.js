'use strict';
let sourceEditorKey=null;
function sourceVector(prefix){
  return ['x','y','z'].map(axis=>{
    const input=$(prefix+axis),value=input.valueAsNumber;
    if(input.value.trim()===''||!Number.isFinite(value))throw Error('Preencha componentes SI finitas.');
    return value;
  });
}
function setSourceVector(prefix,values){['x','y','z'].forEach((axis,index)=>$(prefix+axis).value=values[index]);}
function sourceScalar(id){const input=$(id),value=input.valueAsNumber;if(input.value.trim()===''||!Number.isFinite(value))throw Error('Preencha valores SI finitos.');return value;}
function renderCloudSources(){
  if(!state)return;
  const id=visual.selected_source_id,source=state.model.sources.find(s=>s.id===id);
  const key=state.system_id+'|'+state.edit_token+'|'+state.revision+'|'+id;
  if(key!==sourceEditorKey){
    sourceEditorKey=key;
    const select=$('field-source');select.replaceChildren(new Option('Nova fonte fixa',''));
    state.model.sources.forEach(s=>select.add(new Option(s.id,s.id)));select.value=source?.id||'';
    let next=1;while(state.model.sources.some(s=>s.id==='fonte-'+next))next++;
    $('field-source-id').value=source?.id||'fonte-'+next;
    setSourceVector('field-source-',source?.position_m||[0,0,0]);
    setSourceVector('field-moment-',source?.magnetic_moment_A_m2||[0,0,0]);
    $('field-source-charge').value=source?.charge_C??1e-12;
    $('field-source-radius').value=source?.exclusion_radius_m??.02;
  }
  $('field-source').disabled=pending;
  document.querySelectorAll('#cloud-source-form input,#cloud-source-form button').forEach(input=>input.disabled=pending||!state.paused);
  $('field-source-id').disabled=pending||!state.paused||Boolean(source);
  $('remove-field-source').disabled=pending||!state.paused||!source;
  $('apply-field-source').disabled=pending||!state.paused||(!source&&state.model.sources.length>=128);
  $('apply-field-source').textContent=source?'Aplicar fonte pausada':'Criar fonte pausada';
  $('source-count').textContent=state.model.sources.length+' de 128 fontes fixas · revisão '+state.revision;
  $('source-editor-note').textContent=state.paused?'Alterar fontes preserva as posições e velocidades e muda a hipótese de campo. O mapa anterior é removido; meça novamente.':'Pause para alterar fontes. Selecionar uma fonte preserva a evolução.';
}
$('field-source').onchange=()=>{
  const selected_source_id=$('field-source').value||null;
  run(()=>busy(()=>command('set_visual',{changes:{selected_source_id}})));
};
$('cloud-source-form').onsubmit=event=>{
  event.preventDefault();
  run(()=>busy(async()=>{
    const selected=visual.selected_source_id;
    const source={id:$('field-source-id').value,position_m:sourceVector('field-source-'),
      charge_C:sourceScalar('field-source-charge'),exclusion_radius_m:sourceScalar('field-source-radius'),
      magnetic_moment_A_m2:sourceVector('field-moment-')};
    const sources=state.model.sources.map(s=>s.id===selected?source:s);
    if(!selected){
      if(sources.some(s=>s.id===source.id))throw Error('Essa identidade já pertence a uma fonte.');
      sources.push(source);
    }
    await command('set_model',{model:{...state.model,sources}});
    await command('set_visual',{changes:{selected_source_id:source.id}});
    $('status').textContent='Fonte confirmada. Posições e velocidades da nuvem preservadas.';
  }));
};
$('remove-field-source').onclick=()=>run(()=>busy(async()=>{
  const sources=state.model.sources.filter(s=>s.id!==visual.selected_source_id);
  await command('set_model',{model:{...state.model,sources}});
  $('status').textContent='Fonte removida do modelo. Posições e velocidades preservadas.';
}));
window.renderCloudSources=renderCloudSources;
