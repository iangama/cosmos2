'use strict';
let orbitalSnapshot=null,orbitalIdentity='',orbitalOptions='',orbitalData=null,orbitalPreview=null;
let orbitalFetchPending=false,orbitalFetchTime=0,orbitalPoints=[];
const orbitalLabels={orbital_theta_inner:'θ interno (°; −180…180)',orbital_theta_outer:'θ externo (°; −180…180)',orbital_ratio:'Período externo / interno',orbital_offset:'Desvio da razão nominal (%)'};
Object.assign(historyQuantities,orbitalLabels);
function orbitalValue(row,quantity){
  if(!row.available)return null;
  if(quantity==='orbital_ratio')return row.period_ratio;
  if(quantity==='orbital_offset')return row.relative_offset*100;
  const angle=row.critical_angles?.[quantity==='orbital_theta_outer'?1:0]?.angle_rad;
  return Number.isFinite(angle)?Math.atan2(Math.sin(angle),Math.cos(angle))*180/Math.PI:null;
}
function orbitalAngleText(a){return Number.isFinite(a?.angle_rad)?(a.angle_rad*180/Math.PI).toFixed(6)+'°':'indefinido: periastro quase circular';}
function orbitalReadText(reading,p){
  if(!reading)return 'Meça a fase atual ou grave uma janela durante a evolução.';
  const stale=reading.time!==p.time||reading.revision!==p.revision||reading.configuration_revision!==p.orbital_instruments.revision||reading.edit_token!==p.edit_token;
  const heading=(stale?'Leitura histórica/congelada\n':'Instante confirmado\n')+'t = '+historyNumber(reading.time*p.physical_scale.time_unit_s)+' s · '+reading.frame;
  if(!reading.available)return heading+'\n'+reading.reason;
  const result=reading.result,ratio=result?result.outer_to_inner_period_ratio:reading.period_ratio,offset=result?result.relative_offset_from_nominal:reading.relative_offset;
  const angles=result?result.critical_angles:reading.critical_angles;
  return heading+'\nPeríodo externo / interno: '+ratio.toPrecision(10)+'\nDesvio do nominal: '+(offset*100).toPrecision(7)+'%\nθ interno: '+orbitalAngleText(angles[0])+'\nθ externo: '+orbitalAngleText(angles[1])+'\nLeitura instantânea; não confirma captura ou ressonância permanente.';
}
function updateOrbitalInstruments(p){
  const cfg=p.orbital_instruments;if(!cfg)return;
  const identity=p.system_id+'|'+p.edit_token;
  if(identity!==orbitalIdentity){orbitalIdentity=identity;orbitalSnapshot=null;orbitalData=null;orbitalPreview=null;orbitalOptions='';$('orbital-editor-fields').disabled=true;$('orbital-point-reading').textContent='';drawOrbitalChart();}
  const d=cfg.definition,missing=d?['primary_id','inner_id','outer_id'].map(k=>d[k]).filter(i=>!p.bodies.some(b=>b.id===i)):[];
  const options=JSON.stringify([p.bodies.map(b=>[b.id,b.name]),missing]);
  if(options!==orbitalOptions){
    for(const [index,key] of ['orbital-primary','orbital-inner','orbital-outer'].entries()){
      const previous=$(key).value,choices=p.bodies.map(b=>new Option(b.name,b.id));
      for(const id of missing)choices.push(new Option('Corpo removido · '+id.slice(-6),id));
      $(key).replaceChildren(...choices);
      if(choices.some(o=>o.value===previous))$(key).value=previous;else if(choices.length>index)$(key).selectedIndex=index;
    }
    orbitalOptions=options;
  }
  const stale=orbitalSnapshot&&(orbitalSnapshot.system_id!==p.system_id||orbitalSnapshot.edit_token!==p.edit_token||orbitalSnapshot.revision!==p.revision||orbitalSnapshot.expected_time!==p.time||orbitalSnapshot.orbital_revision!==cfg.revision);
  $('orbital-apply').disabled=pending||!orbitalSnapshot||!p.paused||Boolean(stale);
  $('orbital-align-plane').disabled=$('orbital-apply').disabled;
  $('orbital-disable').disabled=pending||!d;
  $('orbital-prepare').disabled=pending||p.bodies.length<3;
  $('orbital-sample').disabled=pending||!d;
  $('orbital-toggle').disabled=pending||!d;$('orbital-toggle').textContent=cfg.recording?'Parar gravação orbital':'Ativar gravação orbital';
  $('orbital-clear').disabled=pending||!cfg.sample_count;$('orbital-export').disabled=pending||!cfg.sample_count;
  $('orbital-cadence').disabled=pending;if(document.activeElement!==$('orbital-cadence'))$('orbital-cadence').value=String(cfg.cadence_wall_s);
  if(stale)$('orbital-editor-status').textContent='O instante, a revisão ou a definição mudou. Pause e carregue novamente.';
  const latest=orbitalPreview&&orbitalPreview.system_id===p.system_id&&orbitalPreview.edit_token===p.edit_token&&orbitalPreview.time===p.time&&orbitalPreview.configuration_revision===cfg.revision?orbitalPreview:cfg.latest;
  $('orbital-reading').textContent=orbitalReadText(latest,p);
  $('orbital-status').textContent=(cfg.recording?(p.paused?'Gravação ativada; aguardando evolução.':'Gravando estados confirmados.'): 'Gravação orbital parada.')+'\n'+cfg.sample_count+'/'+cfg.maximum_samples+' amostras · '+cfg.dropped+' descartadas · cadência '+cfg.cadence_wall_s+' s reais.'+(d?'\nCombinação: '+d.j+'λ externo − '+(d.j-1)+'λ interno − ϖ selecionado.':'\nNenhum instrumento definido.');
  if(!cfg.sample_count&&orbitalData?.samples.length){orbitalData={...cfg,samples:[]};drawOrbitalChart();}
  if($('orbital-panel').open&&(cfg.next_sequence!==orbitalData?.next_sequence||cfg.revision!==orbitalData?.revision))refreshOrbitalCurves();
}
function fillOrbitalEditor(){
  const p=appState?.physics;if(!p?.paused||p.bodies.length<3)return;
  const cfg=p.orbital_instruments,d=cfg.definition;
  orbitalSnapshot={...editGuard(p),orbital_revision:cfg.revision};
  if(d){$('orbital-primary').value=d.primary_id;$('orbital-inner').value=d.inner_id;$('orbital-outer').value=d.outer_id;}
  $('orbital-j').value=String(d?.j||2);
  for(const [kind,values] of [['normal',d?.plane_normal||[0,0,1]],['reference',d?.plane_reference||[1,0,0]]])values.forEach((v,i)=>$('orbital-'+kind+'-'+i).value=String(v));
  $('orbital-editor-fields').disabled=false;
  $('orbital-editor-status').textContent='Definição preparada no referencial '+p.contract.frame+'. Alterar este instrumento não aplica força ou intervenção física.';
  updateOrbitalInstruments(p);
}
function orbitalFormDefinition(){return {primary_id:$('orbital-primary').value,inner_id:$('orbital-inner').value,outer_id:$('orbital-outer').value,j:Number($('orbital-j').value),plane_normal:[0,1,2].map(i=>Number($('orbital-normal-'+i).value)),plane_reference:[0,1,2].map(i=>Number($('orbital-reference-'+i).value))};}
async function configureOrbital(operation,parameters={}){
  await command({command:'pause'},'Evolução pausada para configurar instrumentos orbitais.');
  const p=appState?.physics;if(!p?.paused)return;
  return command({...editGuard(p),orbital_revision:p.orbital_instruments.revision,command:'configure_orbital_instruments',operation,...parameters},'Instrumento orbital atualizado; integrador de forças preservado.');
}
$('orbital-prepare').onclick=async()=>{await command({command:'pause'},'Experimento pausado para preparar o instrumento.');fillOrbitalEditor();};
$('orbital-form').onsubmit=async event=>{
  event.preventDefault();if(pending||!orbitalSnapshot||!$('orbital-form').reportValidity())return;
  const result=await command({...orbitalSnapshot,command:'configure_orbital_instruments',operation:'definition',definition:orbitalFormDefinition()},'Definição orbital aplicada; sem alteração das forças.');
  if(result?.ok)fillOrbitalEditor();
};
$('orbital-align-plane').onclick=async()=>{
  if(pending||!orbitalSnapshot||!$('orbital-form').reportValidity())return;
  const result=await command({...orbitalSnapshot,command:'configure_orbital_instruments',operation:'align_plane',definition:orbitalFormDefinition()},'Plano da órbita interna fixado neste instante.');
  if(result?.ok)fillOrbitalEditor();
};
$('orbital-disable').onclick=()=>configureOrbital('definition',{definition:null});
$('orbital-toggle').onclick=()=>configureOrbital('capture',{recording:!appState.physics.orbital_instruments.recording,cadence_wall_s:Number($('orbital-cadence').value)});
$('orbital-cadence').onchange=()=>configureOrbital('capture',{recording:appState.physics.orbital_instruments.recording,cadence_wall_s:Number($('orbital-cadence').value)});
$('orbital-clear').onclick=()=>configureOrbital('clear');
$('orbital-sample').onclick=async()=>{
  await command({command:'pause'},'Experimento pausado para medir os ângulos.');const p=appState?.physics;if(!p?.paused)return;
  const result=await command({...editGuard(p),orbital_revision:p.orbital_instruments.revision,command:'sample_orbital_instruments'},'Leitura orbital do instante confirmado.');
  if(result?.ack?.result){orbitalPreview=result.ack.result;updateOrbitalInstruments(appState.physics);}
};
$('orbital-export').onclick=async()=>{const result=await command({command:'export_orbital_instruments'},'Histórico orbital exportado com estados SI selecionados.');if(result?.ack?.export_file)$('notice').textContent='Exportado: '+result.ack.export_file;};
for(const [key,preset] of [['orbital-new-resonant','resonant2'],['orbital-new-control','circulating18']])$(key).onclick=async()=>{
  await command({command:'pause'},'Preparando cenário orbital sintético.');const p=appState?.physics;if(!p?.paused)return;
  await command({...editGuard(p),command:'load_resonant_experiment',preset},'Novo cenário de três massas ativas. O instrumento não acrescenta forças.');fillOrbitalEditor();
};
async function refreshOrbitalCurves(){
  if(orbitalFetchPending||pending||!appState?.physics?.orbital_instruments||performance.now()-orbitalFetchTime<1000)return;
  orbitalFetchTime=performance.now();orbitalFetchPending=true;const identity=orbitalIdentity;
  try{const response=await fetch('/api/orbital/curves');if(!response.ok)return;const data=await response.json();if(identity===orbitalIdentity){orbitalData=data;drawOrbitalChart();}}
  catch{return;}finally{orbitalFetchPending=false;}
}
function drawOrbitalChart(){
  const canvas=$('orbital-chart'),ctx=canvas.getContext('2d'),w=canvas.width,h=canvas.height;
  ctx.clearRect(0,0,w,h);ctx.fillStyle='#0b1925';ctx.fillRect(0,0,w,h);ctx.fillStyle='#b4d5df';ctx.font='20px sans-serif';orbitalPoints=[];
  const rows=orbitalData?.samples||[],quantity=$('orbital-quantity').value,points=rows.map(row=>({row,value:orbitalValue(row,quantity)}));
  const valid=points.filter(p=>Number.isFinite(p.value));
  if(!valid.length){ctx.fillText('Aguardando amostras disponíveis',15,165);$('orbital-chart-legend').textContent='Órbita fora do domínio ou janela vazia: os dados ficam como lacunas.';return;}
  let ymin=Math.min(...valid.map(p=>p.value)),ymax=Math.max(...valid.map(p=>p.value));
  if(ymin===ymax){const margin=Math.max(Math.abs(ymin)*.03,1e-8);ymin-=margin;ymax+=margin;}
  const xmin=rows[0].time_s,xmax=rows.at(-1).time_s,left=112,right=w-16,top=35,bottom=h-60;
  const x=t=>left+(t-xmin)/(xmax===xmin?1:xmax-xmin)*(right-left),y=v=>bottom-(v-ymin)/(ymax-ymin)*(bottom-top);
  ctx.strokeStyle='#355264';ctx.lineWidth=1;
  for(let i=0;i<3;i++){const value=ymin+(ymax-ymin)*i/2,yy=y(value);ctx.beginPath();ctx.moveTo(left,yy);ctx.lineTo(right,yy);ctx.stroke();ctx.fillText(value.toExponential(2),5,yy+6);}
  ctx.fillText(xmin.toExponential(2),left,bottom+32);ctx.textAlign='right';ctx.fillText(xmax.toExponential(2),right,bottom+32);ctx.textAlign='left';ctx.fillText('t (s)',(left+right)/2-18,h-7);
  ctx.strokeStyle=ctx.fillStyle='#79dbeb';ctx.lineWidth=3;let prior=null;
  for(const point of points){
    if(!Number.isFinite(point.value)){prior=null;continue;}
    const current={x:x(point.row.time_s),y:y(point.value),sequence:point.row.sequence,value:point.value};
    const wrap=quantity.startsWith('orbital_theta')&&prior&&Math.abs(current.value-prior.value)>180;
    if(prior&&!point.row.break_before.length&&!wrap){ctx.beginPath();ctx.moveTo(prior.x,prior.y);ctx.lineTo(current.x,current.y);ctx.stroke();}
    ctx.beginPath();ctx.arc(current.x,current.y,3.5,0,Math.PI*2);ctx.fill();orbitalPoints.push(current);prior=current;
  }
  $('orbital-chart-legend').textContent=orbitalLabels[quantity]+'\n'+rows.length+' instantes físicos originais. Ângulos em −180…180°, com interrupção na passagem do limite. Lacunas e mudanças de definição interrompem traços.\nJanela finita e cadência real não certificam libracão ou captura permanente.';
}
$('orbital-quantity').onchange=drawOrbitalChart;
$('orbital-panel').addEventListener('toggle',()=>{if($('orbital-panel').open)refreshOrbitalCurves();});
$('orbital-chart').addEventListener('click',async event=>{
  if(pending||!orbitalPoints.length)return;
  const canvas=$('orbital-chart'),rect=canvas.getBoundingClientRect(),x=(event.clientX-rect.left)*canvas.width/rect.width,y=(event.clientY-rect.top)*canvas.height/rect.height;
  const chosen=orbitalPoints.reduce((a,b)=>Math.hypot(a.x-x,a.y-y)<=Math.hypot(b.x-x,b.y-y)?a:b);
  if(Math.hypot(chosen.x-x,chosen.y-y)>30)return;
  const p=appState.physics,result=await command({command:'orbital_point',system_id:p.system_id,edit_token:p.edit_token,sequence:chosen.sequence},'Amostra orbital original consultada; evolução preservada.');
  const record=result?.ack?.result;if(record)$('orbital-point-reading').textContent='Amostra #'+record.sequence+' · configuração '+record.reading.configuration_revision+'\n'+orbitalReadText(record.reading,p);
});
setInterval(()=>{const cfg=appState?.physics?.orbital_instruments;if(cfg&&$('orbital-panel').open&&appState.mode==='experiment'&&!pending&&(cfg.next_sequence!==orbitalData?.next_sequence||cfg.revision!==orbitalData?.revision))refreshOrbitalCurves();},1000);
