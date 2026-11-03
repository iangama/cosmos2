'use strict';
let particleFormKey=null,customRateKey=null,speciesReference=null,particleMeasurement=null,particleMeasurementArtifact=null;
const particleTarget=()=>state.experiment.mode==='test_particle'?'test-particle':state.editor.visual.selected_id||state.experiment.system.ids[0];
function renderParticle(){
  if(!state)return;
  const ex=state.experiment,prescribed=ex.mode==='test_particle';
  $('test-particle-editor').hidden=!prescribed;
  $('source-editor-title').textContent=prescribed?'Fontes fixas':'Cargas com reação';
  if(prescribed){
    const key=state.system_id+'|'+state.edit_token+'|'+state.revision+'|'+(state.paused?state.time_s:'running');
    if(key!==particleFormKey){
      particleFormKey=key;
      $('particle-charge').value=ex.particle.charge_C;$('particle-mass').value=ex.particle.mass_kg;
      setVector('particle-',['x','y','z'],ex.phase.position_m);setVector('particle-v',['x','y','z'],ex.phase.velocity_m_s);
      const match=Object.entries(speciesReference?.species||{}).find(([,s])=>s.charge_C===ex.particle.charge_C&&s.mass_kg===ex.particle.mass_kg);
      $('particle-species').value=match?.[0]||'custom';
      $('particle-origin').textContent=state.editor.particle_origin==='user_model'?'Condições definidas pelo usuário.':'Condições do preset sintético.';
    }
    document.querySelectorAll('#particle-form input,#particle-form button').forEach(e=>e.disabled=pending||!state.paused);
    $('particle-species').disabled=pending||!state.paused||!speciesReference;
  }
  const rateKey=state.system_id+'|'+state.edit_token+'|'+state.requested_model_s_per_wall_s;
  if(rateKey!==customRateKey&&document.activeElement!==$('custom-rate')){
    $('custom-rate').value=state.requested_model_s_per_wall_s;customRateKey=rateKey;
  }
  $('custom-rate').disabled=pending;
  if(particleMeasurement){
    const m=particleMeasurement,stale=['system_id','edit_token','revision','time_s'].some(k=>m[k]!==state[k])||m.particle.id!==particleTarget();
    $('particle-measurement').textContent=(stale?'LEITURA CONGELADA · ':'Leitura confirmada · ')+'t = '+number(m.time_s)+' s\n'+
      'Partícula: '+(m.particle.id==='test-particle'?'partícula de teste':m.particle.id)+'\nx: '+vector(m.particle.position_m)+' m\nv: '+vector(m.particle.velocity_m_s)+' m/s\n'+
      'Força elétrica: '+vector(m.force.electric_force_N)+' N\nForça magnética: '+vector(m.force.magnetic_force_N)+' N\n'+
      'Força total: '+vector(m.force.force_N)+' N\nPotência elétrica na partícula: '+number(m.electric_power_W)+' W\n'+
      'Energia cinética total: '+number(m.energy.kinetic_energy_J)+' J\nPotencial total: '+number(m.energy.potential_energy_J)+' J\n'+
      'Trabalho elétrico total desde a referência: '+number(m.balance.electric_work_from_static_potential_J)+' J\n'+
      'ΔK total: '+number(m.balance.kinetic_change_J)+' J\nResíduo ΔK − trabalho: '+number(m.balance.residual_J)+' J';
    $('measurement-note').textContent='Referência em t = '+number(m.balance.reference_time_s)+' s. '+
      (m.mode==='mutual_electrostatic'?'Energia e trabalho somam todas as cargas; a força corresponde à carga identificada. ':'Energia e trabalho da partícula de teste. ')+
      'Trabalho obtido pela diferença do potencial estático entre os dois instantes. '+
      (m.gyro_reference?'Raio de giro local: '+number(m.gyro_reference.radius_m)+' m; período: '+number(m.gyro_reference.period_s)+' s. '+m.gyro_reference.scope:'');
  }
}
$('particle-species').onchange=()=>{
  const s=speciesReference?.species[$('particle-species').value];
  if(!s){$('species-uncertainty').textContent='';return;}
  $('particle-charge').value=s.charge_C;$('particle-mass').value=s.mass_kg;
  $('particle-origin').textContent=s.name+': campos preenchidos. Aplique para confirmar a intervenção.';
  $('species-uncertainty').textContent='Incerteza padrão da massa: '+number(s.mass_standard_uncertainty_kg)+' kg. Carga elementar exata no SI.';
};
$('particle-form').onsubmit=event=>{
  event.preventDefault();
  run(async()=>{
    const changes={charge_C:formVector('particle-',['charge'])[0],mass_kg:formVector('particle-',['mass'])[0],
      position_m:formVector('particle-',['x','y','z']),velocity_m_s:formVector('particle-v',['x','y','z'])};
    await command('edit',{...guard(),edit:{operation:'update_test_particle',changes}});
  });
};
$('custom-rate-form').onsubmit=event=>{
  event.preventDefault();const value=$('custom-rate').valueAsNumber,expected_rate=state.requested_model_s_per_wall_s;
  run(()=>command('set_rate',{...guard(),value,expected_rate}));
};
async function measureMatter(download=false){
  await command('pause');const response=await command('measure_particle',guard());
  if(!response)return;particleMeasurement=response.result;particleMeasurementArtifact=response.artifact;renderParticle();
  if(download){
    const link=document.createElement('a');link.href=response.artifact.url;link.download='cosmos2-em-forca-energia.json';link.click();
    $('status').textContent='Força, energia e trabalho exportados com fontes, unidades e instante confirmado.';
  }
}
$('measure-particle').onclick=()=>run(()=>measureMatter());
$('export-particle').onclick=()=>run(()=>measureMatter(true));
$('open-cloud').onclick=event=>{
  event.preventDefault();if(pending)return;
  run(async()=>{await nativeRequest('leave');location.href='/em-cloud.html';});
};
window.renderParticle=renderParticle;
run(async()=>{
  const response=await fetch('em/species.json');if(!response.ok)throw Error('Referências de carga e massa indisponíveis.');
  speciesReference=await response.json();particleFormKey=null;renderParticle();
});
