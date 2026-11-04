'use strict';
function updateTestCloud(p,view,supported){
  const c=p.test_particle_cloud,n=view?.native,m=n?.metadata,reading=view?.reading;
  $('cloud-create').disabled=pending||supported!==true;
  $('cloud-select').disabled=pending||!c;
  $('cloud-focus').disabled=pending||!view?.selection_follows_confirmed_positions;
  $('cloud-remove').disabled=pending||!c;
  $('cloud-export-positions').disabled=pending||!c;
  $('cloud-export-reading').disabled=pending||!reading;
  $('cloud-index').max=c?c.test_particles-1:9999;
  $('cloud-status').textContent=c?c.test_particles.toLocaleString('pt-BR')+' partículas sem massa; uma fonte ativa. '+(m?'Cena confirmada: t = '+m.time_s.toExponential(6)+' s; sequência '+m.sequence+'.':'Aguardando confirmação da cena.'):'Sem partículas de teste. Criar substitui o cenário atual; salve ou arquive antes para retomá-lo.';
  if(supported!==true)$('cloud-status').textContent='Partículas de teste indisponíveis neste modo de abertura. Os cenários de corpos massivos continuam disponíveis.';
  const f=x=>x.toExponential(7);
  $('cloud-reading').textContent=reading?['Partícula '+reading.index+' · massa = 0 kg',
    (view.reading_is_stale?'LEITURA ANTIGA':'Leitura confirmada')+' · t = '+f(reading.time_s)+' s',
    'Posição x/y/z (m): '+reading.position_m.map(f).join(' / '),
    'Velocidade x/y/z (m/s): '+reading.velocity_m_s.map(f).join(' / '),
    'Energia específica relativa à fonte: '+f(reading.specific_energy_J_kg)+' J/kg',
    'Momento angular específico (m²/s): '+reading.specific_angular_momentum_m2_s.map(f).join(' / '),
    'Referencial: '+reading.frame,
    'O marcador acompanha as posições confirmadas. Os números acima pertencem ao instante da medição.'].join('\n'):'Selecione um índice para pausar e medir posição, velocidade e integrais específicas em SI.';
  if(c){
    $('lab-intro').textContent='Anel circular sintético: uma fonte newtoniana e '+c.test_particles.toLocaleString('pt-BR')+' partículas de teste sem massa. Sem reação sobre a fonte e sem interação entre partículas.';
    $('lab-model-tag').textContent='PARTÍCULAS DE TESTE · IAS15';
    $('energy-scope').textContent='O balanço global inclui apenas a fonte ativa. Cada partícula tem energia e momento angular específicos relativos à fonte, medidos na seleção.';
    $('apply-mass').disabled=true;
  }else $('apply-mass').disabled=pending;
}
$('cloud-create').onclick=async()=>{
  await command({command:'pause'},'Preparando anel sintético.');
  const p=appState?.physics;if(!p?.paused)return;
  await command({command:'load_cloud_experiment',...editGuard(p),parameters:{count:10000}},'Anel de 10.000 partículas criado e pausado.');
};
$('cloud-select').onclick=async()=>{
  if(!$('cloud-index').reportValidity())return;
  await command({command:'pause'},'Pausando para medir a partícula.');
  const p=appState?.physics;if(!p?.paused||!p.test_particle_cloud)return;
  await command({command:'select_cloud_particle',system_id:p.system_id,edit_token:p.edit_token,
    cloud_id:p.test_particle_cloud.cloud_id,index:Number($('cloud-index').value)},'Partícula medida no instante confirmado pela cena.');
};
$('cloud-focus').onclick=()=>script('openspace.navigation.setNavigationState({Anchor="C2CloudSelection",ReferenceFrame="LabRoot",Position={0,-1e9,6e8},Up={0,0,1}})');
$('cloud-remove').onclick=async()=>{
  await command({command:'pause'},'Pausando a nuvem.');
  const p=appState?.physics;if(!p?.paused)return;
  await command({command:'set_cloud',...editGuard(p),parameters:null},'Partículas removidas; a fonte ativa foi preservada.');
};
$('cloud-export-reading').onclick=async()=>{
  const p=appState?.physics;if(!p?.test_particle_cloud)return;
  const result=await command({command:'export_cloud_reading',system_id:p.system_id,edit_token:p.edit_token,
    cloud_id:p.test_particle_cloud.cloud_id},'Leitura SI exportada.');
  if(result)$('notice').textContent=(result.ack.reading_is_stale?'Leitura antiga preservada em: ':'Leitura confirmada exportada em: ')+result.ack.export_file;
};
$('cloud-export-positions').onclick=async()=>{
  await command({command:'pause'},'Pausando para exportar todas as posições SI.');
  const p=appState?.physics;if(!p?.paused||!p.test_particle_cloud)return;
  const result=await command({command:'export_cloud_positions',system_id:p.system_id,edit_token:p.edit_token,
    cloud_id:p.test_particle_cloud.cloud_id},'Posições SI exportadas.');
  if(result)$('notice').textContent=result.ack.count.toLocaleString('pt-BR')+' posições SI exportadas em: '+result.ack.export_file;
};
