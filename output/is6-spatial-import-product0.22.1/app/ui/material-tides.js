'use strict';
let tideSnapshot=null,tideIdentity='',tideOptions='';
const tideNumber=v=>Number.isFinite(v)?v.toExponential(6):'—';
function clearTideEditor(){tideSnapshot=null;$('tide-editor-fields').disabled=true;$('tide-editor-status').textContent='Pause e carregue os parâmetros materiais.';}
function updateMaterialTides(p){
  const options=p.system_id+'|'+p.bodies.map(b=>b.id).join('|');
  if(options!==tideOptions){const selected=$('tide-body').value;$('tide-body').replaceChildren(...p.bodies.map(b=>new Option(b.name,b.id)));if(p.bodies.some(b=>b.id===selected))$('tide-body').value=selected;tideOptions=options;}
  const body=p.bodies.find(b=>b.id===$('tide-body').value),identity=p.system_id+'|'+p.edit_token+'|'+body?.id;
  if(identity!==tideIdentity){tideIdentity=identity;clearTideEditor();}
  const material=p.material_tides,selected=material?.body===body?.id;
  $('tide-status').textContent=material?'Maré material ativa em '+p.bodies.find(b=>b.id===material.body)?.name+'.\nCalor acumulado: '+tideNumber(material.dissipated_heat_J)+' J\nPotência dissipada: '+tideNumber(material.heat_power_W)+' W\nSpin material x/y/z: '+material.spin_rad_s.map(tideNumber).join(' / ')+' rad/s\nEnergia mecânica + calor: '+tideNumber(material.energy_plus_heat_J)+' J\n'+material.parameters.provenance:'Maré material desativada. O tensor de maré das sondas continua disponível e mede aceleração diferencial.';
  const stale=tideSnapshot&&(p.revision!==tideSnapshot.revision||p.time!==tideSnapshot.expected_time);
  $('prepare-tide').disabled=pending||!body||p.bodies.length!==2||Object.keys(p.gravity_effects||{}).length>0||Boolean(material&&!selected);
  $('apply-tide').disabled=pending||!tideSnapshot||!p.paused||Boolean(stale)||Boolean(selected&&$('tide-active').checked);
  $('tide-new-pair').disabled=pending;
  if(stale)$('tide-editor-status').textContent='A fase ou a revisão mudou. Pause e carregue novamente.';
  if(material)$('tide-domain').textContent='Deformação pequena: '+tideNumber(material.domain.tidal_strain_parameter)+'; atraso adimensional: '+tideNumber(material.domain.lag_measure)+'; rotação: '+tideNumber(material.domain.rotation_parameter)+'.\nLimites deste modelo: deformação ≤0,01; atraso ≤0,05; rotação ≤0,01. Saída do domínio pausa na última fase válida.';
  else $('tide-domain').textContent='Domínio exterior, campo fraco e velocidades pequenas. Exige exatamente dois corpos ativos, um corpo deformável e um companheiro pontual. J2 prescrito precisa estar desativado.';
  $('lab-model-tag').textContent=material?'MARÉ MATERIAL · ÓRBITA E SPIN':'MODELO NEWTONIANO · IAS15';
  $('energy-scope').textContent='¹ Desde a condição inicial ou última intervenção. '+(material?'Energia auditada = translação + resposta induzida + spin material + calor acumulado.':'Com energia de referência nula, mostra ΔE absoluto em unidades canônicas.');
  $('conservation-scope').textContent=material?'Balanços de energia mecânica mais calor e momento angular de órbita mais spin material. O centro de massa segue movimento inercial.':'Translação dos centros. Referência renovada nas intervenções físicas; raio/spin cinemáticos não a alteram.';
  $('conservation-normalization').textContent='Erros de P e L normalizados pelas somas de seus módulos na referência. '+(material?'L inclui o spin do corpo material.':'Spin cinemático fica fora desses balanços.');
}
function fillTideEditor(){
  const p=appState?.physics,body=p?.bodies.find(b=>b.id===$('tide-body').value);if(!p?.paused||!body)return;
  const active=p.material_tides?.body===body.id,c=active?p.material_tides.parameters:null;
  tideSnapshot={...editGuard(p),body:body.id};$('tide-active').checked=active;
  for(const [id,key] of [['tide-radius','radius_m'],['tide-love','love_k2'],['tide-lag','time_lag_s'],['tide-inertia','inertia_kg_m2'],['tide-provenance','provenance']])$(id).value=c?String(c[key]):'';
  (active?p.material_tides.spin_rad_s:[0,0,0]).forEach((v,i)=>$('tide-spin-'+i).value=String(v));
  $('tide-editor-fields').disabled=false;$('tide-parameters').disabled=active||!$('tide-active').checked;
  $('tide-editor-status').textContent=active?'Para alterar parâmetros, desative primeiro. A remoção do spin, da resposta e do reservatório de calor registra intervenção externa.':'Informe parâmetros próprios: k2 potencial, atraso em segundos, inércia SI e spin material. Nenhum atributo cinemático é convertido automaticamente.';
  updateMaterialTides(p);
}
$('tide-body').onchange=()=>{clearTideEditor();if(appState?.physics)updateMaterialTides(appState.physics);};
$('tide-active').onchange=()=>{$('tide-parameters').disabled=!$('tide-active').checked||appState?.physics?.material_tides?.body===$('tide-body').value;if(appState?.physics)updateMaterialTides(appState.physics);};
$('prepare-tide').onclick=async()=>{await command({command:'pause'},'Experimento pausado para configurar maré material.');fillTideEditor();};
$('tide-new-pair').onclick=async()=>{
  await command({command:'pause'},'Preparando par sintético.');
  const p=appState?.physics;if(!p?.paused)return;
  await command({command:'load_tidal_experiment',...editGuard(p)},'Novo par sintético com maré ativada; parâmetros e origem registrados.');
  if(appState?.physics?.material_tides){$('tide-body').value=appState.physics.material_tides.body;fillTideEditor();}
};
$('tide-form').onsubmit=async event=>{
  event.preventDefault();if(pending||!tideSnapshot||!$('tide-form').reportValidity())return;
  const revision=tideSnapshot.revision,parameters=$('tide-active').checked?{radius_m:Number($('tide-radius').value),love_k2:Number($('tide-love').value),time_lag_s:Number($('tide-lag').value),inertia_kg_m2:Number($('tide-inertia').value),spin_rad_s:[0,1,2].map(i=>Number($('tide-spin-'+i).value)),provenance:$('tide-provenance').value}:null;
  await command({...tideSnapshot,command:'set_tides',parameters},parameters?'Maré material ativada; órbita, spin e calor evoluem juntos.':'Maré material desativada; intervenção de energia e momento angular registrada.');
  if(appState?.physics?.revision===revision+1)fillTideEditor();
};
