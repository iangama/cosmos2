'use strict';
let solarZoneState=null,solarZonePending=false,solarZoneError='',solarZoneCurves=null,solarZoneCurveId=null,solarZoneCurvePending=false,solarZoneFormId=null;
const zoneChannels=['pp','dp','he3he3','c12pg','n13beta','c13pg','n14pg','o15beta','n15pa','he3alpha','be7ec','li7pa','be7p','b8beta2a','n15pg','o16pg','f17beta','o17pa'];
const zoneChannelLabels=['p + p → d + e⁺ + ν','d + p → He-3 + γ','He-3 + He-3 → He-4 + 2p','C-12 + p → N-13 + γ','N-13 → C-13 + e⁺ + ν','C-13 + p → N-14 + γ','N-14 + p → O-15 + γ','O-15 → N-15 + e⁺ + ν','N-15 + p → C-12 + He-4','He-3 + He-4 → Be-7 + γ','Be-7 + e⁻ → Li-7 + ν · plasma solar','Li-7 + p → 2 He-4','Be-7 + p → B-8 + γ','B-8 → 2 He-4 + e⁺ + ν · efetivo','N-15 + p → O-16 + γ','O-16 + p → F-17 + γ','F-17 → O-17 + e⁺ + ν','O-17 + p → N-14 + He-4'];
const zoneFields={temperature_K:'temperature',density_kg_m3:'density',hydrogen_fraction:'hydrogen',catalyst_fraction:'catalyst',catalyst_seed:'seed',duration_s:'duration',volume_m3:'volume'};
const zoneNumber=x=>x===null||x===undefined?'indisponível':(Object.is(Number(x),-0)?0:Number(x)).toLocaleString('pt-BR',{maximumSignificantDigits:7,notation:x!==0&&(Math.abs(x)<1e-4||Math.abs(x)>=1e7)?'scientific':'standard'});
const zoneEventRate=(s,c)=>s.event_rates_m3_s[c]<0?'≈ 0 (resíduo '+zoneNumber(s.event_rates_m3_s[c])+')':zoneNumber(s.event_rates_m3_s[c]);
const zoneAbundance=x=>Number(x)<0&&Number(x)>=-1e-20?'≈ 0 (resíduo '+zoneNumber(x)+')':zoneNumber(x);
for(let i=0;i<zoneChannels.length;i++){
  const label=document.createElement('label');label.className='compact-check';const input=document.createElement('input');input.type='checkbox';input.checked=true;input.id='zone-channel-'+zoneChannels[i];label.append(input,document.createTextNode(' '+zoneChannelLabels[i]));$('zone-channels').append(label);
}
const zoneFactorValues={};
function zonePhysicsOptions(){if(!$('zone-coulomb').checked)$('zone-screening').checked=false;$('zone-screening').disabled=!$('zone-coulomb').checked;}
$('zone-coulomb').onchange=zonePhysicsOptions;
zoneChannels.forEach((c,i)=>{const row=document.createElement('div');row.className='zone-factor-row';const name=document.createElement('span');name.textContent=zoneChannelLabels[i];const value=document.createElement('span');value.className='zone-factor-value';row.append(name,value);$('zone-screening-table').append(row);zoneFactorValues[c]=value;});
function zoneDrawSigned(canvas,series,index){
  const ctx=canvas.getContext('2d'),W=canvas.width,H=canvas.height,L=92,R=20,T=20,B=30;
  ctx.clearRect(0,0,W,H);const values=series.flatMap(s=>s.values).filter(Number.isFinite);let lo=Math.min(...values),hi=Math.max(...values);
  const pad=hi===lo?Math.max(Math.abs(lo)*.05,1):(hi-lo)*.07;lo-=pad;hi+=pad;
  const y=v=>H-B-(H-T-B)*(v-lo)/(hi-lo);ctx.font='12px Segoe UI';ctx.lineWidth=1;ctx.fillStyle='#9eb9ca';ctx.strokeStyle='#24404e';
  for(let j=0;j<=2;j++){const v=lo+(hi-lo)*j/2,yy=y(v);ctx.beginPath();ctx.moveTo(L,yy);ctx.lineTo(W-R,yy);ctx.stroke();ctx.fillText(zoneNumber(v),4,yy+4);}
  if(lo<=0&&hi>=0){ctx.strokeStyle='#526879';ctx.beginPath();ctx.moveTo(L,y(0));ctx.lineTo(W-R,y(0));ctx.stroke();}
  for(const i of [0,120,240])ctx.fillText(String(i),L+(W-L-R)*i/240-7,H-9);
  for(const s of series){ctx.beginPath();ctx.strokeStyle=s.color;ctx.lineWidth=s.reference?1.4:2.2;ctx.setLineDash(s.reference?[6,4]:[]);s.values.forEach((v,i)=>{const x=L+(W-L-R)*i/240;if(i===0)ctx.moveTo(x,y(v));else ctx.lineTo(x,y(v));});ctx.stroke();}
  ctx.setLineDash([]);const x=L+(W-L-R)*index/240;ctx.strokeStyle='#dfedf2';ctx.beginPath();ctx.moveTo(x,T);ctx.lineTo(x,H-B);ctx.stroke();
  for(const s of series.filter(s=>!s.reference)){ctx.fillStyle=s.color;ctx.beginPath();ctx.arc(x,y(s.values[index]),3.2,0,2*Math.PI);ctx.fill();}
}
function zoneGuard(){const w=solarZoneState?.worker;if(!w)throw Error('Atualize a leitura da zona solar.');return Object.fromEntries(['worker_id','artifact_id','edit_token','revision'].map(k=>[k,w[k]]));}
function zoneConfiguration(){return {parameters:Object.fromEntries(Object.entries(zoneFields).map(([k,id])=>[k,k==='catalyst_seed'?$('zone-'+id).value:Number($('zone-'+id).value)])),acting:Object.fromEntries(['strong','weak','electromagnetic'].map(k=>[k,$('zone-'+k).checked])),channel_switches:Object.fromEntries(zoneChannels.map(k=>[k,$('zone-channel-'+k).checked])),mode:'prescribed_density',density_history:($('zone-history').value==='constant'?{kind:'constant'}:{kind:$('zone-history').value,ratio:Number($('zone-ratio').value)}),include_coulomb:$('zone-coulomb').checked,include_screening:$('zone-screening').checked};}
function zoneFillConfiguration(w){const c=w.configuration;for(const [k,id] of Object.entries(zoneFields))$('zone-'+id).value=c.parameters[k];for(const k of ['strong','weak','electromagnetic'])$('zone-'+k).checked=c.acting[k];for(const k of zoneChannels)$('zone-channel-'+k).checked=c.channel_switches[k];$('zone-history').value=c.density_history.kind;$('zone-ratio').value=c.density_history.ratio??1;$('zone-coulomb').checked=c.include_coulomb;$('zone-screening').checked=c.include_screening;zonePhysicsOptions();solarZoneFormId=w.artifact_id;}
async function solarZoneCommand(command,extra={}){
  if(solarZonePending)return;solarZonePending=true;solarZoneError='';renderSolarZone();
  $("notice").textContent="Confirmando zona solar · órbita pausada.";
  try{
    const request={command,...extra};if(!['create','load_saved'].includes(command))request.guard=zoneGuard();
    const response=await fetch('/api/solar-zone/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request)}),value=await response.json();
    if(!response.ok||!value.ok)throw Error(value.error||'Comando da zona solar recusado.');
    solarZoneState=value.zone;$("notice").textContent=solarZoneState.active?"Zona solar · instante "+solarZoneState.worker.view.selected_index+"/240 confirmado · órbita preservada.":"Zona solar encerrada · órbita preservada.";if(command==='export'&&value.result?.path)$('zone-file').textContent='Exportado: '+value.result.path;
    return value;
  }catch(error){solarZoneError=error.message;$("notice").textContent=error.message;}finally{solarZonePending=false;renderSolarZone();}
}
async function zoneLoadCurves(){
  if(solarZoneCurvePending||solarZonePending||!solarZoneState?.active)return;
  const id=solarZoneState.worker.artifact_id;if(solarZoneCurveId===id)return;
  solarZoneCurvePending=true;
  try{
    const response=await fetch('/api/solar-zone/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command:'get_result',guard:zoneGuard()})}),value=await response.json();
    if(!response.ok||!value.ok)throw Error(value.error||'As curvas não foram carregadas.');
    if(solarZoneState?.worker?.artifact_id===id){solarZoneCurves=value.result;solarZoneCurveId=id;}
  }catch(error){solarZoneError=error.message;}finally{solarZoneCurvePending=false;renderSolarZone();}
}
function zoneDraw(canvas,series,index,maxFixed=null){
  const ctx=canvas.getContext('2d'),W=canvas.width,H=canvas.height,L=88,R=20,T=20,B=30;
  ctx.clearRect(0,0,W,H);const ymax=maxFixed??(Math.max(0,...series.flatMap(s=>s.values))>0?Math.max(...series.flatMap(s=>s.values))*1.07:1);
  ctx.font='12px Segoe UI';ctx.lineWidth=1;ctx.fillStyle='#9eb9ca';ctx.strokeStyle='#24404e';
  for(let j=0;j<=2;j++){const y=T+(H-T-B)*j/2;ctx.beginPath();ctx.moveTo(L,y);ctx.lineTo(W-R,y);ctx.stroke();ctx.fillText(zoneNumber(ymax*(1-j/2)),5,y+4);}
  for(const i of [0,120,240]){const x=L+(W-L-R)*i/240;ctx.fillText(String(i),x-7,H-9);}
  for(const s of series){ctx.beginPath();ctx.strokeStyle=s.color;ctx.lineWidth=s.reference?1.4:2.2;ctx.setLineDash(s.reference?[6,4]:[]);s.values.forEach((v,i)=>{const x=L+(W-L-R)*i/240,y=H-B-(H-T-B)*v/ymax;if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);});ctx.stroke();}
  ctx.setLineDash([]);const x=L+(W-L-R)*index/240;ctx.strokeStyle='#dfedf2';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(x,T);ctx.lineTo(x,H-B);ctx.stroke();
  for(const s of series.filter(s=>!s.reference)){const y=H-B-(H-T-B)*s.values[index]/ymax;ctx.fillStyle=s.color;ctx.beginPath();ctx.arc(x,y,3.2,0,2*Math.PI);ctx.fill();}
}
function zoneDrawLog(canvas,series,index){
  const ctx=canvas.getContext('2d'),W=canvas.width,H=canvas.height,L=88,R=20,T=20,B=30;
  ctx.clearRect(0,0,W,H);ctx.font='12px Segoe UI';ctx.fillStyle='#9eb9ca';
  const positive=series.flatMap(s=>s.values).filter(v=>Number.isFinite(v)&&v>0);
  if(!positive.length){ctx.fillText('Sem frações positivas no intervalo.',L,H/2);return;}
  const lo=Math.floor(Math.log10(Math.min(...positive)));let hi=Math.ceil(Math.log10(Math.max(...positive)));if(hi===lo)hi=lo+1;
  const y=v=>H-B-(H-T-B)*(Math.log10(v)-lo)/(hi-lo);
  ctx.strokeStyle='#24404e';ctx.lineWidth=1;
  for(const exponent of [lo,Math.floor((lo+hi)/2),hi]){const yy=H-B-(H-T-B)*(exponent-lo)/(hi-lo);ctx.beginPath();ctx.moveTo(L,yy);ctx.lineTo(W-R,yy);ctx.stroke();ctx.fillText('10^'+exponent,5,yy+4);}
  for(const i of [0,120,240]){const x=L+(W-L-R)*i/240;ctx.fillText(String(i),x-7,H-9);}
  for(const s of series){ctx.beginPath();ctx.strokeStyle=s.color;ctx.lineWidth=s.reference?1.4:2.2;ctx.setLineDash(s.reference?[6,4]:[]);let started=false;
    s.values.forEach((v,i)=>{if(!Number.isFinite(v)||v<=0){started=false;return;}const x=L+(W-L-R)*i/240;if(!started){ctx.moveTo(x,y(v));started=true;}else ctx.lineTo(x,y(v));});ctx.stroke();}
  ctx.setLineDash([]);const x=L+(W-L-R)*index/240;ctx.strokeStyle='#dfedf2';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(x,T);ctx.lineTo(x,H-B);ctx.stroke();
  for(const s of series.filter(s=>!s.reference&&s.values[index]>0)){ctx.fillStyle=s.color;ctx.beginPath();ctx.arc(x,y(s.values[index]),3.2,0,2*Math.PI);ctx.fill();}
}
function zoneRenderCharts(w){
  const view=w.view.visible,i=w.view.selected_index,ready=solarZoneCurveId===w.artifact_id&&solarZoneCurves;
  for(const k of ['composition','energy','neutrinos'])$('zone-'+k+'-chart').hidden=!view[k];
  $('zone-temperature-chart').hidden=!view.energy;$('zone-coulomb-chart').hidden=!view.energy;for(const name of ['density','volume','work'])$('zone-'+name+'-chart').hidden=!view.energy;
  $('zone-branch-composition-chart').hidden=!view.composition;
  $('zone-b8-chart').hidden=!view.composition;
  $('zone-cno-chart').hidden=!view.composition;
  $('zone-chart-status').textContent=ready?'Instante '+i+'/240 · t = '+zoneNumber(w.sample.actual.time_s)+' s desde o início nuclear.':'Carregando as curvas deste cenário…';
  if(!ready){for(const k of ['composition','branch-composition','b8','cno','temperature','coulomb','density','volume','work','energy','neutrinos']){const c=$('zone-'+k+'-canvas');c.getContext('2d').clearRect(0,0,c.width,c.height);}zoneLoadCurves();return;}
  function series(spec){const result=[];for(const [field,color,column] of spec){for(const ref of view.reference?[false,true]:[false]){const network=solarZoneCurves[ref?'reference':'actual'];result.push({color,reference:ref,values:column===undefined?network[field]:network[field].map(a=>a[column])});}}return result;}
  if(view.composition)zoneDraw($('zone-composition-canvas'),series([['mass_fractions','#7addd6',0],['mass_fractions','#edba79',3]]),i,1);
  if(view.composition)zoneDraw($('zone-branch-composition-canvas'),series([['mass_fractions','#7addd6',10],['mass_fractions','#edba79',11]]),i);
  if(view.composition)zoneDraw($('zone-b8-canvas'),series([['mass_fractions','#d8adff',12]]),i);
  if(view.composition)zoneDrawLog($('zone-cno-canvas'),series([['mass_fractions','#7addd6',13],['mass_fractions','#edba79',14],['mass_fractions','#d8adff',15]]),i);
  if(view.energy){
    zoneDraw($('zone-density-canvas'),series([['density_kg_m3','#7addd6']]),i);
    zoneDraw($('zone-volume-canvas'),series([['volume_m3','#edba79']]),i);
    const work=[];for(const ref of view.reference?[false,true]:[false]){
      const network=solarZoneCurves[ref?'reference':'actual'];
      work.push({color:'#d8adff',reference:ref,values:network.external_pressure_work_J});
      work.push({color:'#7addd6',reference:ref,values:network.internal_energy_J.map(e=>e-network.internal_energy_J[0])});
    }zoneDrawSigned($('zone-work-canvas'),work,i);
  }
  if(view.energy)zoneDraw($('zone-temperature-canvas'),series([['temperature_K','#7addd6']]),i);
  if(view.energy)zoneDrawSigned($('zone-coulomb-canvas'),series([['Coulomb_internal_energy_J_m3','#d8adff']]),i);
  if(view.energy)zoneDraw($('zone-energy-canvas'),series([['energy_available_J','#7addd6'],['non_neutrino_energy_available_J','#edba79']]),i);
  if(view.neutrinos)zoneDraw($('zone-neutrinos-canvas'),series([['neutrino_count','#7addd6']]),i);
}
let zoneCancelPending=false;
function zonePlaceForm(active,busy){
  const form=$('zone-config-form'),parent=$(active?'zone-config-holder':'zone-start-fields');
  if(form.parentElement!==parent)parent.append(form);
  $('zone-recompute').hidden=!active;$('zone-config-fields').disabled=busy;
  $('zone-ratio').disabled=busy||$('zone-history').value==='constant';
  const calculation=solarZoneState?.calculation;
  for(const id of ['zone-cancel','zone-cancel-setup']){
    $(id).hidden=!calculation?.cancellable;$(id).disabled=zoneCancelPending;
  }
}
$('zone-history').onchange=()=>{$('zone-ratio').disabled=$('zone-history').value==='constant';};
async function zoneCancelCalculation(){
  const id=solarZoneState?.calculation?.transaction_id;if(!id||zoneCancelPending)return;
  zoneCancelPending=true;renderSolarZone();
  try{
    const response=await fetch('/api/solar-zone/cancel',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({transaction_id:id})});
    const value=await response.json();if(!response.ok||!value.ok)throw Error(value.error||'Cancelamento não confirmado.');
    solarZoneState=value.zone;solarZoneError='Cálculo cancelado; última leitura confirmada preservada.';
  }catch(error){solarZoneError=error.message;}finally{zoneCancelPending=false;renderSolarZone();}
}
$('zone-cancel').onclick=zoneCancelCalculation;$('zone-cancel-setup').onclick=zoneCancelCalculation;
function renderSolarZone(){
  const active=Boolean(solarZoneState?.active),w=solarZoneState?.worker,p=appState?.physics,busy=solarZonePending||Boolean(solarZoneState?.busy);
  zonePlaceForm(active,busy);
  globalThis.cosmosSolarZoneActive=active;document.body.classList.toggle('zone-active',active);$('zone-panel').hidden=!active;$('zone-charts').hidden=!active;
  $('zone-setup').hidden=appState?.mode!=='experiment'||p?.bodies.length!==4;
  $('zone-create').disabled=busy||pending||active||!p?.paused||Boolean(particleState?.active);
  $('zone-load-saved').disabled=$('zone-create').disabled||!solarZoneState?.checkpoint_available;
  $('zone-setup-status').textContent=!active?(busy?'Calculando a zona… O sistema solar continua pausado.':solarZoneError||solarZoneState?.error||''):'';
  if(!active||!w){solarZoneCurves=null;solarZoneCurveId=null;solarZoneFormId=null;return;}
  if(solarZoneFormId!==w.artifact_id)zoneFillConfiguration(w);
  $('zone-status').textContent=busy?'Aguarde a confirmação do cenário…':solarZoneState.playing?'Reproduzindo instantes já calculados':'Leitura pausada · cenário calculado';
  $('zone-source').textContent='Fonte arquivada: Sol\nÉpoca orbital: '+w.source.epoch.utc+'\nA órbita atual fica preservada ao fechar.';
  const s=w.sample.actual,r=w.sample.reference,i=w.view.selected_index;
  $('zone-model-reading').textContent='EOS: '+(w.configuration.include_coulomb?'Coulomb PC · íons clássicos':'Mistura ideal FD')+' · Screening: '+(w.configuration.include_screening?'ativo':'desligado');
  $('zone-screening-reading').textContent='Fatores adicionais de fusão:\np + p: ×'+zoneNumber(s.screening_factors.pp)+' · N14 + p: ×'+zoneNumber(s.screening_factors.n14pg)+'\nO16 + p: ×'+zoneNumber(s.screening_factors.o16pg)+'\nEC Be7 e quatro decaimentos: ×1; lei de plasma EC preservada.';
  for(const c of zoneChannels)zoneFactorValues[c].textContent='×'+zoneNumber(s.screening_factors[c]);
  $('zone-index-label').textContent=i+'/240 · '+zoneNumber(s.time_s)+' s';$('zone-index').value=i;$('zone-index').disabled=busy;
  $('zone-play').textContent=solarZoneState.playing?'Pausar reprodução':'Reproduzir amostras';$('zone-play').disabled=busy||i===240;$('zone-step').disabled=busy||i===240;
  $('zone-rate').value=solarZoneState.samples_per_wall_s;$('zone-rate').disabled=busy;
  $('zone-thermodynamic-reading').textContent='ρ = '+zoneNumber(s.density_kg_m3)+' kg/m³ · V = '+zoneNumber(s.volume_m3)+' m³\nNᵦ = '+zoneNumber(s.baryon_count)+' (fixo)\nTrabalho externo W = '+zoneNumber(s.external_pressure_work_J)+' J\nΔE = '+zoneNumber(s.internal_energy_J-s.initial_internal_energy_J)+' J · Q retido = '+zoneNumber(s.non_neutrino_energy_available_J)+' J';
  $('zone-probe').textContent='Tempo nuclear: '+zoneNumber(s.time_s)+' s\nTemperatura: '+zoneNumber(s.temperature_K)+' K\nPressão: '+zoneNumber(s.pressure_Pa)+' Pa\nEnergia por volume U: '+zoneNumber(s.internal_energy_J_m3)+' J/m³\nEnergia total E=VU: '+zoneNumber(s.internal_energy_J)+' J\nCorrelação de Coulomb: '+zoneNumber(s.Coulomb_internal_energy_J_m3)+' J/m³\nCapacidade térmica: '+zoneNumber(s.heat_capacity_J_m3_K)+' J/(m³ K)\n'+Object.entries(s.mass_fractions).map(([name,x])=>name+': '+zoneAbundance(x)).join(' · ')+'\n'+zoneChannels.map(c=>c+': '+zoneEventRate(s,c)+' /(m³ s)').join('\n')+'\nElétrons capturados: '+zoneNumber(s.captured_electrons)+'\nPósitrons produzidos: '+zoneNumber(s.produced_positrons)+'\nEnergia nuclear disponível: '+zoneNumber(s.energy_available_J)+' J\nEnergia nuclear retida: '+zoneNumber(s.non_neutrino_energy_available_J)+' J\nEnergia em neutrinos: '+zoneNumber(s.energy_neutrinos_J)+' J\nPotência nuclear: '+zoneNumber(s.nuclear_power_W)+' W\nPotência de trabalho externo: '+zoneNumber(s.external_pressure_power_W)+' W\nNeutrinos totais produzidos: '+zoneNumber(s.neutrino_count);
  $('zone-reference-reading').hidden=!w.view.visible.reference;$('zone-reference-reading').textContent='Referência completa no mesmo instante e programa de densidade:\nTemperatura: '+zoneNumber(r.temperature_K)+' K\nEnergia interna total: '+zoneNumber(r.internal_energy_J)+' J\nTrabalho externo: '+zoneNumber(r.external_pressure_work_J)+' J\nEnergia nuclear retida: '+zoneNumber(r.non_neutrino_energy_available_J)+' J\nDiferença atual − referência: '+zoneNumber(s.energy_available_J-r.energy_available_J)+' J';
  $('zone-config-fields').disabled=busy;$('zone-visual').disabled=busy;$('zone-screening').disabled=busy||!$('zone-coulomb').checked;$('zone-ratio').disabled=busy||$('zone-history').value==='constant';
  for(const k of ['composition','energy','neutrinos','reference'])$('zone-show-'+k).checked=w.view.visible[k];
  for(const id of ['zone-save','zone-load','zone-new-worker','zone-export','zone-restart','zone-branch-create','zone-branch-load','zone-frame','zone-leave'])$(id).disabled=busy;
  $('zone-load').disabled||=!solarZoneState.checkpoint_available;$('zone-new-worker').disabled||=!solarZoneState.checkpoint_available;
  const select=$('zone-branch-select'),branches=w.branches||[],signature=JSON.stringify(branches),selected=select.value;
  if(select.dataset.signature!==signature){select.replaceChildren();for(const b of branches){const o=document.createElement('option');o.value=b.id;o.disabled=!b.valid;o.textContent=b.name+(b.valid?' · amostra '+b.selected_index:' · indisponível');select.append(o);}if(branches.some(b=>b.id===selected))select.value=selected;select.dataset.signature=signature;}
  $('zone-branch-load').disabled||=!branches.some(b=>b.id===select.value&&b.valid);
  $('zone-provenance').textContent='Fonte: '+w.source.body_reference_id+'\nReferencial: J2000, cópia baricêntrica; render GALACTIC\nGM: '+zoneNumber(w.source.GM_m3_s2)+' m³/s²\nFonte selada: '+w.source.binding_sha256.slice(0,16)+'…\nSem reação na órbita.';
  $('zone-error').textContent=solarZoneError||solarZoneState.error||'';zoneRenderCharts(w);
}
$('zone-create').onclick=()=>{const p=appState?.physics;if(!p||!$('zone-config-form').reportValidity())return;return solarZoneCommand('create',{source_guard:{system_id:p.system_id,edit_token:p.edit_token,revision:p.revision,time:p.time,frame:p.contract.frame},configuration:zoneConfiguration()});};
$('zone-load-saved').onclick=()=>solarZoneCommand('load_saved');
$('zone-config-form').onsubmit=e=>{e.preventDefault();if($('zone-config-form').reportValidity()){if(solarZoneState?.active)solarZoneCommand('configure',{configuration:zoneConfiguration()});else $('zone-create').click();}};
$('zone-play').onclick=()=>solarZoneCommand(solarZoneState.playing?'pause':'play');
$('zone-step').onclick=()=>solarZoneCommand('sample',{index:Math.min(240,solarZoneState.worker.view.selected_index+1)});
$('zone-index').onchange=()=>solarZoneCommand('sample',{index:Number($('zone-index').value)});
$('zone-rate').onchange=()=>solarZoneCommand('set_rate',{value:Number($('zone-rate').value)});
for(const k of ['composition','energy','neutrinos','reference'])$('zone-show-'+k).onchange=()=>solarZoneCommand('set_view',{view:{selected_index:solarZoneState.worker.view.selected_index,visible:Object.fromEntries(['composition','energy','neutrinos','reference'].map(k=>[k,$('zone-show-'+k).checked]))}});
for(const name of ['save','load','export','restart','frame','leave'])$('zone-'+name).onclick=()=>solarZoneCommand(name);
$('zone-new-worker').onclick=()=>solarZoneCommand('new_worker');
$('zone-branch-create').onclick=()=>solarZoneCommand('branch_create',{name:$('zone-branch-name').value});
$('zone-branch-load').onclick=()=>solarZoneCommand('branch_load',{branch_id:$('zone-branch-select').value});
async function pollSolarZone(){try{const response=await fetch('/api/solar-zone/state');if(response.ok){const value=await response.json();if(solarZonePending){solarZoneState={...solarZoneState,busy:value.busy,calculation:value.calculation};}else solarZoneState=value;}renderSolarZone();}catch{}finally{setTimeout(pollSolarZone,200);}}
pollSolarZone();
