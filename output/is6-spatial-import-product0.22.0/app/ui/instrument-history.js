'use strict';
let historyIdentity=null,historyData=null,historyOptions='',historyFetchPending=false,historyLastSequence=-1,historyLastFetch=0,historyPlotPoints=[];
const historyQuantities={acceleration_norm_m_s2:'|g| (m/s²)',potential_J_kg:'Φ (J/kg)',tidal_xx_s_2:'Txx (s⁻²)',energy_J:'E (J)',energy_error:'Erro relativo de E',momentum_error_normalized:'Erro normalizado de P',angular_momentum_error_normalized:'Erro normalizado de L'};
const historyNumber=v=>v===null||v===undefined?'—':v.toExponential(5);
function updateInstrumentHistory(p,preview,comparison){
  const h=p.instrument_history;if(!h)return;
  const identity=p.system_id+':'+p.edit_token;
  if(identity!==historyIdentity){historyIdentity=identity;historyData=null;historyLastSequence=-1;historyOptions='';$('history-point-reading').textContent='';}
  const probes=preview?.readings||[],choices=[...new Map([...p.instruments.probes.map(r=>({id:r.id,name:r.name})),...probes.map(r=>({id:r.id,name:r.definition.name})),...(historyData?.samples.flatMap(r=>r.probes)||[])].map(r=>[r.id,r])).values()];
  const options=JSON.stringify(choices.map(r=>[r.id,r.name]));
  if(options!==historyOptions){
    for(const id of ['compare-probe-a','compare-probe-b']){
      const previous=$(id).value;$(id).replaceChildren(...choices.map(r=>new Option(r.name+' · '+r.id.slice(-6),r.id)));
      if(choices.some(r=>r.id===previous))$(id).value=previous;
    }
    if(choices.length>1&&$('compare-probe-a').value===$('compare-probe-b').value)$('compare-probe-b').selectedIndex=1;
    historyOptions=options;drawHistory();
  }
  const selectedA=probes.find(r=>r.id===$('compare-probe-a').value),selectedB=probes.find(r=>r.id===$('compare-probe-b').value);
  $('compare-probes').disabled=pending||!selectedA?.available||!selectedB?.available||selectedA.id===selectedB.id;
  $('history-toggle').disabled=pending||!p.instruments.probes.length;
  $('history-toggle').textContent=h.recording?'Parar gravação':'Ativar gravação';
  $('history-cadence').disabled=pending;
  if(document.activeElement!==$('history-cadence'))$('history-cadence').value=String(h.cadence_wall_s);
  $('history-clear').disabled=pending||!h.sample_count;$('history-export').disabled=pending||!h.sample_count;
  $('history-status').textContent=(h.recording?(p.paused?'Gravação ativada; aguardando iniciar a evolução.':'Gravando estados confirmados.'): 'Gravação parada.')+(p.material_tides?'\nEnergia auditada inclui calor acumulado; L inclui spin material.':Object.keys(p.gravity_effects||{}).length?'\nJ2 inclui energia quadrupolar; erro de L orbital indisponível sob eixo prescrito.':'')+'\n'+h.sample_count+'/'+h.maximum_samples+' amostras · '+h.dropped+' descartadas da janela.\nCadência solicitada: '+h.cadence_wall_s+' s reais; instante físico de cada ponto preservado.';
  if(comparison){
    const stale=comparison.system_id!==p.system_id||comparison.edit_token!==p.edit_token||comparison.revision!==p.revision||comparison.time!==p.time||comparison.instruments_revision!==p.instruments.revision;
    const vector=v=>v.map(historyNumber).join(' / ');
    $('probe-comparison-reading').textContent=(stale?'Comparação da leitura congelada.\n':'Comparação do instante confirmado.\n')+'Distância: '+historyNumber(comparison.distance_m)+' m\nΔg: '+vector(comparison.delta_acceleration_m_s2)+' m/s²\n|Δg|: '+historyNumber(comparison.delta_acceleration_norm_m_s2)+' m/s²\nΔΦ: '+historyNumber(comparison.delta_potential_J_kg)+' J/kg\nAutovalores de T na primeira sonda (s⁻²): '+vector(comparison.first_tidal_eigenvalues_s_2)+'\n'+(comparison.same_included_sources?'T·Δx: '+vector(comparison.linear_tidal_prediction_m_s2)+' m/s²\nResíduo da aproximação local: '+historyNumber(comparison.linear_tidal_residual_norm_m_s2)+' m/s².':'As sondas excluem fontes diferentes; a aproximação T·Δx fica indisponível.');
  }else $('probe-comparison-reading').textContent='';
  if($('instrument-history').open&&(h.next_sequence!==historyLastSequence||h.revision!==historyData?.revision)&&!historyFetchPending)refreshHistory();
}
async function refreshHistory(){
  if(historyFetchPending||!appState?.physics?.instrument_history||performance.now()-historyLastFetch<1000)return;
  historyLastFetch=performance.now();
  historyFetchPending=true;const identity=historyIdentity;
  try{
    const response=await fetch('/api/instruments/history');if(!response.ok)return;
    const data=await response.json();
    if(identity===historyIdentity){historyData=data;historyLastSequence=data.next_sequence;drawHistory();}
  }catch{return;}finally{historyFetchPending=false;}
}
function drawHistory(){
  const canvas=$('history-chart'),ctx=canvas.getContext('2d'),w=canvas.width,h=canvas.height;
  ctx.clearRect(0,0,w,h);ctx.fillStyle='#0b1925';ctx.fillRect(0,0,w,h);ctx.font='20px sans-serif';ctx.fillStyle='#b4d5df';
  const rows=historyData?.samples||[],quantity=$('history-quantity').value,log=$('history-scale').value==='log';
  const selected=[$('compare-probe-a').value,$('compare-probe-b').value].filter((v,k,a)=>v&&a.indexOf(v)===k);
  const probeQuantity=['acceleration_norm_m_s2','potential_J_kg','tidal_xx_s_2'].includes(quantity);
  const ids=probeQuantity?selected:[null],colors=['#79dbeb','#ffb35a'];
  const getValue=(row,id)=>id===null?row.integrals[quantity]:row.probes.find(p=>p.id===id&&p.available)?.[quantity];
  const transform=v=>Number.isFinite(v)&&(!log||v>0)?(log?Math.log10(v):v):null;
  const valid=rows.flatMap(r=>ids.map(id=>transform(getValue(r,id)))).filter(v=>v!==null);
  historyPlotPoints=[];
  if(!rows.length||!valid.length){ctx.fillText('Aguardando leituras disponíveis',20,165);$('history-chart-legend').textContent='Sem pontos disponíveis nesta grandeza/escala.';return;}
  let ymin=Math.min(...valid),ymax=Math.max(...valid),xmin=rows[0].time_s,xmax=rows[rows.length-1].time_s;
  if(ymin===ymax){const margin=Math.max(Math.abs(ymin)*.03,log ? .1 : 1e-30);ymin-=margin;ymax+=margin;}
  const axisOffset=!log&&(ymax-ymin)<1e-2*Math.max(Math.abs(ymin),Math.abs(ymax))?(ymin+ymax)/2:0;
  if(xmin===xmax)xmax=xmin+1;
  const left=112,right=w-16,top=35,bottom=h-60;
  const x=t=>left+(t-xmin)/(xmax-xmin)*(right-left),y=v=>bottom-(v-ymin)/(ymax-ymin)*(bottom-top);
  ctx.strokeStyle='#355264';ctx.lineWidth=1;
  for(let i=0;i<3;i++){const v=ymin+(ymax-ymin)*i/2,yy=y(v);ctx.beginPath();ctx.moveTo(left,yy);ctx.lineTo(right,yy);ctx.stroke();ctx.fillText((log?10**v:v-axisOffset).toExponential(2),5,yy+6);}
  ctx.fillText(xmin.toExponential(2),left,bottom+32);ctx.textAlign='right';ctx.fillText(xmax.toExponential(2),right,bottom+32);ctx.textAlign='left';ctx.fillText('t (s)',(left+right)/2-18,h-7);
  ids.forEach((id,k)=>{
    ctx.strokeStyle=colors[k];ctx.fillStyle=colors[k];ctx.lineWidth=3;let prior=null;
    for(const row of rows){
      const value=transform(getValue(row,id));if(value===null){prior=null;continue;}
      const point={x:x(row.time_s),y:y(value),sequence:row.sequence,time:row.time_s};
      if(prior&&!row.break_before.length){ctx.beginPath();ctx.moveTo(prior.x,prior.y);ctx.lineTo(point.x,point.y);ctx.stroke();}
      ctx.beginPath();ctx.arc(point.x,point.y,3.5,0,Math.PI*2);ctx.fill();historyPlotPoints.push(point);prior=point;
    }
  });
  const names=selected.map((id,k)=>[k?'Laranja':'Ciano',(rows.flatMap(r=>r.probes).find(p=>p.id===id)?.name||id)] .join(': '));
  $('history-chart-legend').textContent=historyQuantities[quantity]+' · '+(log?'escala logarítmica; valores≤0 viram lacunas.':'escala linear.')+(axisOffset?'\nEixo vertical: diferença em relação a '+axisOffset.toExponential(10)+' na unidade acima.':'')+'\n'+(probeQuantity?names.join('\n'):'Balanço translacional dos centros.')+'\n'+rows.length+' instantes confirmados; traços não preenchem lacunas.';
}
$('compare-probes').onclick=()=>{
  const r=appState?.instruments_preview;if(!r)return;
  command({command:'compare_instruments',system_id:r.system_id,reading_edit_token:r.edit_token,reading_time:r.time,reading_revision:r.revision,reading_instruments_revision:r.instruments_revision,
    first_id:$('compare-probe-a').value,second_id:$('compare-probe-b').value},'Comparação de duas leituras do mesmo instante.');
};
async function configureHistory(recording,cadence=Number($('history-cadence').value)){
  await command({command:'pause'},'Experimento pausado para configurar gravação.');
  const p=appState?.physics;if(!p?.paused)return;
  await command({...editGuard(p),instruments_revision:p.instruments.revision,history_revision:p.instrument_history.revision,
    command:'configure_history',recording,cadence_wall_s:cadence},recording?'Gravação ativada. Inicie a evolução para coletar leituras.':'Gravação parada; janela preservada.');
}
$('history-toggle').onclick=()=>configureHistory(!appState.physics.instrument_history.recording);
$('history-cadence').onchange=()=>configureHistory(appState.physics.instrument_history.recording);
$('history-clear').onclick=async()=>{
  await command({command:'pause'},'Experimento pausado.');const p=appState?.physics;if(!p?.paused)return;
  await command({...editGuard(p),instruments_revision:p.instruments.revision,history_revision:p.instrument_history.revision,command:'clear_history'},'Janela de leituras limpa; definições e física preservadas.');historyLastSequence=-1;refreshHistory();
};
$('history-export').onclick=async()=>{const result=await command({command:'export_history'},'Histórico exportado com fontes SI e cadência.');if(result?.ack?.export_file)$('notice').textContent='Exportado: '+result.ack.export_file;};
for(const id of ['history-quantity','history-scale','compare-probe-a','compare-probe-b'])$(id).addEventListener('change',drawHistory);
$('instrument-history').addEventListener('toggle',()=>{if($('instrument-history').open)refreshHistory();});
$('history-chart').addEventListener('click',async event=>{
  if(pending||!historyPlotPoints.length)return;
  const canvas=$('history-chart'),rect=canvas.getBoundingClientRect(),cx=(event.clientX-rect.left)*canvas.width/rect.width,cy=(event.clientY-rect.top)*canvas.height/rect.height;
  const chosen=historyPlotPoints.reduce((a,b)=>Math.hypot(a.x-cx,a.y-cy)<=Math.hypot(b.x-cx,b.y-cy)?a:b),p=appState.physics;
  const result=await command({command:'history_point',system_id:p.system_id,edit_token:p.edit_token,sequence:chosen.sequence},'Consulta histórica; a evolução física foi preservada.');
  const record=result?.ack?.result;if(!record)return;
  const reasons={state_or_instrument_definition_changed:'estado físico ou sondas alterados',cadence_gap:'intervalo de coleta maior que a cadência',physical_time_did_not_increase:'tempo físico não avançou'};
  $('history-point-reading').textContent='Amostra #'+record.sequence+' · t='+historyNumber(record.reading.time*p.physical_scale.time_unit_s)+' s\n'+record.reading.frame+'\n'+(record.break_before.length?'Início após lacuna: '+record.break_before.map(r=>reasons[r]).join(', '):'Sem lacuna anterior registrada.');
});
setInterval(()=>{const h=appState?.physics?.instrument_history;if(h&&$('instrument-history').open&&appState.mode==='experiment'&&!pending&&(h.next_sequence!==historyLastSequence||h.revision!==historyData?.revision))refreshHistory();},1000);
