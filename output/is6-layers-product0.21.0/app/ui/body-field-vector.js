'use strict';

let restoredBodyFieldToken=null;
window.bodyFieldConfiguration=()=>({selected_body_id:$('solar-body').value,representation:$('body-field-representation').value,
  earth:earthCoordinates(),jupiter:jupiterCoordinates()});
function restoreBodyFieldConfiguration(p){
  if(!p.body_field_view||restoredBodyFieldToken===p.edit_token)return;
  restoredBodyFieldToken=p.edit_token;
  const c=p.body_field_view.configuration;
  $('solar-body').value=c.selected_body_id;$('body-field-representation').value=c.representation;
  ['earth-field-latitude','earth-field-longitude','earth-field-altitude'].forEach((id,i)=>$(id).value=c.earth[i]/(i===2?1000:1));
  ['jupiter-field-radius','jupiter-field-latitude','jupiter-field-longitude','jupiter-field-degree'].forEach((id,i)=>$(id).value=c.jupiter[i]/(i===0?71492000:1));
}
function updateBodyFieldVector(p,body) {
  restoreBodyFieldConfiguration(p);
  body=p.bodies.find(b=>b.id===$('solar-body').value);
  const available=body?.reference_id==='sol:naif:399'||body?.reference_id==='sol:naif:599';
  $('body-field-show').disabled=pending||!available;
  $('body-field-representation').disabled=pending||!available;
  const reference=body?.reference_id;
  $('body-field-model-status').textContent=reference==='sol:naif:399'?
    'Terra: IGRF14 interno, eixos ITRF93 e época da cena. Linhas restritas à altura WGS84 de 0 a 1000 km; sem campo externo.':
    reference==='sol:naif:599'?'Júpiter: JRM33 interno estático de 2019, Sistema III e época da cena; domínio numérico de 1 a 20 Rj, sem correntes externas.':
    reference==='sol:naif:301'?'Lua: modelo crostal, induzido e externo não adotados. Campo indisponível não significa B = 0.':
    reference==='sol:naif:10'?'Sol: campo solar e plasma não adotados nesta camada. Campo indisponível não significa B = 0.':
    'Nenhum modelo magnético adotado para este corpo.';
  const layer=appState?.body_field_preview;
  if(window.updateBodyFieldMap)updateBodyFieldMap(layer);
  $('body-field-visible').disabled=pending||!layer;$('body-field-visible').checked=layer?.visible??true;
  $('body-field-export').disabled=pending||!layer;
  $('body-field-clear').disabled=pending||!layer;
  $('body-field-view').disabled=pending||!layer;
  if (!layer) {
    $('body-field-status').textContent='Escolha Terra ou Júpiter. O vetor usa as coordenadas do formulário magnético correspondente.';
    return;
  }
  const r=layer.reading;
  const stale=['system_id','edit_token','revision','time'].some(k=>r[k]!==p[k]);
  const name=r.body_reference_id==='sol:naif:399'?'Terra · IGRF14':'Júpiter · JRM33';
  const oldCoordinates=r.body_reference_id==='sol:naif:399'?
    [r.coordinates.latitude_deg,r.coordinates.longitude_deg,r.coordinates.altitude_m]:
    [r.coordinates.radius_m,r.coordinates.latitude_planetocentric_deg,r.coordinates.longitude_east_deg,r.degree];
  const currentCoordinates=r.body_reference_id==='sol:naif:399'?earthCoordinates():jupiterCoordinates();
  const changed=currentCoordinates.some((v,i)=>v!==oldCoordinates[i]);
  const lineNote=layer.representation==='lines'?
    `Linhas internas 3D: ${layer.line_summary.curves} curvas, ${layer.line_summary.vertices} vértices.\n`+
    'Traçado interrompido nas bordas ou no limite de arco; não implica linha fechada. Setas verdes indicam +B; seu comprimento é gráfico. Não são trajetórias de partículas.\n':'';
  $('body-field-status').textContent=`${name}\n`+(layer.visible?'Camada visível.\n':'Camada oculta; leitura preservada.\n')+(layer.restored_from_checkpoint?'Amostra original restaurada do checkpoint.\n':'')+lineNote+
    (stale?'Amostra fixa: a fase atual mudou.\n':'Fase da camada confirmada.\n')+
    (changed?'Formulário alterado: a camada continua mostrando a amostra anterior.\n':'')+
    `Época da camada: ${r.epoch.utc}\n|B| = ${(r.field_norm_T*1e9).toPrecision(8)} nT\n`+
    `Seta verde: direção B; comprimento gráfico ${(layer.arrow_length_m/1000).toPrecision(6)} km.\n`+
    (r.body_reference_id==='sol:naif:399'?'Grade: elipsoide WGS84 de referência.':'Grade: esfera de referência JRM33; não representa superfície sólida ou achatamento.')+
    '\nPonto amarelo: posição da amostra. Sem força no centro neutro. A camada fica fixa ao evoluir; salvar/restaurar preserva a amostra e sua visibilidade.';
}
window.updateBodyFieldVector=updateBodyFieldVector;

$('body-field-show').onclick=async()=>{
  if(pending)return;
  const body=appState?.physics?.bodies.find(b=>b.id===$('solar-body').value);
  if(!body)return;
  const earth=body.reference_id==='sol:naif:399';
  if(!$(earth?'earth-field-form':'jupiter-field-form').reportValidity())return;
  await command({command:'pause'},'Evolução pausada para mostrar uma amostra do campo.');
  const p=appState?.physics;if(!p?.paused)return;
  let parameters;
  if(earth){const [latitude_deg,longitude_deg,altitude_m]=earthCoordinates();parameters={latitude_deg,longitude_deg,altitude_m};}
  else{const [radius_m,latitude_deg,east_longitude_deg,degree]=jupiterCoordinates();parameters={radius_m,latitude_deg,east_longitude_deg,degree};}
  await command({command:'show_body_field',model:earth?'IGRF14':'JRM33',representation:$('body-field-representation').value,...editGuard(p),body_id:body.id,...parameters},
    'Camada magnética confirmada no motor. Setas têm comprimento gráfico; linhas usam o campo interno.');
};
$('body-field-clear').onclick=async()=>{
  const layer=appState?.body_field_preview;if(pending||!layer)return;
  await command({command:'clear_body_field',layer_id:layer.render.id},'Camada magnética ocultada; exibição dos corpos restaurada.');
};
$('body-field-view').onclick=async()=>{
  const layer=appState?.body_field_preview;if(pending||!layer)return;
  await command({command:'view_body_field',layer_id:layer.render.id},'Vista da amostra magnética fixa.');
};

$('body-field-visible').onchange=async()=>{
  const layer=appState?.body_field_preview;if(pending||!layer)return;
  await command({command:'set_body_field_visible',layer_id:layer.render.id,visible:$('body-field-visible').checked},'Visibilidade alterada; leitura e evolução preservadas.');
};
$('body-field-export').onclick=async()=>{
  const layer=appState?.body_field_preview;if(pending||!layer)return;
  const result=await command({command:'export_body_field',layer_id:layer.render.id,configuration:bodyFieldConfiguration()},'Leitura magnética exportada.');
  if(result?.ack?.result?.export_file)$('notice').textContent='Exportado: '+result.ack.result.export_file;
};
