"use strict";
let mapProbeIdentity=null;
function updateBodyFieldMap(layer){
  const available=layer&&['shell','cut'].includes(layer.representation),summary=layer?.map_summary;
  $('body-map-controls').hidden=!available;if(!available){mapProbeIdentity=null;return;}
  $('body-map-sample').disabled=pending;$('body-map-row').disabled=pending;$('body-map-column').disabled=pending;
  $('body-map-row').max=summary.shape[0]-1;$('body-map-column').max=summary.shape[1]-1;
  $('body-map-legend').textContent=`Cores: |B interno| de ${(summary.minimum_sampled_T*1e6).toPrecision(5)} a ${(summary.maximum_sampled_T*1e6).toPrecision(5)} µT na grade amostrada. ${summary.drawn_symbols} símbolos, tamanho gráfico. ${summary.shape[0]} linhas × ${summary.shape[1]} colunas, índices começando em zero. Pontos fora do domínio não são desenhados e não significam B = 0.`;
  $('body-map-palette').replaceChildren(...summary.palette_rgb.map(rgb=>{const swatch=document.createElement('span');swatch.style.flex='1';swatch.style.background=`rgb(${rgb.map(v=>Math.round(v*255)).join(',')})`;return swatch;}));
  const probe=layer.map_probe,identity=layer.render.id+'|'+(probe?probe.row+','+probe.column:'none');
  if(identity!==mapProbeIdentity){
    mapProbeIdentity=identity;$('body-map-row').value=probe?probe.row:Math.floor(summary.shape[0]/2);
    $('body-map-column').value=probe?probe.column:0;
  }
  $('body-map-reading').textContent=probe?`Marcador + · célula ${probe.row}/${probe.column} · ${probe.model}, grau ${probe.degree}\nÉpoca da amostra: ${probe.epoch.utc}\nPosição x/y/z em ${probe.frame}: ${probe.sample.position_model_m.map(v=>v.toExponential(6)).join(' / ')} m\nB x/y/z: ${probe.sample.field_model_T.map(v=>v.toExponential(6)).join(' / ')} T\n|B| = ${(probe.sample.field_norm_T*1e6).toPrecision(8)} µT. Mesmo dado que determinou a cor; incerteza local não propagada.`:'Escolha uma célula para consultar o mesmo valor SI usado pelo mapa. Células mascaradas ficam indisponíveis.';
}
window.updateBodyFieldMap=updateBodyFieldMap;
$('body-map-probe-form').onsubmit=async event=>{
  event.preventDefault();const layer=appState?.body_field_preview;
  if(pending||!layer||!$('body-map-probe-form').reportValidity())return;
  await command({command:'select_body_field_map_cell',layer_id:layer.render.id,row:Number($('body-map-row').value),column:Number($('body-map-column').value)},'Sonda na célula do mapa; leitura e evolução preservadas.');
};
