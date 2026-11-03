'use strict';
let particleState=null,particlePending=false,particlePolling=false,particleError='';
const particleNumber=(x,d=7)=>x!==0&&(Math.abs(Number(x))<1e-4||Math.abs(Number(x))>=1e7)?Number(x).toExponential(d-1):Number(x).toLocaleString('pt-BR',{maximumSignificantDigits:d});
const particleVector=x=>x.map(v=>Number(v).toExponential(6)).join(' / ');
function particleGuard(){const s=particleState?.worker,e=s?.experiment;if(!e)throw Error('Atualize a leitura da partícula.');return {worker_id:s.worker_id,experiment_id:e.id,edit_token:e.edit_token,revision:e.revision,expected_time_s:e.phase.time_s,frame:s.frame};}
async function particleCommand(command,extra={}){
  if(particlePending)return;particlePending=true;particleError='';renderParticle();
  try{const request={command,...extra};if(!['create','create_wind','load_saved','leave'].includes(command))request.guard=particleGuard();
    const response=await fetch('/api/particles/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request)}),value=await response.json();
    if(!response.ok||!value.ok)throw Error(value.error||'Comando de partícula recusado.');particleState=value.particle;
    $("notice").textContent=particleState.active?"Partícula "+(particleState.worker.paused?"pausada":"em movimento")+" · órbita preservada.":"Vista da partícula encerrada · órbita preservada.";
    if(command==='export'&&value.result?.export_file)$('notice').textContent='Exportado: '+value.result.export_file;
    return value;
  }catch(error){particleError=error.message;$("notice").textContent=error.message;}finally{particlePending=false;renderParticle();}
}
function renderParticle(){
  const active=Boolean(particleState?.active),s=particleState?.worker,e=s?.experiment,p=appState?.physics;
  document.body.classList.toggle('particle-active',active);$('particle-panel').hidden=!active;
  $('wind-setup').hidden=appState?.mode!=='experiment'||p?.bodies.length!==4;
  $('wind-create').disabled=particlePending||pending||active||!p?.paused||p?.bodies.length!==4;
  $('wind-setup-status').textContent=!active?particleError:'';
  $('particle-setup').hidden=appState?.mode!=='experiment'||p?.bodies.length!==4;
  const layer=appState?.body_field_preview,r=layer?.reading,fresh=r&&p&&['system_id','edit_token','revision','time'].every(k=>r[k]===p[k]);
  $('particle-source').textContent=fresh?`Origem: ${r.body_reference_id==='sol:naif:399'?'Terra · IGRF14':'Júpiter · JRM33'}. Amostra e fase confirmadas. E = 0 prescrito; gravidade dos quatro centros.`:'Prepare uma amostra magnética da Terra ou de Júpiter abaixo, na fase pausada atual.';
  $('particle-create').disabled=particlePending||pending||active||!fresh||!p?.paused;
  $('particle-load-saved').disabled=particlePending||active||!particleState?.checkpoint_available||!p?.paused;
  $('particle-setup-status').textContent=!active?particleError:'';
  for(const id of ['atlas','experiment','forces','open-content']){if(active||globalThis.cosmosSolarZoneActive)$(id).disabled=true;else if(!pending)$(id).disabled=false;}
  if(!active||!e)return;
  const wind=e.model.startsWith('Parker');
  const paused=s.paused,view=particleState.view,cp=view?.confirmed_phase,native=view?.native,meta=view?.confirmed_metadata;
  $('particle-title').textContent=(e.parameters.charge_C===0?'Partícula neutra':e.parameters.charge_C<0?'Elétron':'Próton')+(wind?' no vento solar prescrito':' no campo '+(e.model.startsWith('IGRF')?'da Terra':'de Júpiter'));
  $('particle-electric-label').textContent=wind?'Força elétrica · E = −u × B prescrito':'Força elétrica · E = 0 prescrito';
  $('particle-state').textContent=e.termination?'Pausada no limite do modelo: '+e.termination.message:paused?'Partícula pausada':'Partícula em movimento · fonte orbital congelada';
  $('particle-phase').textContent='Tempo próprio: '+particleNumber(e.phase.time_s)+' s\nPasso físico: '+particleNumber(e.parameters.dt_s)+' s\n'+e.step_index.toLocaleString('pt-BR')+' passos aceitos';
  $('particle-view-phase').textContent=!cp?'Aguardando a primeira fase da vista.':cp.time_s===e.phase.time_s&&!view.pending_sequence?'Vista na fase atual: '+particleNumber(cp.time_s)+' s.':'Vista confirmada até '+particleNumber(cp.time_s)+' s; próxima fase em trânsito.';
  $('particle-play').textContent=paused?'Iniciar':'Pausar';$('particle-play').disabled=particlePending||Boolean(e.termination);
  for(const id of ['particle-step','particle-rate','particle-save','particle-load','particle-export','particle-restart'])$(id).disabled=particlePending||!paused;
  $('particle-load').disabled||=!particleState.checkpoint_available;
  $('particle-branch-create').disabled=particlePending;
  const branch=$('particle-branch-select'),selected=branch.value,branches=particleState.branches||[];
  if(branch.dataset.signature!==JSON.stringify(branches)){branch.replaceChildren();for(const b of branches){const o=document.createElement('option');o.value=b.id;o.disabled=!b.valid;o.textContent=b.name+(b.valid?' · '+particleNumber(b.time_s)+' s':' · indisponível');branch.append(o);}if(branches.some(b=>b.id===selected))branch.value=selected;branch.dataset.signature=JSON.stringify(branches);}
  $('particle-branch-load').disabled=particlePending||!paused||!branches.some(b=>b.id===branch.value&&b.valid);
  $('particle-sample').disabled=particlePending;$('particle-acting').disabled=particlePending||!paused;
  for(const key of ['gravity','magnetic','electric'])$('particle-'+key).checked=e.controls[key];
  const steps=s.requested_particle_s_per_wall_s/e.parameters.dt_s;
  if(document.activeElement!==$('particle-rate')){const choice=[...$('particle-rate').options].find(o=>Math.abs(Number(o.value)-steps)<1e-7);$('particle-rate').value=choice?.value||'';}
  $('particle-rate-reading').textContent='Solicitado: '+particleNumber(s.requested_particle_s_per_wall_s)+' s de partícula/s real. Efetivo: '+particleNumber(s.effective_particle_s_per_wall_s)+' s/s. Reprodução não altera o passo físico.';
  $('particle-visible').checked=view?.visible??true;$('particle-visible').disabled=particlePending;$('particle-frame').disabled=particlePending;
  $('particle-scale').textContent='Vista ampliada: 1 unidade local = '+particleNumber(view?.physical_unit_m)+' m. Eixos fixos no lançamento; cor e tamanho do marcador são gráficos.';
  $('particle-provenance').textContent=e.model+(e.degree===null?'':' · grau '+e.degree)+'\nÉpoca congelada: '+e.snapshot_epoch.utc+'\nOrientação '+(wind?'IAU_SUN':e.model.startsWith('IGRF')?'ITRF93':'System III')+' congelada na época'+'\n'+particleState.scope+'\n'+(!view?.visible?'Trajetória oculta; dados confirmados até '+particleNumber(cp?.time_s??0)+' s.':native?.gpu_buffer_uploaded&&native?.draw_submitted_sequence===meta?.sequence?'Linha e marcador na fase confirmada.':'Aguardando a confirmação da vista.');
  const a=particleState.sample;
  $('particle-reading').textContent=a?'Tempo: '+particleNumber(a.phase.time_s)+' s\nPosição (m): '+particleVector(a.phase.position_m)+'\nOrigem (m): '+particleVector(a.phase.position_origin_m)+'\nDeslocamento (m): '+particleVector(a.phase.position_offset_m)+'\nVelocidade (m/s): '+particleVector(a.phase.velocity_m_s)+'\nB (T): '+particleVector(a.field.magnetic_field_T)+'\nE (V/m): '+particleVector(a.field.electric_field_V_m)+'\ng (m/s²): '+particleVector(a.field.gravity_m_s2)+'\nΔK: '+Number(a.kinetic_change_J).toExponential(7)+' J\nTrabalho elétrico: '+Number(a.electric_work_J).toExponential(7)+' J\nTrabalho gravitacional: '+Number(a.gravity_work_J).toExponential(7)+' J\nΔ(K + Ugrav): '+Number(a.mechanical_energy_change_J).toExponential(7)+' J\nReferência: '+particleNumber(a.reference_time_s)+' s':'Pause para medir posição, velocidade, campos e trabalho.';
  if(a&&wind)$('particle-reading').textContent+='\nVento radial u (m/s): '+particleVector(a.field.wind_velocity_m_s)+'\nPotencial elétrico (V): '+particleNumber(a.field.electric_potential_V)+'\nΔUelétrico: '+Number(a.electric_potential_change_J).toExponential(7)+' J\nΔ(K + Ugrav + Uelétrico): '+Number(a.total_static_energy_change_J).toExponential(7)+' J';
  $('particle-error').textContent=particleError||particleState.error||'';
  $('particle-leave').disabled=particlePending;
}
$('particle-create-form').onsubmit=async event=>{event.preventDefault();if(!$('particle-create-form').reportValidity())return;const p=appState?.physics;if(!p)return;await particleCommand('create',{source_guard:{system_id:p.system_id,edit_token:p.edit_token,revision:p.revision,time:p.time,frame:p.contract.frame},species:$('particle-species').value,speed_m_s:Number($('particle-speed').value),pitch_deg:Number($('particle-pitch').value)});};
$('particle-play').onclick=()=>particleCommand(particleState.worker.paused?'resume':'pause');
$('particle-step').onclick=()=>particleCommand('advance',{steps:64});
$('particle-rate').onchange=()=>particleCommand('set_rate',{value:Number($('particle-rate').value)*particleState.worker.experiment.parameters.dt_s});
for(const key of ['gravity','magnetic','electric'])$('particle-'+key).onchange=()=>particleCommand('set_controls',{controls:Object.fromEntries(['gravity','magnetic','electric'].map(k=>[k,$('particle-'+k).checked]))});
$('particle-visible').onchange=()=>particleCommand('visible',{visible:$('particle-visible').checked});
$('particle-branch-create').onclick=()=>particleCommand('create_branch',{name:$('particle-branch-name').value});
$('particle-branch-load').onclick=()=>particleCommand('load_branch',{branch_id:$('particle-branch-select').value});
$('particle-frame').onclick=()=>particleCommand('frame');$('particle-save').onclick=()=>particleCommand('save');$('particle-load').onclick=()=>particleCommand('load');
$('particle-load-saved').onclick=()=>particleCommand('load_saved');$('particle-export').onclick=()=>particleCommand('export');$('particle-restart').onclick=()=>particleCommand('restart');$('particle-leave').onclick=()=>particleCommand('leave');
$('particle-sample').onclick=async()=>{if(!particleState.worker.paused)await particleCommand('pause');if(particleState.worker.paused)await particleCommand('sample');};
async function pollParticle(){if(particlePolling)return;particlePolling=true;try{const response=await fetch('/api/particles/state');if(response.ok)particleState=await response.json();renderParticle();}catch{}finally{particlePolling=false;setTimeout(pollParticle,200);}}
pollParticle();

$('wind-create-form').onsubmit=async event=>{event.preventDefault();if(!$('wind-create-form').reportValidity())return;const p=appState?.physics;if(!p)return;await particleCommand('create_wind',{source_guard:{system_id:p.system_id,edit_token:p.edit_token,revision:p.revision,time:p.time,frame:p.contract.frame},species:$('wind-species').value,relative_speed_m_s:Number($('wind-relative-speed').value),pitch_deg:Number($('wind-pitch').value),coordinates:{radius_m:Number($('wind-radius').value)*149597870700,latitude_deg:Number($('wind-latitude').value),east_longitude_deg:Number($('wind-longitude').value)},wind_parameters:{wind_speed_m_s:Number($('wind-speed').value),radial_field_at_AU_T:Number($('wind-bref').value)*1e-9,rotation_rate_rad_s:2*Math.PI/(25.38*86400),polarity:Number($('wind-polarity').value)}});};
