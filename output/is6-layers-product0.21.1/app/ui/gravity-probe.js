'use strict';
function updateGravityProbe(p,result){
  $('sample-probe').disabled=pending;
  $('clear-probe').disabled=pending||!result;
  $('view-probe').disabled=pending||!result;
  if(!result){$('probe-reading').textContent='Posicione a sonda no referencial do experimento e calcule uma leitura.';return;}
  const stale=result.system_id!==p.system_id||result.edit_token!==p.edit_token||result.revision!==p.revision||result.time!==p.time;
  const vector=v=>v.map(x=>x.toExponential(5)).join(' / ');
  $('probe-reading').textContent=(stale?'AMOSTRA FIXA: o estado atual mudou.\n':'Estado atual confirmado.\n')+
    't='+ (result.time*p.physical_scale.time_unit_s/3600).toPrecision(7)+' h · revisão '+result.revision+'\n'+
    'Referencial: '+result.frame+'\nPosição x/y/z (m): '+vector(result.position_m)+'\n'+
    'g x/y/z (m/s²): '+vector(result.acceleration_m_s2)+'\n|g|: '+result.acceleration_norm_m_s2.toExponential(5)+' m/s²\n'+
    'Potencial: '+result.potential_J_kg.toExponential(5)+' J/kg\nFontes ativas: '+result.sources.length;
}
$('probe-form').onsubmit=async e=>{
  e.preventDefault();if(pending)return;
  await command({command:'pause'},'Experimento pausado para a leitura da sonda.');
  const p=appState?.physics;if(!p?.paused)return;
  await command({...editGuard(p),command:'probe',position_m:[0,1,2].map(i=>Number($('probe-position-'+i).value))},'Sonda calculada no instante confirmado.');
};
$('clear-probe').onclick=()=>command({command:'clear_probe'},'Marca e leitura removidas; física preservada.');
$('view-probe').onclick=()=>{
  const result=appState?.probe_preview;if(!result)return;
  const d=Math.max(3e6,.3*Math.min(...result.sources.map(s=>s.distance_m)));
  script('openspace.setPropertyValueSingle("Scene.LabProbe.Renderable.Size",'+Math.log10(d*.001)+');openspace.navigation.setNavigationState({Anchor="LabProbe",ReferenceFrame="LabRoot",Position={0,'+(-d)+','+(d*.6)+'},Up={0,0,1}})');
};
