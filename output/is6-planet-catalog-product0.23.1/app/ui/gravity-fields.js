'use strict';
let fieldsGuard=null,fieldsIdentity=null,fieldsBodyOptions='',fieldsReadingKey='';
const fieldScalar=v=>v===null||v===undefined?'—':v.toExponential(5);
const fieldVector=v=>v.map(fieldScalar).join(' / ');
function fieldCenterMode(){
  const follow=$('field-center-mode').value==='follow';
  $('field-body-label').hidden=!follow;
  $('field-center-note').textContent=follow?'Deslocamento a partir do corpo, nos eixos inerciais; sem girar com ele.':'Posição fixa em metros nos eixos do experimento.';
}
function loadFieldSettings(cfg){
  $('field-center-mode').value=cfg.center_mode;
  if(cfg.body_id)$('field-body').value=cfg.body_id;
  cfg.center_m.forEach((v,k)=>$('field-center-'+k).value=String(v));
  cfg.cut_orientation_deg.forEach((v,k)=>$('field-angle-'+k).value=String(v));
  $('field-shell-enabled').checked=cfg.shell_enabled;$('field-cut-enabled').checked=cfg.cut_enabled;
  $('field-radius').value=String(cfg.shell_radius_m);$('field-shell-count').value=String(cfg.shell_count);
  $('field-cut-width').value=String(cfg.cut_half_width_m);$('field-cut-resolution').value=String(cfg.cut_resolution);
  $('field-cut-offset').value=String(cfg.cut_offset_m);$('field-magnitude-scale').value=cfg.magnitude_scale;
  $('field-levels').value=cfg.potential_levels_J_kg.join(', ');fieldCenterMode();
}
function fieldIsStale(p,map){
  return map&&(map.system_id!==p.system_id||map.edit_token!==p.edit_token||map.revision!==p.revision||map.time!==p.time||map.fields_revision!==p.field_layers.revision);
}
function updateGravityFields(p,map,reading,visible){
  if(!p.field_layers)return;
  const identity=p.system_id+':'+p.edit_token,bodies=JSON.stringify(p.bodies.map(b=>[b.id,b.name]));
  if(bodies!==fieldsBodyOptions){
    const prior=$('field-body').value;$('field-body').replaceChildren(...p.bodies.map(b=>new Option(b.name,b.id)));
    if(p.bodies.some(b=>b.id===prior))$('field-body').value=prior;
    fieldsBodyOptions=bodies;
  }
  if(identity!==fieldsIdentity){fieldsIdentity=identity;fieldsGuard=null;loadFieldSettings(p.field_layers.settings);fieldsReadingKey='';}
  const current=fieldsGuard&&fieldsGuard.system_id===p.system_id&&fieldsGuard.edit_token===p.edit_token&&fieldsGuard.revision===p.revision&&fieldsGuard.expected_time===p.time&&fieldsGuard.fields_revision===p.field_layers.revision;
  $('fields-inputs').disabled=pending||!current;$('prepare-fields').disabled=pending;$('measure-fields').disabled=pending;
  for(const id of ['view-fields','toggle-fields','clear-fields','export-fields','read-field-sample'])$(id).disabled=pending||!map;
  $('toggle-fields').textContent=visible?'Esconder campo':'Mostrar campo';
  const stale=fieldIsStale(p,map);
  $('fields-status').textContent=map?(stale?'MAPA CONGELADO: o estado mudou desde a medição.\n':'Mapa do instante confirmado.\n')+'t='+fieldScalar(map.time*p.physical_scale.time_unit_s)+' s · '+map.frame+'\n'+map.sample_count+' pontos · '+map.source_ids.length+' fontes · cálculo '+map.evaluation_ms.toFixed(1)+' ms.\n'+(visible?'Camadas visíveis.':'Camadas escondidas.'):'Prepare a configuração ou meça o mapa salvo. O cálculo ocorre sob pedido, com quantidade limitada de pontos.';
  $('fields-colorbar').hidden=!map;
  if(map){
    const legend=map.magnitude_legend,parts=['Cor de |g|: '+(legend.scale==='log'?'logarítmica':'linear')+' · '+fieldScalar(legend.minimum)+' a '+fieldScalar(legend.maximum)+' m/s².'];
    if(map.shell)parts.push('Casca: '+map.shell.drawn_arrows+' setas, comprimento gráfico '+fieldScalar(map.shell.arrow_length_m)+' m; '+map.shell.invalid_samples+' pontos indisponíveis.');
    if(map.cut){parts.push('Corte: '+map.cut.grid.resolution+'×'+map.cut.grid.resolution+' leituras; '+map.cut.drawn_arrows+' setas com espaçamento de '+map.cut.arrow_grid_stride+' pontos.');parts.push('Equipotenciais Φ (J/kg): '+map.cut.levels_J_kg.map(fieldScalar).join(' / ')+'.');parts.push(map.cut.invalid_cells+' células com lacunas; '+map.cut.plateau_cells+' células de platô sem curva única.');}
    $('fields-legend').textContent=parts.join('\n');
  }else $('fields-legend').textContent='';
  const key=JSON.stringify([reading,stale]);
  if(key!==fieldsReadingKey){
    fieldsReadingKey=key;
    const sample=reading?.sample;
    $('field-sample-reading').textContent=sample?(stale?'Leitura do mapa congelado.\n':'')+reading.layer+' #'+sample.index+' · posição '+fieldVector(sample.position_m)+' m\n'+(sample.valid?'g: '+fieldVector(sample.acceleration_m_s2)+' m/s²\n|g|: '+fieldScalar(sample.acceleration_norm_m_s2)+' m/s²\nΦ: '+fieldScalar(sample.potential_J_kg)+' J/kg\nT x/y/z (s⁻²):\n'+sample.tidal_tensor_s_2.map(fieldVector).join('\n'):'Indisponível: '+sample.reason):'';
  }
  const layer=map?.[$('field-sample-layer').value];
  $('field-sample-index').max=String(Math.max(0,(layer?.sample_count||1)-1));
  $('read-field-sample').disabled=pending||!layer;
}
$('field-center-mode').onchange=()=>{[0,1,2].forEach(k=>$('field-center-'+k).value='0');fieldCenterMode();};
$('prepare-fields').onclick=async()=>{
  await command({command:'pause'},'Experimento pausado para configurar o campo.');
  const p=appState?.physics;if(!p?.paused)return;
  loadFieldSettings(p.field_layers.settings);fieldsGuard={...editGuard(p),fields_revision:p.field_layers.revision};
  updateGravityFields(p,appState.fields_preview,appState.field_reading,appState.fields_visible);
};
$('fields-form').onsubmit=async event=>{
  event.preventDefault();if(pending||!fieldsGuard)return;
  const follows=$('field-center-mode').value==='follow';
  const text=$('field-levels').value.trim(),levels=text?text.split(',').map(v=>v.trim()===''?NaN:Number(v)):[];
  if(levels.length>4||levels.some(v=>!Number.isFinite(v))||new Set(levels).size!==levels.length){$('notice').textContent='Use até quatro potenciais distintos, com ponto decimal, separados por vírgula.';return;}
  const cfg={center_mode:follows?'follow':'fixed',center_m:[0,1,2].map(k=>Number($('field-center-'+k).value)),body_id:follows?$('field-body').value:null,
    shell_enabled:$('field-shell-enabled').checked,shell_radius_m:Number($('field-radius').value),shell_count:Number($('field-shell-count').value),
    cut_enabled:$('field-cut-enabled').checked,cut_half_width_m:Number($('field-cut-width').value),cut_resolution:Number($('field-cut-resolution').value),
    cut_orientation_deg:[0,1,2].map(k=>Number($('field-angle-'+k).value)),cut_offset_m:Number($('field-cut-offset').value),
    magnitude_scale:$('field-magnitude-scale').value,potential_levels_J_kg:levels};
  await command({...fieldsGuard,command:'configure_fields',settings:cfg},'Configuração do campo salva. Meça para atualizar a cena.');fieldsGuard=null;
};
$('measure-fields').onclick=async()=>{
  await command({command:'pause'},'Experimento pausado para medir o campo.');
  const p=appState?.physics;if(!p?.paused)return;
  await command({...editGuard(p),fields_revision:p.field_layers.revision,command:'sample_fields'},'Mapa de campo confirmado e instalado na cena.');
};
$('view-fields').onclick=()=>{
  const render=appState?.fields_preview?.render;if(!render)return;
  const d=render.view_distance_m;
  script('openspace.navigation.setNavigationState({Anchor='+JSON.stringify(render.frame_node)+',ReferenceFrame="LabRoot",Position={0,'+(-d)+','+(d*.6)+'},Up={0,0,1}})');
};
$('field-sample-layer').onchange=()=>{if(appState?.physics)updateGravityFields(appState.physics,appState.fields_preview,appState.field_reading,appState.fields_visible);};
$('read-field-sample').onclick=()=>{
  if(!$('field-sample-index').reportValidity()||!appState?.fields_preview)return;
  command({command:'select_field_sample',map_id:appState.fields_preview.render.id,layer:$('field-sample-layer').value,index:Number($('field-sample-index').value)},'Leitura do mesmo instante do mapa.');
};
$('toggle-fields').onclick=()=>command({command:'set_fields_visible',visible:!appState.fields_visible},'Visibilidade do campo alterada.');
$('clear-fields').onclick=()=>command({command:'clear_fields'},'Mapa limpo; configuração e evolução preservadas.');
$('export-fields').onclick=async()=>{
  const result=await command({command:'export_fields'},'Mapa e fontes SI exportados.');
  if(result?.ack?.export_file)$('notice').textContent='Exportado: '+result.ack.export_file;
};
